from __future__ import annotations

import tomllib
from pathlib import Path

from red_env.manifest.models import BundleSpec, ManifestSpec, PackageSpec, ProfileSpec, SourceSpec, StrategySpec


def _read_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def load_manifest(manifest_root: Path) -> ManifestSpec:
    manifest_data = _read_toml(manifest_root / "manifest.toml")
    profiles_data = _read_toml(manifest_root / "profiles.toml")
    bundle_data = _read_toml(manifest_root / "bundle.toml")

    package_dir = manifest_root / manifest_data["package_dir"]
    packages: dict[str, PackageSpec] = {}
    for package_file in sorted(package_dir.glob("*.toml")):
        package_data = _read_toml(package_file)
        package = PackageSpec(
            id=package_data["id"],
            description=package_data["description"],
            profiles=list(package_data["profiles"]),
            architectures=list(package_data["architectures"]),
            source=SourceSpec(**package_data["source"]),
            strategy=StrategySpec(
                type=package_data["strategy"]["type"],
                match=dict(package_data["strategy"].get("match", {})),
                extract=dict(package_data["strategy"].get("extract", {})),
            ),
        )
        packages[package.id] = package

    profiles = {
        name: ProfileSpec(
            name=name,
            packages=list(data.get("packages", [])),
            extends=list(data.get("extends", [])),
        )
        for name, data in profiles_data["profiles"].items()
    }

    return ManifestSpec(
        manifest_version=int(manifest_data["manifest_version"]),
        bundle=BundleSpec(layout=dict(bundle_data["layout"])),
        profiles=profiles,
        packages=packages,
    )
