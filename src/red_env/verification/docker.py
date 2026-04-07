from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


def _platform_for_arch(arch: str) -> str:
    return {"x86_64": "linux/amd64", "arm64": "linux/arm64"}[arch]


@dataclass(frozen=True)
class VerifierContext:
    context_dir: Path
    dockerfile_path: Path
    artifact_name: str


def prepare_verifier_context(artifact: Path, dockerfile: Path, context_dir: Path) -> VerifierContext:
    if not artifact.exists():
        raise FileNotFoundError(f"artifact not found: {artifact}")
    if not dockerfile.exists():
        raise FileNotFoundError(f"dockerfile not found: {dockerfile}")

    context_dir.mkdir(parents=True, exist_ok=True)
    staged_artifact = context_dir / artifact.name
    staged_dockerfile = context_dir / dockerfile.name
    shutil.copy2(artifact, staged_artifact)
    shutil.copy2(dockerfile, staged_dockerfile)
    return VerifierContext(
        context_dir=context_dir,
        dockerfile_path=staged_dockerfile,
        artifact_name=staged_artifact.name,
    )


def verifier_build_command(*, arch: str, dockerfile: Path, package_file: str, context_dir: Path) -> list[str]:
    return [
        "docker",
        "buildx",
        "build",
        "--platform",
        _platform_for_arch(arch),
        "-f",
        str(dockerfile),
        "--build-arg",
        f"PACKAGE_FILE={package_file}",
        "--load",
        str(context_dir),
    ]


def run_verifier(artifact: Path, arch: str, dockerfile: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="red-env-verify-") as temp_dir:
        staged = prepare_verifier_context(artifact, dockerfile, Path(temp_dir))
        subprocess.run(
            verifier_build_command(
                arch=arch,
                dockerfile=staged.dockerfile_path,
                package_file=staged.artifact_name,
                context_dir=staged.context_dir,
            ),
            check=True,
        )
