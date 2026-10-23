import io
import tarfile
from pathlib import Path

import pytest

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.archive_tree import apply_archive_tree


def test_apply_archive_tree_extracts_full_tree_with_stripped_prefix(tmp_path: Path):
    archive_path = tmp_path / "fish.tar.xz"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with tarfile.open(archive_path, "w:xz") as archive:
        files = {
            "fish-4.6.0/bin/fish": b"#!/bin/sh\necho fish\n",
            "fish-4.6.0/share/fish/config.fish": b"set -g fish_greeting\n",
        }
        for name, payload in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o755 if name.endswith("/fish") else 0o644
            archive.addfile(info, io.BytesIO(payload))

    package = PackageSpec(
        id="fish",
        description="fish",
        profiles=["extended"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="fish-shell/fish-shell"),
        strategy=StrategySpec(
            type="archive_tree",
            extract={"target_dir": "fish", "strip_components": 1},
        ),
    )

    outputs = apply_archive_tree(package, archive_path, bundle_root, "x86_64")

    assert outputs == [
        bundle_root / "fish" / "bin" / "fish",
        bundle_root / "fish" / "share" / "fish" / "config.fish",
    ]
    assert (bundle_root / "fish" / "bin" / "fish").exists()
    assert (bundle_root / "fish" / "share" / "fish" / "config.fish").exists()


def _write_plugin_archive(archive_path: Path, entry: str) -> None:
    with tarfile.open(archive_path, "w:gz") as archive:
        payload = b"# plugin\n"
        info = tarfile.TarInfo(f"zsh-z-master/{entry}")
        info.size = len(payload)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(payload))


def _z_package(links: object = None) -> PackageSpec:
    extract: dict[str, object] = {
        "target_dir": "cache/oh-my-zsh/custom/plugins/z",
        "strip_components": 1,
    }
    if links is not None:
        extract["links"] = links
    return PackageSpec(
        id="oh-my-zsh-z",
        description="z plugin",
        profiles=["core"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_archive", repo="agkozak/zsh-z"),
        strategy=StrategySpec(type="archive_tree", extract=extract),
    )


def test_apply_archive_tree_exposes_a_plugin_entry_point_under_its_expected_name(tmp_path: Path):
    archive_path = tmp_path / "z.tar.gz"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    _write_plugin_archive(archive_path, "zsh-z.plugin.zsh")

    apply_archive_tree(
        _z_package(links={"z.plugin.zsh": "zsh-z.plugin.zsh"}),
        archive_path,
        bundle_root,
        "x86_64",
    )

    plugin_dir = bundle_root / "cache" / "oh-my-zsh" / "custom" / "plugins" / "z"
    link = plugin_dir / "z.plugin.zsh"
    assert link.is_symlink()
    assert link.readlink() == Path("zsh-z.plugin.zsh")
    assert link.exists()


def test_apply_archive_tree_rejects_a_link_to_a_missing_file(tmp_path: Path):
    archive_path = tmp_path / "z.tar.gz"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    _write_plugin_archive(archive_path, "zsh-z.plugin.zsh")

    with pytest.raises(ValueError, match="does not exist in the extracted tree"):
        apply_archive_tree(
            _z_package(links={"z.plugin.zsh": "missing.plugin.zsh"}),
            archive_path,
            bundle_root,
            "x86_64",
        )


def test_apply_archive_tree_rejects_a_malformed_links_table(tmp_path: Path):
    archive_path = tmp_path / "z.tar.gz"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    _write_plugin_archive(archive_path, "zsh-z.plugin.zsh")

    with pytest.raises(ValueError, match="expects extract.links to be a table"):
        apply_archive_tree(
            _z_package(links=["z.plugin.zsh"]),
            archive_path,
            bundle_root,
            "x86_64",
        )
