import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.zig_build import apply_zig_build


def _make_source_tarball(path: Path, extract_dir: str = "bat-0.24.0") -> Path:
    with tarfile.open(path, "w:gz") as archive:
        payload = b"fake-cargo-package\n"
        info = tarfile.TarInfo(f"{extract_dir}/Cargo.toml")
        info.size = len(payload)
        info.mode = 0o644
        archive.addfile(info, io.BytesIO(payload))
    return path


def _make_package() -> PackageSpec:
    return PackageSpec(
        id="bat",
        description="bat",
        profiles=["core"],
        architectures=["x86_64", "arm64"],
        source=SourceSpec(type="github_release_source", repo="sharkdp/bat"),
        strategy=StrategySpec(type="zig_build", extract={"include": ["bat"], "target_dir": "bin"}),
    )


def test_apply_zig_build_rejects_unsupported_arch(tmp_path: Path):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    with pytest.raises(ValueError, match="unsupported architecture"):
        apply_zig_build(_make_package(), archive_path, bundle_root, "sparc")


def test_apply_zig_build_raises_when_build_fails(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    def fake_run(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args[0] if args else ["cargo", "zigbuild"],
            output="",
            stderr="some linker error",
        )

    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", fake_run)

    with pytest.raises(RuntimeError, match="zig build failed for bat"):
        apply_zig_build(_make_package(), archive_path, bundle_root, "x86_64")


def test_apply_zig_build_sets_cache_dir(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    captured_env: dict[str, str] = {}

    def fake_run(*args, **kwargs):
        env = kwargs.get("env", {})
        captured_env.update(env)
        # Simulate a successful build by creating the expected binary
        cwd = kwargs.get("cwd")
        if cwd is not None:
            target_dir = Path(cwd) / "target" / "x86_64-unknown-linux-musl" / "release"
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "bat").write_bytes(b"fake binary")

    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", fake_run)

    result = apply_zig_build(_make_package(), archive_path, bundle_root, "x86_64")

    assert "CARGO_ZIGBUILD_CACHE_DIR" in captured_env
    assert len(result) == 1
    assert result[0].exists()