import io
import json
import tarfile
import zipfile
from pathlib import Path
from types import SimpleNamespace

from red_env.cli.app import main
from red_env.strategies.registry import STRATEGY_REGISTRY


def _fake_zig_build(package, downloaded_asset, bundle_root, arch, cache_dir=None):
    target_dir = bundle_root / package.strategy.extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    include = package.strategy.extract.get("include", [package.id])
    written = []
    for name in include:
        dest = target_dir / name
        dest.write_text(f"#!/bin/sh\necho {name}\n", encoding="utf-8")
        dest.chmod(0o755)
        written.append(dest)
    return written


def _fake_go_build(package, downloaded_asset, bundle_root, arch, cache_dir=None):
    target_dir = bundle_root / package.strategy.extract.get("target_dir", "bin")
    target_dir.mkdir(parents=True, exist_ok=True)
    binary_name = package.strategy.extract.get("binary_name", package.id)
    include = package.strategy.extract.get("include", [binary_name])
    written = []
    for name in include:
        dest = target_dir / name
        dest.write_text(f"#!/bin/sh\necho {name}\n", encoding="utf-8")
        dest.chmod(0o755)
        written.append(dest)
    return written


def test_build_command_stages_tools_configs_installer_and_metadata(tmp_path: Path, monkeypatch):
    build_root = tmp_path / "build"
    dist_root = tmp_path / "dist"

    monkeypatch.setitem(STRATEGY_REGISTRY, "zig_build", _fake_zig_build)
    monkeypatch.setitem(STRATEGY_REGISTRY, "go_build", _fake_go_build)

    def fake_download(package, arch, destination, manifest_root=None):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(destination, "w:gz") as archive:
            files = {package.id: f"#!/bin/sh\necho {package.id}-{arch}\n".encode("utf-8")}
            if package.id == "zsh":
                files = {
                    "zsh-5.8-linux-x86_64/bin/zsh": b"#!/bin/sh\necho zsh\n",
                    "zsh-5.8-linux-x86_64/share/zsh/5.8/functions/_red_env": b"#compdef red_env\n",
                    "zsh-5.8-linux-x86_64/install": b"#!/bin/sh\necho install\n",
                }
            for name, payload in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(payload)
                info.mode = 0o755 if name.endswith("zsh") or name.endswith("install") else 0o644
                archive.addfile(info, io.BytesIO(payload))
        return destination

    monkeypatch.setattr("red_env.cli.commands.build.download_package_asset", fake_download)

    exit_code = main(
        [
            "build",
            "--profile",
            "core",
            "--arch",
            "x86_64",
            "--manifest-root",
            "manifests",
            "--build-root",
            str(build_root),
            "--dist-root",
            str(dist_root),
        ]
    )

    assert exit_code == 0

    tarball_path = dist_root / "red_env_core_x86_64.tar.gz"
    assert tarball_path.exists()
    assert (dist_root / "red_env_core_x86_64.tar.gz.sha256").exists()

    with tarfile.open(tarball_path, "r:gz") as archive:
        members = set(archive.getnames())
        assert "red_env_offline/bundle/bin/fzf" in members
        assert "red_env_offline/bundle/bin/bat" in members
        assert "red_env_offline/bundle/bin/rg" in members
        assert "red_env_offline/bundle/bin/fd" in members
        assert "red_env_offline/bundle/bin/delta" in members
        assert "red_env_offline/bundle/zsh-bin/zsh-5.8-linux.tar.gz" in members
        assert "red_env_offline/bundle/zsh-bin/install" in members
        assert "red_env_offline/configs/zsh/zshrc" in members
        assert "red_env_offline/configs/zsh/.zshrc" in members
        assert "red_env_offline/installer/install.sh" in members
        assert "red_env_offline/bundle/bundle-manifest.json" in members

        manifest_payload = json.loads(
            archive.extractfile("red_env_offline/bundle/bundle-manifest.json").read().decode("utf-8")
        )
        assert manifest_payload["profile"] == "core"
        assert manifest_payload["arch"] == "x86_64"
        assert manifest_payload["packages"] == [
            "bat",
            "delta",
            "dust",
            "fd",
            "fish",
            "font-jetbrains-maple-mono",
            "fzf",
            "navi",
            "ouch",
            "rg",
            "ruff",
            "zellij",
            "zoxide",
            "zsh",
            "zsh-bin-install-script",
        ]
        assert manifest_payload["installed_files"] == [
            "bin/bat",
            "bin/delta",
            "bin/dust",
            "bin/fd",
            "bin/fish",
            "bin/fzf",
            "bin/navi",
            "bin/ouch",
            "bin/rg",
            "bin/ruff",
            "bin/zellij",
            "bin/zoxide",
        ]


