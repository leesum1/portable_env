import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.archive_extract import apply_archive_extract


def test_apply_archive_extract_copies_named_binary(tmp_path: Path):
    archive_path = tmp_path / "tool.tar.gz"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with tarfile.open(archive_path, "w:gz") as tar:
        payload = b"#!/bin/sh\necho fzf\n"
        info = tarfile.TarInfo("fzf")
        info.size = len(payload)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(payload))

    package = PackageSpec(
        id="fzf",
        description="fzf",
        profiles=["core"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="junegunn/fzf"),
        strategy=StrategySpec(
            type="archive_extract",
            extract={"include": ["fzf"], "target_dir": "bin"},
        ),
    )

    outputs = apply_archive_extract(package, archive_path, bundle_root)
    assert outputs == [bundle_root / "bin" / "fzf"]
    assert (bundle_root / "bin" / "fzf").exists()


def test_apply_archive_extract_fails_if_include_missing(tmp_path: Path):
    archive_path = tmp_path / "tool.tar.gz"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with tarfile.open(archive_path, "w:gz") as tar:
        payload = b"#!/bin/sh\necho fzf\n"
        info = tarfile.TarInfo("fzf")
        info.size = len(payload)
        info.mode = 0o755
        tar.addfile(info, io.BytesIO(payload))

    package = PackageSpec(
        id="fzf",
        description="fzf",
        profiles=["core"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="junegunn/fzf"),
        strategy=StrategySpec(
            type="archive_extract",
            extract={"include": ["fzf", "picker"], "target_dir": "bin"},
        ),
    )

    with pytest.raises(ValueError, match="missing includes: picker"):
        apply_archive_extract(package, archive_path, bundle_root)


def test_apply_archive_extract_supports_zip_assets(tmp_path: Path):
    archive_path = tmp_path / "tool.zip"
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("yazi-x86_64-unknown-linux-musl/yazi", "#!/bin/sh\necho yazi\n")
        archive.writestr("yazi-x86_64-unknown-linux-musl/ya", "#!/bin/sh\necho ya\n")

    package = PackageSpec(
        id="yazi",
        description="yazi",
        profiles=["extended"],
        architectures=["x86_64"],
        source=SourceSpec(type="github_release", repo="sxyazi/yazi"),
        strategy=StrategySpec(
            type="archive_extract",
            extract={"include": ["ya", "yazi"], "target_dir": "bin"},
        ),
    )

    outputs = apply_archive_extract(package, archive_path, bundle_root)

    assert outputs == [bundle_root / "bin" / "yazi", bundle_root / "bin" / "ya"]
    assert (bundle_root / "bin" / "yazi").exists()
    assert (bundle_root / "bin" / "ya").exists()
