from __future__ import annotations

from pathlib import Path

from red_env.verification.docker import run_verifier


def verify_command(args) -> int:
    artifact = Path(args.artifact)
    run_verifier(artifact, args.arch, Path(args.dockerfile))
    print(f"verified {artifact}")
    return 0
