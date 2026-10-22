from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from red_env.manifest.models import PackageSpec
from red_env.strategies.toolchain import cargo_environment, locked_flag

_TARGET_MAP = {
    "x86_64": "x86_64-unknown-linux-musl",
    "arm64": "aarch64-unknown-linux-musl",
}

# Upstreams that pin a toolchain channel would otherwise make rustup switch to
# a channel without the musl targets and fail with "can't find crate for
# `core`". The manifest pin is authoritative, so these files are dropped.
_PINNED_TOOLCHAIN_FILES = ("rust-toolchain.toml", "rust-toolchain")


def _optional_version(value: object) -> str | None:
    if value is None:
        return None
    version = str(value).strip()
    return version or None


def _installed_cargo_version() -> str | None:
    try:
        completed = subprocess.run(["cargo", "--version"], capture_output=True, text=True, check=False)
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    parts = completed.stdout.strip().split()
    return parts[1] if len(parts) >= 2 else None


def _rustup_toolchains() -> list[str] | None:
    """Return the toolchains rustup knows about, or None when it cannot be determined."""
    try:
        completed = subprocess.run(
            ["rustup", "toolchain", "list"], capture_output=True, text=True, check=False
        )
    except OSError:
        return None
    if getattr(completed, "returncode", 0) != 0:
        return None
    stdout = getattr(completed, "stdout", None)
    if not isinstance(stdout, str):
        return None
    return [line.split()[0] for line in stdout.splitlines() if line.strip()]


def _require_installed_toolchain(rust_version: str) -> None:
    toolchains = _rustup_toolchains()
    if toolchains is None:
        # Cannot inspect rustup; let the actual build report the problem.
        return
    if any(name.split("-")[0] == rust_version for name in toolchains):
        return
    raise RuntimeError(
        f"pinned Rust toolchain {rust_version} is not installed. Either install it:\n"
        f"  rustup toolchain install {rust_version} "
        "--target x86_64-unknown-linux-musl,aarch64-unknown-linux-musl\n"
        "or build inside the hermetic image, which already carries every pinned toolchain:\n"
        "  python -m red_env build --profile <profile> --arch <arch> --in-docker"
    )


def _cargo_command(rust_version: str | None) -> list[str]:
    if rust_version is None:
        return ["cargo"]
    if shutil.which("rustup"):
        _require_installed_toolchain(rust_version)
        return ["rustup", "run", rust_version, "cargo"]
    installed = _installed_cargo_version()
    if installed != rust_version:
        raise RuntimeError(
            f"pinned Rust toolchain {rust_version} is required for zig_build but cargo reports "
            f"{installed or 'an unknown version'}. Install rustup and run: "
            f"rustup toolchain install {rust_version}"
        )
    return ["cargo"]


def apply_zig_build(
    package: PackageSpec,
    downloaded_asset: Path,
    bundle_root: Path,
    arch: str,
    cache_dir: Path | None = None,
) -> list[Path]:
    target_triple = _TARGET_MAP.get(arch)
    if target_triple is None:
        raise ValueError(f"unsupported architecture for zig build: {arch}")

    extract = package.strategy.extract
    rust_version = _optional_version(extract.get("rust_version"))
    locked = locked_flag(extract, package.id)

    target_dir = bundle_root / extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    include = extract.get("include", [package.id])

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

        for marker in _PINNED_TOOLCHAIN_FILES:
            pinned = source_root / marker
            if pinned.is_file():
                pinned.unlink()

        args_list = extract.get("build_args", [])
        if isinstance(args_list, list):
            extra_args = [str(a) for a in args_list]
        else:
            extra_args = []

        cmd = [*_cargo_command(rust_version), "zigbuild", "--target", target_triple, "--release"]
        if locked:
            if not (source_root / "Cargo.lock").is_file():
                raise RuntimeError(
                    f"zig build for {package.id} requires a Cargo.lock to honour --locked, but the "
                    "source archive does not contain one. Add a lock file upstream or set "
                    'locked = false in the package strategy extract.'
                )
            cmd.append("--locked")
        cmd.extend(extra_args)

        env = cargo_environment(cache_dir)
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