def test_build_command_extended_profile_stages_offline_oh_my_zsh_runtime(tmp_path: Path, monkeypatch):
    build_root = tmp_path / "build"
    dist_root = tmp_path / "dist"

    monkeypatch.setitem(STRATEGY_REGISTRY, "zig_build", _fake_zig_build)
    monkeypatch.setitem(STRATEGY_REGISTRY, "go_build", _fake_go_build)

    def fake_download(package, arch, destination, manifest_root=None):
        destination.parent.mkdir(parents=True, exist_ok=True)
        strategy_type = package.strategy.type
        if package.id == "oh-my-zsh":
            with tarfile.open(destination, "w:gz") as archive:
                files = {
                    "ohmyzsh-master/oh-my-zsh.sh": b"# oh-my-zsh\n",
                    "ohmyzsh-master/lib/theme-and-appearance.zsh": b"# theme\n",
                }
                for name, payload in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.mode = 0o644
                    archive.addfile(info, io.BytesIO(payload))
            return destination
        if package.id == "zsh":
            with tarfile.open(destination, "w:gz") as archive:
                files = {
                    "zsh-5.8-linux-x86_64/bin/zsh": b"#!/bin/sh\necho zsh\n",
                    "zsh-5.8-linux-x86_64/share/zsh/5.8/functions/_red_env": b"#compdef red_env\n",
                    "zsh-5.8-linux-x86_64/install": b"#!/bin/sh\necho install\n",
                }
                for name, payload in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.mode = 0o755 if name.endswith("zsh") or name.endswith("install") else 0o644
                    archive.addfile(info, io.BytesIO(payload))
            return destination
        if strategy_type == "archive_tree":
            with tarfile.open(destination, "w:gz") as archive:
                files = {}
                if package.id == "zsh-bin-install-script":
                    files = {"install": b"#!/bin/sh\necho install\n"}
                else:
                    module_name = package.strategy.extract["target_dir"].split("/")[-1]
                    files = {f"{package.id}-master/{module_name}.plugin.zsh": b"# plugin\n"}
                for name, payload in files.items():
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.mode = 0o755 if name.endswith("zsh") else 0o644
                    archive.addfile(info, io.BytesIO(payload))
            return destination
        if package.id == "fish":
            with tarfile.open(destination, "w:xz") as archive:
                payload = b"#!/bin/sh\necho fish\n"
                info = tarfile.TarInfo("fish")
                info.size = len(payload)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(payload))
            return destination
        if package.id == "fastfetch":
            with zipfile.ZipFile(destination, "w") as archive:
                archive.writestr("fastfetch", "#!/bin/sh\necho fastfetch\n")
            return destination
        if package.id == "jq":
            destination.write_text("#!/bin/sh\necho jq\n", encoding="utf-8")
            return destination
        if package.id == "font-jetbrains-maple-mono":
            destination.write_text("fake-ttf-font-data", encoding="utf-8")
            return destination
        if package.id == "forceterm":
            destination.write_text("fake-appimage-data", encoding="utf-8")
            return destination
        if package.id == "upx":
            with tarfile.open(destination, "w:xz") as archive:
                payload = b"#!/bin/sh\necho upx\n"
                info = tarfile.TarInfo("upx")
                info.size = len(payload)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(payload))
            return destination
        with tarfile.open(destination, "w:gz") as archive:
            payload = f"#!/bin/sh\necho {package.id}-{arch}\n".encode("utf-8")
            info = tarfile.TarInfo(package.id)
            info.size = len(payload)
            info.mode = 0o755
            archive.addfile(info, io.BytesIO(payload))
        return destination

    monkeypatch.setattr("red_env.cli.commands.build.download_package_asset", fake_download)

    exit_code = main(
        [
            "build",
            "--profile",
            "extended",
            "--arch",
            "x86_64",
            "--manifest-root",
            "manifests",
            "--build-root",
            str(build_root),
            "--dist-root",
            str(dist_root),
        ]
    )

    assert exit_code == 0

    tarball_path = dist_root / "red_env_extended_x86_64.tar.gz"
    with tarfile.open(tarball_path, "r:gz") as archive:
        members = set(archive.getnames())
        assert "red_env_offline/bundle/zsh-bin/zsh-5.8-linux.tar.gz" in members
        assert "red_env_offline/bundle/zsh-bin/install" in members
        assert "red_env_offline/bundle/cache/oh-my-zsh/oh-my-zsh.sh" in members
        assert "red_env_offline/bundle/cache/oh-my-zsh/custom/plugins/zsh-autosuggestions/zsh-autosuggestions.plugin.zsh" in members
        assert "red_env_offline/bundle/cache/oh-my-zsh/custom/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.plugin.zsh" in members
        assert "red_env_offline/bundle/bin/zellij" in members
        assert "red_env_offline/bundle/bin/yazi" in members
        assert "red_env_offline/bundle/bin/ya" in members
        assert "red_env_offline/bundle/bin/fish" in members
        assert "red_env_offline/bundle/bin/eza" in members
        assert "red_env_offline/configs/zsh/.zshrc" in members

        manifest_payload = json.loads(
            archive.extractfile("red_env_offline/bundle/bundle-manifest.json").read().decode("utf-8")
        )
        assert "oh-my-zsh" in manifest_payload["packages"]
        assert "zsh" in manifest_payload["packages"]
        assert "zellij" in manifest_payload["packages"]
        assert "bin/zellij" in manifest_payload["installed_files"]

