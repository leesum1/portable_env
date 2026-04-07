from __future__ import annotations

from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest


def show_command(args) -> int:
    manifest = load_manifest(Path(args.manifest_root))
    validate_manifest(manifest)
    for package_id in resolve_profile(manifest, args.profile_name):
        print(package_id)
    return 0
