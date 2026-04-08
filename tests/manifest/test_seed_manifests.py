from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest


def test_repo_manifests_define_core_profile_with_expected_packages():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "core") == ["bat", "delta", "fd", "fzf", "rg", "zsh"]


def test_repo_manifests_define_extended_profile_with_modern_tooling():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "extended") == [
        "bat",
        "delta",
        "eza",
        "fd",
        "fish",
        "fzf",
        "navi",
        "ouch",
        "rg",
        "yazi",
        "zellij",
        "zimfw",
        "zimfw-asciiship",
        "zimfw-chrissicool-zsh-256color",
        "zimfw-completion",
        "zimfw-duration-info",
        "zimfw-environment",
        "zimfw-git",
        "zimfw-git-info",
        "zimfw-input",
        "zimfw-pvenv",
        "zimfw-utility",
        "zimfw-zsh-autosuggestions",
        "zimfw-zsh-completions",
        "zimfw-zsh-history-substring-search",
        "zimfw-zsh-syntax-highlighting",
        "zimfw-zsh-z",
        "zsh",
    ]
