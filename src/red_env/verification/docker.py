from __future__ import annotations

import subprocess
from pathlib import Path


def _platform_for_arch(arch: str) -> str:
    return {"x86_64": "linux/amd64", "arm64": "linux/arm64"}[arch]


def verifier_build_command(
    artifact: Path,
    arch: str,
    dockerfile: Path,
    *,
    include_artifact_path: bool = True,
) -> list[str]:
    command = [
        "docker",
        "buildx",
        "build",
        "--platform",
        _platform_for_arch(arch),
        "-f",
        str(dockerfile),
        "--build-arg",
        f"PACKAGE_FILE={artifact}",
        "--load",
        ".",
    ]
    if include_artifact_path:
        command.append(str(artifact))
    return command


def run_verifier(artifact: Path, arch: str, dockerfile: Path) -> None:
    subprocess.run(
        verifier_build_command(
            artifact,
            arch,
            dockerfile,
            include_artifact_path=False,
        ),
        check=True,
    )
