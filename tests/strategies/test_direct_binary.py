from pathlib import Path

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.direct_binary import apply_direct_binary


def test_apply_direct_binary_supports_custom_target_name_and_directory(tmp_path: Path):
    downloaded_asset = tmp_path / "tool.bin"
    downloaded_asset.write_text("# tool\n", encoding="utf-8")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    package = PackageSpec(
        id="some-tool",
        description="some tool",
        profiles=["extended"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="some/tool"),
        strategy=StrategySpec(
            type="direct_binary",
            extract={"target_dir": "cache/tools", "target_name": "tool.bin"},
        ),
    )

    outputs = apply_direct_binary(package, downloaded_asset, bundle_root)

    assert outputs == [bundle_root / "cache" / "tools" / "tool.bin"]
    assert (bundle_root / "cache" / "tools" / "tool.bin").read_text(encoding="utf-8") == "# tool\n"


def test_apply_direct_binary_copies_asset_as_is(tmp_path: Path):
    downloaded_asset = tmp_path / "archive.tar.gz"
    downloaded_asset.write_text("# fake archive\n", encoding="utf-8")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    package = PackageSpec(
        id="tool",
        description="tool archive",
        profiles=["core"],
        architectures=["x86_64", "arm64"],
        source=SourceSpec(type="local_file", repo="local/tool", file_path="tool.tar.gz"),
        strategy=StrategySpec(
            type="direct_binary",
            extract={"target_dir": "tool-dir", "target_name": "tool.tar.gz"},
        ),
    )

    outputs = apply_direct_binary(package, downloaded_asset, bundle_root)

    assert outputs == [bundle_root / "tool-dir" / "tool.tar.gz"]
    assert (bundle_root / "tool-dir" / "tool.tar.gz").read_text(encoding="utf-8") == "# fake archive\n"
