import io
import json
import tarfile
import zipfile
from pathlib import Path

from red_env.cli.app import main


def test_build_command_stages_tools_configs_installer_and_metadata(tmp_path: Path, monkeypatch):
    build_root = tmp_path / "build"
    dist_root = tmp_path / "dist"

    def fake_download(package, arch, destination, manifest_root=None):
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(destination, "w:gz") as archive:
            files = {package.id: f"#!/bin/sh\necho {package.id}-{arch}\n".encode("utf-8")}
            if package.id == "zsh":
                # zsh is now a tarball archive copied as-is
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
        # zsh is now a tarball in zsh-bin/ directory (installed via romkatv/zsh-bin install script)
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
        assert manifest_payload["packages"] == ["bat", "delta", "fd", "fzf", "rg", "zsh", "zsh-bin-install-script"]
        assert manifest_payload["installed_files"] == [
            "bin/bat",
            "bin/delta",
            "bin/fd",
            "bin/fzf",
            "bin/rg",
        ]


def test_build_command_extended_profile_stages_offline_oh_my_zsh_runtime(tmp_path: Path, monkeypatch):
    build_root = tmp_path / "build"
    dist_root = tmp_path / "dist"

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
            # zsh is a tarball archive copied as-is
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
        if package.id == "yazi":
            with zipfile.ZipFile(destination, "w") as archive:
                archive.writestr("yazi-x86_64-unknown-linux-musl/ya", "#!/bin/sh\necho ya\n")
                archive.writestr("yazi-x86_64-unknown-linux-musl/yazi", "#!/bin/sh\necho yazi\n")
            return destination
        if package.id == "fastfetch":
            # fastfetch uses zip archives
            with zipfile.ZipFile(destination, "w") as archive:
                archive.writestr("fastfetch", "#!/bin/sh\necho fastfetch\n")
            return destination
        if package.id == "uv":
            # uv includes both uv and uvx
            with tarfile.open(destination, "w:gz") as archive:
                for name in ["uv", "uvx"]:
                    payload = f"#!/bin/sh\necho {name}\n".encode("utf-8")
                    info = tarfile.TarInfo(name)
                    info.size = len(payload)
                    info.mode = 0o755
                    archive.addfile(info, io.BytesIO(payload))
            return destination
        if package.id == "aichat":
            # aichat uses github_release + archive_extract
            with tarfile.open(destination, "w:gz") as archive:
                payload = b"#!/bin/sh\necho aichat\n"
                info = tarfile.TarInfo("aichat")
                info.size = len(payload)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(payload))
            return destination
        if package.id == "jq":
            # jq uses github_release + direct_binary
            destination.write_text("#!/bin/sh\necho jq\n", encoding="utf-8")
            return destination
        if package.id == "yq":
            # yq uses github_release + direct_binary
            destination.write_text("#!/bin/sh\necho yq\n", encoding="utf-8")
            return destination
        if package.id == "font-jetbrains-maple-mono":
            # font uses local_file + direct_binary
            destination.write_text("fake-ttf-font-data", encoding="utf-8")
            return destination
        if package.id == "forceterm":
            # forceterm uses local_file + direct_binary (AppImage)
            destination.write_text("fake-appimage-data", encoding="utf-8")
            return destination
        if package.id == "upx":
            # upx uses github_release + archive_extract with .tar.xz
            with tarfile.open(destination, "w:xz") as archive:
                payload = b"#!/bin/sh\necho upx\n"
                info = tarfile.TarInfo("upx")
                info.size = len(payload)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(payload))
            return destination
        if package.id == "crush":
            # crush uses github_release + archive_extract
            with tarfile.open(destination, "w:gz") as archive:
                payload = b"#!/bin/sh\necho crush\n"
                info = tarfile.TarInfo("crush")
                info.size = len(payload)
                info.mode = 0o755
                archive.addfile(info, io.BytesIO(payload))
            return destination
        if package.id == "opencode":
            # opencode uses archive_tree with single binary
            with tarfile.open(destination, "w:gz") as archive:
                payload = b"#!/bin/sh\necho opencode\n"
                info = tarfile.TarInfo("opencode")
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
        # zsh is now a tarball in zsh-bin/ directory
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
