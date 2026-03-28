from __future__ import annotations

from red_env.manifest.models import ManifestSpec


def validate_manifest(manifest: ManifestSpec) -> None:
    for profile in manifest.profiles.values():
        for package_id in profile.packages:
            if package_id not in manifest.packages:
                raise ValueError(f"profile {profile.name} references unknown package {package_id}")
        for parent in profile.extends:
            if parent not in manifest.profiles:
                raise ValueError(f"profile {profile.name} extends unknown profile {parent}")

    for package in manifest.packages.values():
        if package.source.type != "github_release":
            raise ValueError(f"unsupported source type: {package.source.type}")
        if package.strategy.type not in {"direct_binary", "archive_extract", "directory_copy"}:
            raise ValueError(f"unsupported strategy type: {package.strategy.type}")


def resolve_profile(manifest: ManifestSpec, profile_name: str) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []

    def visit(name: str) -> None:
        profile = manifest.profiles[name]
        for parent in profile.extends:
            visit(parent)
        for package_id in profile.packages:
            if package_id not in seen:
                seen.add(package_id)
                ordered.append(package_id)

    if profile_name not in manifest.profiles:
        raise ValueError(f"unknown profile: {profile_name}")
    visit(profile_name)
    return sorted(ordered)
