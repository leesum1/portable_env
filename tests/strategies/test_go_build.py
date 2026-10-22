import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.go_build import apply_go_build


def _make_source_tarball(path: Path) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name, payload in (
            ("fzf-main/go.mod", b"module github.com/junegunn/fzf\n"),
            ("fzf-main/go.sum", b""),
        ):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(payload))
    return path


def _make_package(extract: dict | None = None) -> PackageSpec:
    return PackageSpec(
        id="fzf",
        description="fzf",
        profiles=["core"],
        architectures=["x86_64", "arm64"],
        source=SourceSpec(type="github_release_source", repo="junegunn/fzf"),
        strategy=StrategySpec(type="go_build", extract=extract or {"target_dir": "bin", "binary_name": "fzf"}),
    )


def _successful_run(captured: dict | None = None):
    def fake_run(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args")
        if captured is not None:
            captured["cmd"] = cmd
            captured["env"] = dict(kwargs.get("env", {}))
        cwd = kwargs.get("cwd")
        if cwd is not None:
            binary_name = cmd[cmd.index("-o") + 1]
            (Path(cwd) / binary_name).write_bytes(b"fake binary")

    return fake_run


def test_apply_go_build_rejects_unsupported_arch(tmp_path: Path):
    archive_path = _make_source_tarball(tmp_path / "fzf.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError, match="unsupported architecture"):
        apply_go_build(_make_package(), archive_path, bundle_root, "sparc")


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


def test_apply_go_build_uses_persistent_cache_and_targets_the_requested_arch(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "fzf.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    cache_dir = tmp_path / "cache"

    captured: dict = {}
    monkeypatch.setattr("red_env.strategies.go_build.subprocess.run", _successful_run(captured))

    result = apply_go_build(_make_package(), archive_path, bundle_root, "arm64", cache_dir=cache_dir)

    assert captured["env"]["GOCACHE"] == str(cache_dir / "go-build")
    assert captured["env"]["GOMODCACHE"] == str(cache_dir / "go-mod")
    assert captured["env"]["CGO_ENABLED"] == "0"
    assert captured["env"]["GOOS"] == "linux"
    assert captured["env"]["GOARCH"] == "arm64"
    assert len(result) == 1
    assert result[0].exists()


def test_apply_go_build_pins_toolchain_and_module_graph(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "fzf.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    captured: dict = {}
    monkeypatch.setattr("red_env.strategies.go_build.subprocess.run", _successful_run(captured))

    package = _make_package({"target_dir": "bin", "binary_name": "fzf", "go_version": "1.27.3"})
    apply_go_build(package, archive_path, bundle_root, "x86_64")

    assert captured["env"]["GOTOOLCHAIN"] == "go1.27.3"
    assert captured["env"]["GOARCH"] == "amd64"
    assert "-mod=readonly" in captured["cmd"]
    assert "-trimpath" in captured["cmd"]
    assert "-buildvcs=false" in captured["cmd"]


def test_apply_go_build_allows_unlocked_build_when_opted_out(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "fzf.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    captured: dict = {}
    monkeypatch.setattr("red_env.strategies.go_build.subprocess.run", _successful_run(captured))

    package = _make_package({"target_dir": "bin", "binary_name": "fzf", "locked": False})
    apply_go_build(package, archive_path, bundle_root, "x86_64")

    assert "-mod=readonly" not in captured["cmd"]
