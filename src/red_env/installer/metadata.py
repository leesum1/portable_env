from __future__ import annotations

import json
from pathlib import Path


def write_bundle_metadata(
    bundle_root: Path,
    profile: str,
    arch: str,
    package_ids: list[str],
    installed_files: list[str],
) -> Path:
    bundle_root.mkdir(parents=True, exist_ok=True)
    metadata_path = bundle_root / "bundle-manifest.json"
    metadata_path.write_text(
        json.dumps(
            {
                "profile": profile,
                "arch": arch,
                "packages": package_ids,
                "installed_files": installed_files,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return metadata_path
