import json
import os
from pathlib import Path

from red_env.installer.metadata import write_bundle_metadata


def test_write_bundle_metadata_records_profile_arch_and_packages(tmp_path: Path):
    bundle_root = tmp_path / "bundle"
    metadata_path = write_bundle_metadata(
        bundle_root=bundle_root,
        profile="core",
        arch="x86_64",
        package_ids=["fzf", "bat", "rg"],
    )

    assert metadata_path == bundle_root / "bundle-manifest.json"
    assert bundle_root.exists()

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["profile"] == "core"
    assert payload["arch"] == "x86_64"
    assert payload["packages"] == ["fzf", "bat", "rg"]


def test_installer_scripts_are_executable():
    repo_root = Path(__file__).resolve().parents[2]
    installer_assets = repo_root / "assets" / "installer"
    for script in ("install.sh", "uninstall.sh"):
        script_path = installer_assets / script
        assert script_path.exists()
        assert os.access(script_path, os.X_OK)
