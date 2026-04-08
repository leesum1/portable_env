from pathlib import Path

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.direct_binary import apply_direct_binary


def test_apply_direct_binary_supports_custom_target_name_and_directory(tmp_path: Path):
    downloaded_asset = tmp_path / "zimfw.zsh"
    downloaded_asset.write_text("# zimfw\n", encoding="utf-8")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    package = PackageSpec(
        id="zimfw",
        description="zimfw",
        profiles=["extended"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="zimfw/zimfw"),
        strategy=StrategySpec(
            type="direct_binary",
            extract={"target_dir": "cache/zim", "target_name": "zimfw.zsh"},
        ),
    )

    outputs = apply_direct_binary(package, downloaded_asset, bundle_root)

    assert outputs == [bundle_root / "cache" / "zim" / "zimfw.zsh"]
    assert (bundle_root / "cache" / "zim" / "zimfw.zsh").read_text(encoding="utf-8") == "# zimfw\n"
