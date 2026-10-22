from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from red_env.manifest.models import PackageSpec

_TARGET_MAP = {
    "x86_64": "x86_64-unknown-linux-musl",
    "arm64": "aarch64-unknown-linux-musl",
}


def apply_zig_build(package: PackageSpec, downloaded_asset: Path, bundle_root: Path, arch: str) -> list[Path]:
    target_triple = _TARGET_MAP.get(arch)
    if target_triple is None:
        raise ValueError(f"unsupported architecture for zig build: {arch}")

    target_dir = bundle_root / package.strategy.extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    include = package.strategy.extract.get("include", [package.id])

    with tempfile.TemporaryDirectory(prefix="red_env_zig_build_") as tmp:
        extract_dir = Path(tmp) / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(downloaded_asset, "r:*") as archive:
            archive.extractall(extract_dir)

        entries = list(extract_dir.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            source_root = entries[0]
        else:
            source_root = extract_dir

        # Some upstreams pin a toolchain via rust-toolchain.toml. rustup then
        # switches to that channel, which usually lacks the musl target this
        # build needs and fails with "can't find crate for `core`". Drop the
        # pin so the environment toolchain (with musl targets installed) wins.
        for marker in ("rust-toolchain.toml", "rust-toolchain"):
            pinned = source_root / marker
            if pinned.is_file():
                pinned.unlink()

        args_list = package.strategy.extract.get("build_args", [])
        if isinstance(args_list, list):
            extra_args = [str(a) for a in args_list]
        else:
            extra_args = []
        cmd = ["cargo", "zigbuild", "--target", target_triple, "--release", *extra_args]
        env = os.environ.copy()
        env.setdefault("CARGO_TERM_COLOR", "always")
        # Use a per-build cache dir so cargo-zigbuild and zig don't collide
        # with global caches (which may be read-only or owned by another user).
        env.setdefault("CARGO_ZIGBUILD_CACHE_DIR", str(Path(tmp) / "zigbuild-cache"))
        try:
            subprocess.run(cmd, cwd=source_root, env=env, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else ""
            stdout = exc.stdout.strip() if exc.stdout else ""
            detail = stderr or stdout
            raise RuntimeError(
                f"zig build failed for {package.id} (target={target_triple}): {detail}"
            ) from exc

        written = []
        for name in include:
            binary_path = source_root / "target" / target_triple / "release" / name
            if not binary_path.exists():
                raise ValueError(f"zig build did not produce expected binary: {name}")
            dest = target_dir / name
            shutil.copy2(binary_path, dest)
            dest.chmod(0o755)
            written.append(dest)

    return written