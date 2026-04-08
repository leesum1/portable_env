from __future__ import annotations

import shutil
from pathlib import Path

from red_env.manifest.models import PackageSpec


def apply_direct_binary(package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
    target_dir = bundle_root / package.strategy.extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / package.strategy.extract.get("target_name", package.id)
    shutil.copy2(downloaded_asset, target_path)
    target_path.chmod(0o755)
    return [target_path]
