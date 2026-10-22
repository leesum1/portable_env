from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest


def test_repo_manifests_define_core_profile_with_expected_packages():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "core") == [
        "bat",
        "delta",
        "dust",
        "fd",
        "fish",
        "font-jetbrains-maple-mono",
        "fzf",
        "navi",
        "ouch",
        "rg",
        "ruff",
        "zellij",
        "zoxide",
        "zsh",
        "zsh-bin-install-script",
    ]


def test_repo_manifests_define_extended_profile_with_modern_tooling():
    manifest = load_manifest(Path("manifests"))
    validate_manifest(manifest)

    assert resolve_profile(manifest, "extended") == [
        "bat",
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


def test_repo_manifests_pin_the_source_build_toolchains():
    manifest = load_manifest(Path("manifests"))

    assert manifest.toolchains == {"rust": "1.99.1", "go": "1.27.3"}

    for package in manifest.packages.values():
        if package.strategy.type == "zig_build":
            assert package.strategy.extract["rust_version"] == "1.99.1", package.id
        if package.strategy.type == "go_build":
            assert package.strategy.extract["go_version"] == "1.27.3", package.id
