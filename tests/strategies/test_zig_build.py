import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from red_env.manifest.models import PackageSpec, SourceSpec, StrategySpec
from red_env.strategies.zig_build import apply_zig_build


def _make_source_tarball(
    path: Path,
    extract_dir: str = "bat-0.24.0",
    with_lock: bool = True,
    extra_files: dict[str, bytes] | None = None,
) -> Path:
    files = {f"{extract_dir}/Cargo.toml": b"fake-cargo-package\n"}
    if with_lock:
        files[f"{extract_dir}/Cargo.lock"] = b'version = 3\n'
    files.update(extra_files or {})
    with tarfile.open(path, "w:gz") as archive:
        for name, payload in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(payload))
    return path


def _make_package(extract: dict | None = None) -> PackageSpec:
    return PackageSpec(
        id="bat",
        description="bat",
        profiles=["core"],
        architectures=["x86_64", "arm64"],
        source=SourceSpec(type="github_release_source", repo="sharkdp/bat"),
        strategy=StrategySpec(type="zig_build", extract=extract or {"include": ["bat"], "target_dir": "bin"}),
    )


def _successful_run(captured: dict | None = None):
    def fake_run(*args, **kwargs):
        if captured is not None:
            captured["cmd"] = args[0] if args else kwargs.get("args")
            captured["env"] = dict(kwargs.get("env", {}))
        cwd = kwargs.get("cwd")
        if cwd is not None:
            target_dir = Path(cwd) / "target" / "x86_64-unknown-linux-musl" / "release"
            target_dir.mkdir(parents=True, exist_ok=True)
            (target_dir / "bat").write_bytes(b"fake binary")

    return fake_run


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


def test_apply_zig_build_uses_persistent_cache(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    cache_dir = tmp_path / "cache"

    captured: dict = {}
    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", _successful_run(captured))

    result = apply_zig_build(_make_package(), archive_path, bundle_root, "x86_64", cache_dir=cache_dir)

    assert captured["env"]["CARGO_HOME"] == str(cache_dir / "cargo")
    assert captured["env"]["CARGO_ZIGBUILD_CACHE_DIR"] == str(cache_dir / "zig")
    assert captured["env"]["CARGO_INCREMENTAL"] == "0"
    assert len(result) == 1
    assert result[0].exists()


def test_apply_zig_build_passes_locked_when_lock_file_present(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    captured: dict = {}
    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", _successful_run(captured))

    apply_zig_build(_make_package(), archive_path, bundle_root, "x86_64")

    assert "--locked" in captured["cmd"]


def test_apply_zig_build_requires_lock_file_by_default(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz", with_lock=False)
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", _successful_run())

    with pytest.raises(RuntimeError, match="requires a Cargo.lock"):
        apply_zig_build(_make_package(), archive_path, bundle_root, "x86_64")


def test_apply_zig_build_allows_unlocked_build_when_opted_out(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz", with_lock=False)
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    captured: dict = {}
    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", _successful_run(captured))

    package = _make_package({"include": ["bat"], "target_dir": "bin", "locked": False})
    apply_zig_build(package, archive_path, bundle_root, "x86_64")

    assert "--locked" not in captured["cmd"]


def test_apply_zig_build_runs_pinned_toolchain_through_rustup(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    captured: dict = {}
    monkeypatch.setattr("red_env.strategies.zig_build.shutil.which", lambda name: "/usr/bin/rustup")
    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", _successful_run(captured))

    package = _make_package({"include": ["bat"], "target_dir": "bin", "rust_version": "1.99.1"})
    apply_zig_build(package, archive_path, bundle_root, "x86_64")

    assert captured["cmd"][:4] == ["rustup", "run", "1.99.1", "cargo"]
    assert "--locked" in captured["cmd"]


def test_apply_zig_build_rejects_mismatched_host_cargo(tmp_path: Path, monkeypatch):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    monkeypatch.setattr("red_env.strategies.zig_build.shutil.which", lambda name: None)
    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", _successful_run())

    def fake_version(*args, **kwargs):
        return subprocess.CompletedProcess(args=["cargo", "--version"], returncode=0, stdout="cargo 1.81.0 (abc 2024-01-01)\n")

    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", fake_version)

    package = _make_package({"include": ["bat"], "target_dir": "bin", "rust_version": "1.99.1"})
    with pytest.raises(RuntimeError, match="pinned Rust toolchain 1.99.1"):
        apply_zig_build(package, archive_path, bundle_root, "x86_64")


def test_apply_zig_build_drops_pinned_toolchain_file(tmp_path: Path, monkeypatch):
    """Upstreams pinning rust-toolchain.toml would otherwise make rustup pick a
    channel that lacks the musl target, failing with "can't find crate for core"."""
    archive_path = _make_source_tarball(
        tmp_path / "navi.tar.gz",
        extract_dir="navi-2.23.0",
        extra_files={"navi-2.23.0/rust-toolchain.toml": b'[toolchain]\nchannel = "1.81.0"\n'},
    )
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    seen_pinned_file: list[bool] = []

    def fake_run(*args, **kwargs):
        cwd = Path(kwargs["cwd"])
        seen_pinned_file.append((cwd / "rust-toolchain.toml").exists())
        target_dir = cwd / "target" / "x86_64-unknown-linux-musl" / "release"
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "bat").write_bytes(b"fake binary")

    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", fake_run)

    result = apply_zig_build(_make_package(), archive_path, bundle_root, "x86_64")

    assert seen_pinned_file == [False]
    assert result[0].exists()


def test_apply_zig_build_reports_a_missing_rustup_toolchain(monkeypatch, tmp_path: Path):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()

    monkeypatch.setattr("red_env.strategies.zig_build.shutil.which", lambda _name: "/usr/bin/rustup")

    def fake_run(command, **kwargs):
        if command[:3] == ["rustup", "toolchain", "list"]:
            return subprocess.CompletedProcess(
                command, 0, stdout="1.81.0-x86_64-unknown-linux-gnu (default)\n", stderr=""
            )
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        apply_zig_build(_make_package({"rust_version": "1.99.1"}), archive_path, bundle_root, "x86_64")

    message = str(excinfo.value)
    assert "pinned Rust toolchain 1.99.1 is not installed" in message
    assert "rustup toolchain install 1.99.1" in message
    assert "--in-docker" in message


def test_apply_zig_build_accepts_an_installed_rustup_toolchain(monkeypatch, tmp_path: Path):
    archive_path = _make_source_tarball(tmp_path / "bat.tar.gz")
    bundle_root = tmp_path / "bundle"
    bundle_root.mkdir()
    captured: dict[str, object] = {}

    monkeypatch.setattr("red_env.strategies.zig_build.shutil.which", lambda _name: "/usr/bin/rustup")

    def fake_run(command, **kwargs):
        if command[:3] == ["rustup", "toolchain", "list"]:
            return subprocess.CompletedProcess(
                command, 0, stdout="1.99.1-x86_64-unknown-linux-gnu\n1.81.0-x86_64-unknown-linux-gnu\n", stderr=""
            )
        return _successful_run(captured)(command, **kwargs)

    monkeypatch.setattr("red_env.strategies.zig_build.subprocess.run", fake_run)

    apply_zig_build(_make_package({"rust_version": "1.99.1"}), archive_path, bundle_root, "x86_64")

    assert captured["cmd"][:4] == ["rustup", "run", "1.99.1", "cargo"]
