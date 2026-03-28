from __future__ import annotations

from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import validate_manifest


def lint_command(args) -> int:
    manifest = load_manifest(Path(args.manifest_root))
    validate_manifest(manifest)
    print(f"manifest ok: {len(manifest.packages)} packages")
    return 0
