from pathlib import Path

import pytest

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import validate_manifest


def _write_tree(
    root: Path,
    *,
    toolchains: dict[str, str] | None = None,
    package_body: str = "",
    strategy_type: str = "zig_build",
    source_type: str = "github_release_source",
    extract_body: str = "",
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "packages").mkdir(exist_ok=True)
    toolchain_block = ""
    if toolchains is not None:
        entries = "\n".join(f'{key} = "{value}"' for key, value in toolchains.items())
        toolchain_block = f"\n[toolchains]\n{entries}\n"
    (root / "manifest.toml").write_text(
        f'manifest_version = 1\npackage_dir = "packages"\n{toolchain_block}',
        encoding="utf-8",
    )
    (root / "bundle.toml").write_text(
        '[layout]\nbin = "bin"\nshare = "share"\nconfigs = "configs"\ncache = "cache"\nfonts = "fonts"\n',
        encoding="utf-8",
    )
    (root / "profiles.toml").write_text(
        '[profiles.core]\npackages = ["tool"]\n',
        encoding="utf-8",
    )
    (root / "packages" / "tool.toml").write_text(
        f'''id = "tool"
description = "tool"
profiles = ["core"]
architectures = ["x86_64", "arm64"]

[source]
type = "{source_type}"
repo = "owner/tool"

[strategy]
type = "{strategy_type}"
{package_body}
[strategy.extract]
target_dir = "bin"
{extract_body}
''',
        encoding="utf-8",
    )
    return root


def test_loader_injects_manifest_toolchain_defaults(tmp_path: Path):
    root = _write_tree(tmp_path / "manifests", toolchains={"rust": "1.99.1", "go": "1.27.3"})

    manifest = load_manifest(root)

    assert manifest.toolchains == {"rust": "1.99.1", "go": "1.27.3"}
    assert manifest.packages["tool"].strategy.extract["rust_version"] == "1.99.1"
    validate_manifest(manifest)


def test_loader_injects_go_version_for_go_build(tmp_path: Path):
    root = _write_tree(
        tmp_path / "manifests",
        toolchains={"rust": "1.99.1", "go": "1.27.3"},
        strategy_type="go_build",
        extract_body='binary_name = "tool"',
    )

    manifest = load_manifest(root)

    assert manifest.packages["tool"].strategy.extract["go_version"] == "1.27.3"
    assert "rust_version" not in manifest.packages["tool"].strategy.extract
    validate_manifest(manifest)


def test_package_level_pin_overrides_the_manifest_default(tmp_path: Path):
    root = _write_tree(
        tmp_path / "manifests",
        toolchains={"rust": "1.99.1"},
        extract_body='rust_version = "1.85.0"',
    )

    manifest = load_manifest(root)

    assert manifest.packages["tool"].strategy.extract["rust_version"] == "1.85.0"


def test_loader_does_not_inject_pins_into_non_build_strategies(tmp_path: Path):
    root = _write_tree(
        tmp_path / "manifests",
        toolchains={"rust": "1.99.1", "go": "1.27.3"},
        strategy_type="direct_binary",
        source_type="github_release",
        extract_body='include = ["tool"]',
    )

    manifest = load_manifest(root)

    extract = manifest.packages["tool"].strategy.extract
    assert "rust_version" not in extract
    assert "go_version" not in extract


def test_resolver_rejects_source_build_without_a_pinned_toolchain(tmp_path: Path):
    root = _write_tree(tmp_path / "manifests")

    manifest = load_manifest(root)

    with pytest.raises(ValueError, match="must pin rust_version for zig_build builds"):
        validate_manifest(manifest)


def test_resolver_rejects_source_build_with_a_binary_source(tmp_path: Path):
    root = _write_tree(
        tmp_path / "manifests",
        toolchains={"rust": "1.99.1"},
        source_type="github_release",
    )

    manifest = load_manifest(root)

    with pytest.raises(ValueError, match="does not provide a source archive"):
        validate_manifest(manifest)


def test_resolver_rejects_non_boolean_locked_flag(tmp_path: Path):
    root = _write_tree(
        tmp_path / "manifests",
        toolchains={"rust": "1.99.1"},
        extract_body='locked = "yes"',
    )

    manifest = load_manifest(root)

    with pytest.raises(ValueError, match="locked must be a boolean"):
        validate_manifest(manifest)
