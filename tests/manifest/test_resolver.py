import pytest

from red_env.manifest.models import (
    BundleSpec,
    ManifestSpec,
    PackageSpec,
    ProfileSpec,
    SourceSpec,
    StrategySpec,
)
from red_env.manifest.resolver import resolve_profile, validate_manifest


def _make_package_with_profiles(package_id: str, profile_names: list[str]) -> PackageSpec:
    return PackageSpec(
        id=package_id,
        description="package",
        profiles=profile_names,
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="owner/repo"),
        strategy=StrategySpec(type="direct_binary"),
    )


def _make_package(package_id: str, profile_name: str) -> PackageSpec:
    return _make_package_with_profiles(package_id, [profile_name])


def _make_manifest(
    profiles: dict[str, ProfileSpec],
    packages: dict[str, PackageSpec],
) -> ManifestSpec:
    return ManifestSpec(
        manifest_version=1,
        bundle=BundleSpec(layout={"bin": "bin"}),
        profiles=profiles,
        packages=packages,
    )


def test_resolve_profile_detects_cycles() -> None:
    profiles = {
        "a": ProfileSpec(name="a", packages=["pkg"], extends=["b"]),
        "b": ProfileSpec(name="b", packages=[], extends=["a"]),
    }
    manifest = _make_manifest(profiles, {"pkg": _make_package("pkg", "a")})

    with pytest.raises(ValueError) as excinfo:
        resolve_profile(manifest, "a")
    assert "cyclic profile inheritance" in str(excinfo.value)


def test_validate_manifest_rejects_unknown_package_profile() -> None:
    profiles = {"core": ProfileSpec(name="core", packages=[], extends=[])}
    manifest = _make_manifest(profiles, {"pkg": _make_package("pkg", "missing")})

    with pytest.raises(ValueError) as excinfo:
        validate_manifest(manifest)
    assert "package pkg references unknown profile missing" in str(excinfo.value)


def test_validate_manifest_detects_profile_package_mismatch() -> None:
    profiles = {"core": ProfileSpec(name="core", packages=["pkg"], extends=[])}
    manifest = _make_manifest(
        profiles,
        {
            "pkg": _make_package_with_profiles("pkg", []),
        },
    )

    with pytest.raises(ValueError) as excinfo:
        validate_manifest(manifest)
    assert "profile core lists package pkg but package does not declare it" in str(excinfo.value)


def test_validate_manifest_detects_cycles() -> None:
    profiles = {
        "a": ProfileSpec(name="a", packages=["pkg"], extends=["b"]),
        "b": ProfileSpec(name="b", packages=["pkg"], extends=["a"]),
    }
    manifest = _make_manifest(
        profiles,
        {"pkg": _make_package_with_profiles("pkg", ["a", "b"])},
    )

    with pytest.raises(ValueError) as excinfo:
        validate_manifest(manifest)
    assert "cyclic profile inheritance" in str(excinfo.value)


def test_validate_manifest_accepts_github_archive_source_and_archive_tree_strategy() -> None:
    manifest = _make_manifest(
        profiles={"extended": ProfileSpec(name="extended", packages=["plugin"], extends=[])},
        packages={
            "plugin": PackageSpec(
                id="plugin",
                description="plugin",
                profiles=["extended"],
                architectures=["x86_64"],
                source=SourceSpec(type="github_archive", repo="owner/plugin"),
                strategy=StrategySpec(
                    type="archive_tree",
                    extract={"target_dir": "cache/zim/modules/plugin", "strip_components": 1},
                ),
            )
        },
    )

    validate_manifest(manifest)
