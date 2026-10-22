from __future__ import annotations

import tomllib
from pathlib import Path

from red_env.manifest.models import BundleSpec, ManifestSpec, PackageSpec, ProfileSpec, SourceSpec, StrategySpec

# Strategy types that compile from a source archive and therefore need a pinned
# toolchain version (filled from the manifest-level [toolchains] defaults).
_TOOLCHAIN_KEYS = {
    "zig_build": ("rust_version", "rust"),
    "go_build": ("go_version", "go"),
}


def _read_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _strategy_extract(package_data: dict, toolchains: dict[str, str]) -> dict[str, object]:
    strategy_data = package_data["strategy"]
    extract = dict(strategy_data.get("extract", {}))
    pinned_key = _TOOLCHAIN_KEYS.get(strategy_data["type"])
    if pinned_key is not None:
        package_key, default_key = pinned_key
        if not extract.get(package_key) and toolchains.get(default_key):
            extract[package_key] = toolchains[default_key]
    return extract


def load_manifest(manifest_root: Path) -> ManifestSpec:
    manifest_data = _read_toml(manifest_root / "manifest.toml")
    profiles_data = _read_toml(manifest_root / "profiles.toml")
    bundle_data = _read_toml(manifest_root / "bundle.toml")
    manifest_version = int(manifest_data["manifest_version"])
    if manifest_version != 1:
        raise ValueError(f"unsupported manifest_version: {manifest_version}")

    toolchains = {str(key): str(value) for key, value in manifest_data.get("toolchains", {}).items()}

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
                extract=_strategy_extract(package_data, toolchains),
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
        manifest_version=manifest_version,
        bundle=BundleSpec(layout=dict(bundle_data["layout"])),
        profiles=profiles,
        packages=packages,
        toolchains=toolchains,
    )
