from __future__ import annotations

import shutil
from pathlib import Path

from red_env.manifest.models import PackageSpec


def apply_directory_copy(package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
    target_dir = bundle_root / package.strategy.extract["target_dir"]
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / downloaded_asset.name
    if downloaded_asset.is_dir():
        shutil.copytree(downloaded_asset, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(downloaded_asset, destination)
    return [destination]
