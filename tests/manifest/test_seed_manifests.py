from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest


def test_repo_manifests_define_core_profile_with_expected_packages():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "core") == ["bat", "delta", "fd", "fzf", "rg", "zsh"]
