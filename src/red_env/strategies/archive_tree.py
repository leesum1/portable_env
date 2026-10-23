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


def _create_links(target_root: Path, links: object, package_id: str) -> list[Path]:
    if not links:
        return []
    if not isinstance(links, dict):
        raise ValueError(
            f"archive_tree for {package_id} expects extract.links to be a table of "
            f"link name to target, got {type(links).__name__}"
        )

    created: list[Path] = []
    for link_name, target_name in links.items():
        link_path = target_root / str(link_name)
        target_path = target_root / str(target_name)
        if not target_path.exists():
            raise ValueError(
                f"archive_tree for {package_id} cannot link {link_name} to {target_name}: "
                f"{target_path} does not exist in the extracted tree"
            )
        if link_path.is_symlink() or link_path.exists():
            link_path.unlink()
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(Path(target_name))
        created.append(link_path)
    return created


def apply_archive_tree(
    package: PackageSpec,
    downloaded_asset: Path,
    bundle_root: Path,
    arch: str,
    cache_dir: Path | None = None,
) -> list[Path]:
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

    written.extend(_create_links(target_root, package.strategy.extract.get("links"), package.id))
    return sorted(written)