def _recording_strategies(seen: list):
    def recording_zig_build(package, downloaded_asset, bundle_root, arch, cache_dir=None):
        seen.append(cache_dir)
        return _fake_zig_build(package, downloaded_asset, bundle_root, arch, cache_dir)

    def recording_go_build(package, downloaded_asset, bundle_root, arch, cache_dir=None):
        seen.append(cache_dir)
        return _fake_go_build(package, downloaded_asset, bundle_root, arch, cache_dir)

    return recording_zig_build, recording_go_build


def _generic_download(package, arch, destination, manifest_root=None):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(destination, "w:gz") as archive:
        files = {package.id: f"#!/bin/sh\necho {package.id}-{arch}\n".encode("utf-8")}
        if package.id == "zsh":
            files = {
                "zsh-5.8-linux-x86_64/bin/zsh": b"#!/bin/sh\necho zsh\n",
                "zsh-5.8-linux-x86_64/install": b"#!/bin/sh\necho install\n",
            }
        for name, payload in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            info.mode = 0o755
            archive.addfile(info, io.BytesIO(payload))
    return destination


def _run_core_build(tmp_path: Path, monkeypatch, extra_args: list[str]):
    build_root = tmp_path / "build"
    dist_root = tmp_path / "dist"
    seen: list = []
    zig, go = _recording_strategies(seen)
    monkeypatch.setitem(STRATEGY_REGISTRY, "zig_build", zig)
    monkeypatch.setitem(STRATEGY_REGISTRY, "go_build", go)
    monkeypatch.setattr("red_env.cli.commands.build.download_package_asset", _generic_download)
    exit_code = main(
        [
            "build",
            "--profile",
            "core",
            "--arch",
            "x86_64",
            "--manifest-root",
            "manifests",
            "--build-root",
            str(build_root),
            "--dist-root",
            str(dist_root),
            *extra_args,
        ]
    )
    return exit_code, seen, build_root


def test_build_command_defaults_the_cache_outside_the_wiped_work_tree(tmp_path: Path, monkeypatch):
    exit_code, seen, build_root = _run_core_build(tmp_path, monkeypatch, [])

    assert exit_code == 0
    assert seen
    expected = (build_root / "cache").resolve()
    assert all(entry == expected for entry in seen), seen
    work_dir = (build_root / "work").resolve()
    assert work_dir not in expected.parents


def test_build_command_honours_a_shared_cache_root(tmp_path: Path, monkeypatch):
    shared = tmp_path / "shared-cache"
    exit_code, seen, _ = _run_core_build(tmp_path, monkeypatch, ["--cache-root", str(shared)])

    assert exit_code == 0
    assert seen
    assert all(entry == shared.resolve() for entry in seen), seen
    assert shared.is_dir()


def test_build_command_dispatches_to_the_docker_builder(tmp_path: Path, monkeypatch):
    calls: list = []
    monkeypatch.delenv("RED_ENV_IN_DOCKER", raising=False)
    monkeypatch.setattr(
        "red_env.packaging.docker_builder.run_build_in_docker",
        lambda args: calls.append(args) or 0,
    )

    from red_env.cli.commands.build import build_command

    exit_code = build_command(
        SimpleNamespace(profile="core", arch="x86_64", in_docker=True, manifest_root="manifests")
    )

    assert exit_code == 0
    assert len(calls) == 1


def test_build_command_does_not_recurse_inside_the_container(tmp_path: Path, monkeypatch):
    calls: list = []
    monkeypatch.setenv("RED_ENV_IN_DOCKER", "1")
    monkeypatch.setattr(
        "red_env.packaging.docker_builder.run_build_in_docker",
        lambda args: calls.append(args) or 0,
    )
    monkeypatch.setitem(STRATEGY_REGISTRY, "zig_build", _fake_zig_build)
    monkeypatch.setitem(STRATEGY_REGISTRY, "go_build", _fake_go_build)
    monkeypatch.setattr("red_env.cli.commands.build.download_package_asset", _generic_download)

    from red_env.cli.commands.build import build_command

    exit_code = build_command(
        SimpleNamespace(
            profile="core",
            arch="x86_64",
            in_docker=True,
            manifest_root="manifests",
            build_root=str(tmp_path / "build"),
            dist_root=str(tmp_path / "dist"),
            cache_root=None,
        )
    )

    assert exit_code == 0
    assert calls == []
