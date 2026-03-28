import io
import json
import tarfile
from pathlib import Path

from red_env.cli.app import main


def test_build_command_stages_tools_configs_installer_and_metadata(tmp_path: Path, monkeypatch):
    build_root = tmp_path / "build"
    dist_root = tmp_path / "dist"

    def fake_download(package, arch, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
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
        assert "red_env_offline/bundle/bin/zsh" in members
        assert "red_env_offline/configs/zsh/zshrc" in members
        assert "red_env_offline/installer/install.sh" in members
        assert "red_env_offline/bundle/bundle-manifest.json" in members

        manifest_payload = json.loads(
            archive.extractfile("red_env_offline/bundle/bundle-manifest.json").read().decode("utf-8")
        )
        assert manifest_payload["profile"] == "core"
        assert manifest_payload["arch"] == "x86_64"
        assert manifest_payload["packages"] == ["bat", "delta", "fd", "fzf", "rg", "zsh"]
