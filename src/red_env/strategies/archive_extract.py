from __future__ import annotations

import shutil
import tarfile
from pathlib import Path

from red_env.manifest.models import PackageSpec


def apply_archive_extract(package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
    target_dir = bundle_root / package.strategy.extract["target_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    include = set(package.strategy.extract["include"])
    written: list[Path] = []

    with tarfile.open(downloaded_asset, "r:*") as archive:
        for member in archive.getmembers():
            member_name = Path(member.name).name
            if member_name not in include or not member.isfile():
                continue
            extracted = archive.extractfile(member)
            assert extracted is not None
            target_path = target_dir / member_name
            with target_path.open("wb") as handle:
                shutil.copyfileobj(extracted, handle)
            target_path.chmod(member.mode or 0o755)
            written.append(target_path)

    return written
