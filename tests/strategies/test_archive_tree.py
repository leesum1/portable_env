import io
import tarfile
from pathlib import Path

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

    outputs = apply_archive_tree(package, archive_path, bundle_root)

    assert outputs == [
        bundle_root / "fish" / "bin" / "fish",
        bundle_root / "fish" / "share" / "fish" / "config.fish",
    ]
    assert (bundle_root / "fish" / "bin" / "fish").exists()
    assert (bundle_root / "fish" / "share" / "fish" / "config.fish").exists()
