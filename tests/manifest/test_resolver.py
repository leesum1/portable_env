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


def _make_package(package_id: str, profile_name: str) -> PackageSpec:
    return PackageSpec(
        id=package_id,
        description="package",
        profiles=[profile_name],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="owner/repo"),
        strategy=StrategySpec(type="direct_binary"),
    )


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
