from __future__ import annotations

from pathlib import Path


def release_command(args) -> int:
    artifact = Path(args.artifact)
    checksum = Path(f"{artifact}.sha256")
    if not artifact.exists() or not checksum.exists():
        raise FileNotFoundError("artifact and checksum must exist before release")
    print(artifact)
    print(checksum)
    return 0
