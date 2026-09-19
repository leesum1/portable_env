import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.go_build import apply_go_build


def _make_source_tarball(path: Path) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        payload = b"package main\n"
        info = tarfile.TarInfo("fzf-main/go.mod")
        info.size = len(payload)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(payload))
    return path


def _make_package() -> PackageSpec:
    return PackageSpec(
        id="fzf",
        description="fzf",
        profiles=["core"],
        architectures=["x86_64", "arm64"],
        source=SourceSpec(type="github_release_source", repo="junegunn/fzf"),
        strategy=StrategySpec(type="go_build", extract={"target_dir": "bin", "binary_name": "fzf"}),
    )


def test_apply_go_build_raises_when_build_fails(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "fzf.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args[0] if args else ["go", "build"],
            output="",
            stderr="compilation error",
        )

    monkeypatch.setattr("red_env.strategies.go_build.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="go build failed for fzf"):
        apply_go_build(_make_package(), archive_path, bundle_root, "x86_64")


def test_apply_go_build_sets_cache_dirs(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "fzf.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    captured_env: dict[str, str] = {}

    def fake_run(*args, **kwargs):
        env = kwargs.get("env", {})
        captured_env.update(env)
        # Simulate a successful build by creating the expected binary
        cwd = kwargs.get("cwd")
        if cwd is not None:
            binary_name = args[0][args[0].index("-o") + 1]
            (Path(cwd) / binary_name).write_bytes(b"fake binary")

    monkeypatch.setattr("red_env.strategies.go_build.subprocess.run", fake_run)

    result = apply_go_build(_make_package(), archive_path, bundle_root, "x86_64")

    assert "GOCACHE" in captured_env
    assert "GOMODCACHE" in captured_env
    assert "CGO_ENABLED" in captured_env
    assert captured_env["CGO_ENABLED"] == "0"
    assert len(result) == 1
    assert result[0].exists()