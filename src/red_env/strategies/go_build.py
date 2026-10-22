from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from red_env.manifest.models import PackageSpec
from red_env.strategies.toolchain import go_environment, locked_flag

_GOARCH_MAP = {
    "x86_64": "amd64",
    "arm64": "arm64",
}


def _optional_version(value: object) -> str | None:
    if value is None:
        return None
    version = str(value).strip()
    return version or None


def apply_go_build(
    package: PackageSpec,
    downloaded_asset: Path,
    bundle_root: Path,
    arch: str,
    cache_dir: Path | None = None,
) -> list[Path]:
    goarch = _GOARCH_MAP.get(arch)
    if goarch is None:
        raise ValueError(f"unsupported architecture for go build: {arch}")

    extract = package.strategy.extract
    go_version = _optional_version(extract.get("go_version"))
    locked = locked_flag(extract, package.id)

    target_dir = bundle_root / extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    binary_name = extract.get("binary_name", package.id)
    include = extract.get("include", [binary_name])

    with tempfile.TemporaryDirectory(prefix="red_env_go_build_") as tmp:
        extract_dir = Path(tmp) / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(downloaded_asset, "r:*") as archive:
            archive.extractall(extract_dir)

        entries = list(extract_dir.iterdir())
        if len(entries) == 1 and entries[0].is_dir():
            source_root = entries[0]
        else:
            source_root = extract_dir

        env = go_environment(cache_dir, go_version, goarch)

        for name in include:
            cmd = ["go", "build", "-trimpath", "-buildvcs=false"]
            if locked:
                cmd.append("-mod=readonly")
            cmd.extend(["-ldflags=-s -w", "-o", name, "."])
            try:
                subprocess.run(cmd, cwd=source_root, env=env, check=True, capture_output=True, text=True)
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.strip() if exc.stderr else ""
                stdout = exc.stdout.strip() if exc.stdout else ""
                detail = stderr or stdout
                raise RuntimeError(
                    f"go build failed for {package.id} (binary={name}): {detail}"
                ) from exc
            dest = target_dir / name
            shutil.copy2(source_root / name, dest)
            dest.chmod(0o755)

    return [target_dir / name for name in include]
