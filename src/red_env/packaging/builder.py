from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path


def build_artifact(bundle_root: Path, output_dir: Path, profile: str, arch: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tarball_path = output_dir / f"red_env_{profile}_{arch}.tar.gz"
    checksum_path = output_dir / f"{tarball_path.name}.sha256"

    with tarfile.open(tarball_path, "w:gz") as archive:
        archive.add(bundle_root, arcname="red_env_offline")

    digest = hashlib.sha256(tarball_path.read_bytes()).hexdigest()
    checksum_path.write_text(f"{digest}  {tarball_path.name}\n", encoding="utf-8")
    return tarball_path, checksum_path
