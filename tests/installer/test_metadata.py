import json
from pathlib import Path

from red_env.installer.metadata import write_bundle_metadata


def test_write_bundle_metadata_records_profile_arch_and_packages(tmp_path: Path):
    metadata_path = write_bundle_metadata(
        bundle_root=tmp_path,
        profile="core",
        arch="x86_64",
        package_ids=["fzf", "bat", "rg"],
    )

    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert payload["profile"] == "core"
    assert payload["arch"] == "x86_64"
    assert payload["packages"] == ["fzf", "bat", "rg"]
