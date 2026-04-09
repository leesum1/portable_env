from __future__ import annotations

import shutil
from pathlib import Path

from red_env.fetchers.github_release import download_package_asset
from red_env.installer.metadata import write_bundle_metadata
from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest
from red_env.packaging.builder import build_artifact
from red_env.packaging.layout import BuildLayout
from red_env.strategies.registry import STRATEGY_REGISTRY


def _download_destination(package_id: str, strategy_type: str, downloads_dir: Path, arch: str) -> Path:
    extension = ".tar.gz" if strategy_type in {"archive_extract", "archive_tree"} else ".bin"
    return downloads_dir / f"{package_id}-{arch}{extension}"


def _download_suffix(args_arch: str, package) -> str:
    if package.source.type in {"github_archive", "local_file"}:
        return ".tar.gz"
    if package.strategy.type == "direct_binary":
        return ".bin"
    match = package.strategy.match.get(args_arch, "")
    lowered = match.lower()
    if ".zip" in lowered:
        return ".zip"
    if ".tar.xz" in lowered:
        return ".tar.xz"
    if package.strategy.type in {"archive_extract", "archive_tree"}:
        return ".tar.gz"
    return ".bin"


def _stage_static_assets(manifest_root: Path, offline_root: Path) -> None:
    assets_root = manifest_root.parent / "assets"
    configs_src = assets_root / "configs"
    installer_src = assets_root / "installer"
    if not configs_src.exists():
        raise FileNotFoundError(f"missing static configs: {configs_src}")
    if not installer_src.exists():
        raise FileNotFoundError(f"missing installer assets: {installer_src}")
    shutil.copytree(configs_src, offline_root / "configs", dirs_exist_ok=True)
    shutil.copytree(installer_src, offline_root / "installer", dirs_exist_ok=True)


def _installed_files(bundle_root: Path) -> list[str]:
    bin_root = bundle_root / "bin"
    if not bin_root.exists():
        return []
    return sorted(str(path.relative_to(bundle_root)) for path in bin_root.rglob("*") if path.is_file())


def build_command(args) -> int:
    manifest_root = Path(args.manifest_root)
    manifest = load_manifest(manifest_root)
    validate_manifest(manifest)
    package_ids = resolve_profile(manifest, args.profile)
    layout = BuildLayout(Path(args.build_root), args.profile, args.arch)

    if layout.work_dir.exists():
        shutil.rmtree(layout.work_dir)

    offline_root = layout.bundle_dir
    downloads_dir = layout.downloads_dir
    bundle_root = offline_root / "bundle"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    bundle_root.mkdir(parents=True, exist_ok=True)

    for relative_dir in manifest.bundle.layout.values():
        (bundle_root / relative_dir).mkdir(parents=True, exist_ok=True)

    for package_id in package_ids:
        package = manifest.packages[package_id]
        if args.arch not in package.architectures:
            raise ValueError(f"package {package.id} does not support architecture {args.arch}")

        destination = downloads_dir / f"{package.id}-{args.arch}{_download_suffix(args.arch, package)}"
        downloaded_asset = download_package_asset(package, args.arch, destination, manifest_root.resolve())
        strategy_handler = STRATEGY_REGISTRY[package.strategy.type]
        strategy_handler(package, downloaded_asset, bundle_root)

    _stage_static_assets(manifest_root.resolve(), offline_root)
    write_bundle_metadata(
        bundle_root,
        args.profile,
        args.arch,
        package_ids,
        _installed_files(bundle_root),
    )
    (bundle_root / "selected-packages.txt").write_text("\n".join(package_ids) + "\n", encoding="utf-8")

    tarball_path, checksum_path = build_artifact(offline_root, Path(args.dist_root), args.profile, args.arch)
    print(tarball_path)
    print(checksum_path)
    return 0
