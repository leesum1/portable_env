from __future__ import annotations

import re
from pathlib import Path

from red_env.verification.docker import run_verifier


def verify_command(args) -> int:
    artifact = Path(args.artifact)
    requested_arch = args.arch

    # Extract architecture from artifact filename (e.g., red_env_extended_x86_64.tar.gz)
    match = re.search(r'_(x86_64|aarch64|arm64)\.', artifact.name)
    if match:
        artifact_arch = match.group(1)
        # Normalize arm64 <-> aarch64
        if artifact_arch == "aarch64":
            artifact_arch = "arm64"
        if artifact_arch != requested_arch:
            raise ValueError(
                f"architecture mismatch: artifact '{artifact.name}' was built for '{artifact_arch}' "
                f"but verification requested '{requested_arch}'. Use '--arch {artifact_arch}' instead."
            )

    run_verifier(artifact, requested_arch, Path(args.dockerfile), interactive=args.interactive)
    if args.interactive:
        print(f"interactive verifier ready for {artifact}")
        return 0
    print(f"verified {artifact}")
    return 0
