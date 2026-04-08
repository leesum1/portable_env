from __future__ import annotations

import shutil
import tarfile
from pathlib import Path

from red_env.manifest.models import PackageSpec


def _strip_path(path: str, strip_components: int) -> Path | None:
    parts = Path(path).parts
    if len(parts) <= strip_components:
        return None
    return Path(*parts[strip_components:])


def apply_archive_tree(package: PackageSpec, downloaded_asset: Path, bundle_root: Path) -> list[Path]:
    target_dir_value = package.strategy.extract.get("target_dir", "")
    strip_components = int(package.strategy.extract.get("strip_components", 0))
    target_root = bundle_root / target_dir_value if target_dir_value else bundle_root
    target_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    with tarfile.open(downloaded_asset, "r:*") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            relative_path = _strip_path(member.name, strip_components)
            if relative_path is None:
                continue
            target_path = target_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            extracted = archive.extractfile(member)
            assert extracted is not None
            with target_path.open("wb") as handle:
                shutil.copyfileobj(extracted, handle)
            target_path.chmod(member.mode or 0o644)
            written.append(target_path)

    return sorted(written)
