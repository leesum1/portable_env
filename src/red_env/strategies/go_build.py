from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

from red_env.manifest.models import PackageSpec


def apply_go_build(package: PackageSpec, downloaded_asset: Path, bundle_root: Path, arch: str) -> list[Path]:
    target_dir = bundle_root / package.strategy.extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    binary_name = package.strategy.extract.get("binary_name", package.id)
    include = package.strategy.extract.get("include", [binary_name])

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

        env = os.environ.copy()
        env["CGO_ENABLED"] = "0"
        # Use per-build cache dirs so go doesn't touch global caches
        # (which may be read-only or owned by another user).
        env.setdefault("GOCACHE", str(Path(tmp) / "go-cache"))
        env.setdefault("GOMODCACHE", str(Path(tmp) / "gomod-cache"))

        for name in include:
            cmd = ["go", "build", "-ldflags=-s -w", "-o", name, "."]
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