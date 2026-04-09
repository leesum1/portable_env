from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest


def test_repo_manifests_define_core_profile_with_expected_packages():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "core") == ["bat", "delta", "fd", "fzf", "rg", "zsh", "zsh-bin-install-script"]


def test_repo_manifests_define_extended_profile_with_modern_tooling():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "extended") == [
        "aichat",
        "bat",
        "crush",
        "delta",
        "duf",
        "dust",
        "eza",
        "fastfetch",
        "fd",
        "fish",
        "font-jetbrains-maple-mono",
        "forceterm",
        "fzf",
        "glow",
        "jq",
        "lazygit",
        "navi",
        "oh-my-zsh",
        "oh-my-zsh-z",
        "oh-my-zsh-zsh-autosuggestions",
        "oh-my-zsh-zsh-syntax-highlighting",
        "opencode",
        "ouch",
        "rg",
        "ruff",
        "upx",
        "uv",
        "yazi",
        "yq",
        "zellij",
        "zoxide",
        "zsh",
        "zsh-bin-install-script",
    ]
