from __future__ import annotations

from pathlib import Path

from red_env.manifest.loader import load_manifest
from red_env.manifest.resolver import resolve_profile, validate_manifest
from red_env.packaging.builder import build_artifact


def build_command(args) -> int:
    manifest = load_manifest(Path(args.manifest_root))
    validate_manifest(manifest)
    package_ids = resolve_profile(manifest, args.profile)

    bundle_root = Path(args.build_root) / "work" / args.profile / args.arch / "bundle"
    (bundle_root / "bin").mkdir(parents=True, exist_ok=True)
    manifest_file = bundle_root / "selected-packages.txt"
    manifest_file.write_text("\n".join(package_ids) + "\n", encoding="utf-8")

    tarball_path, checksum_path = build_artifact(bundle_root, Path(args.dist_root), args.profile, args.arch)
    print(tarball_path)
    print(checksum_path)
    return 0
