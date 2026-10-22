from __future__ import annotations

from red_env.manifest.models import ManifestSpec

_SOURCE_TYPES = {"github_release", "github_release_source", "github_archive", "local_file"}
_STRATEGY_TYPES = {
    "direct_binary",
    "archive_extract",
    "archive_tree",
    "directory_copy",
    "zig_build",
    "go_build",
}
_SOURCE_BUILD_STRATEGIES = {"zig_build", "go_build"}
_SOURCE_ARCHIVE_TYPES = {"github_release_source", "github_archive"}
_PINNED_TOOLCHAIN_KEYS = {"zig_build": "rust_version", "go_build": "go_version"}


def validate_manifest(manifest: ManifestSpec) -> None:
    for profile in manifest.profiles.values():
        for package_id in profile.packages:
            if package_id not in manifest.packages:
                raise ValueError(f"profile {profile.name} references unknown package {package_id}")
            package = manifest.packages[package_id]
            if profile.name not in package.profiles:
                raise ValueError(
                    f"profile {profile.name} lists package {package_id} but package does not declare it"
                )
        for parent in profile.extends:
            if parent not in manifest.profiles:
                raise ValueError(f"profile {profile.name} extends unknown profile {parent}")

    for package in manifest.packages.values():
        for profile_name in package.profiles:
            if profile_name not in manifest.profiles:
                raise ValueError(f"package {package.id} references unknown profile {profile_name}")
            profile = manifest.profiles[profile_name]
            if package.id not in profile.packages:
                raise ValueError(
                    f"package {package.id} declares profile {profile_name} but profile does not list it"
                )
        if package.source.type not in _SOURCE_TYPES:
            raise ValueError(f"unsupported source type: {package.source.type}")
        if package.strategy.type not in _STRATEGY_TYPES:
            raise ValueError(f"unsupported strategy type: {package.strategy.type}")
        _validate_source_build(package)

    _ensure_no_profile_cycles(manifest)


def _validate_source_build(package) -> None:
    if package.strategy.type not in _SOURCE_BUILD_STRATEGIES:
        return
    if package.source.type not in _SOURCE_ARCHIVE_TYPES:
        raise ValueError(
            f"package {package.id} uses {package.strategy.type} but source type {package.source.type} "
            "does not provide a source archive"
        )
    pinned_key = _PINNED_TOOLCHAIN_KEYS[package.strategy.type]
    pinned_value = package.strategy.extract.get(pinned_key)
    if not isinstance(pinned_value, str) or not pinned_value.strip():
        raise ValueError(
            f"package {package.id} must pin {pinned_key} for {package.strategy.type} builds; "
            f"set [toolchains] in manifest.toml or {pinned_key} in the package strategy extract"
        )
    locked = package.strategy.extract.get("locked", True)
    if not isinstance(locked, bool):
        raise ValueError(f"package {package.id}: strategy.extract.locked must be a boolean")


def resolve_profile(manifest: ManifestSpec, profile_name: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    if profile_name not in manifest.profiles:
        raise ValueError(f"unknown profile: {profile_name}")

    _ensure_no_profile_cycles(manifest)

    def visit(name: str) -> None:
        profile = manifest.profiles[name]
        for parent in profile.extends:
            visit(parent)
        for package_id in profile.packages:
            if package_id not in seen:
                seen.add(package_id)
                ordered.append(package_id)

    visit(profile_name)
    return sorted(ordered)


def _ensure_no_profile_cycles(manifest: ManifestSpec) -> None:
    visited: set[str] = set()
    stack: list[str] = []

    def visit(name: str) -> None:
        if name in stack:
            cycle = stack[stack.index(name):] + [name]
            raise ValueError(f"cyclic profile inheritance: {' -> '.join(cycle)}")
        if name in visited:
            return
        stack.append(name)
        profile = manifest.profiles[name]
        for parent in profile.extends:
            if parent not in manifest.profiles:
                raise ValueError(f"profile {profile.name} extends unknown profile {parent}")
            visit(parent)
        stack.pop()
        visited.add(name)

    for profile_name in manifest.profiles:
        visit(profile_name)
