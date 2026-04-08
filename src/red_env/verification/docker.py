from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
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


def verifier_build_command(
    *,
    arch: str,
    dockerfile: Path,
    package_file: str,
    context_dir: Path,
    image_tag: str | None = None,
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
        f"PACKAGE_FILE={package_file}",
        "--load",
        str(context_dir),
    ]
    if image_tag is not None:
        command[-1:-1] = ["-t", image_tag]
    return command


def verifier_image_tag(arch: str) -> str:
    return f"red-env-verify:{arch}-{uuid.uuid4().hex[:12]}"


def verifier_run_command(*, arch: str, image_tag: str) -> list[str]:
    return [
        "docker",
        "run",
        "--rm",
        "-it",
        "--platform",
        _platform_for_arch(arch),
        "-e",
        "PATH=/root/.red_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "-e",
        "ZDOTDIR=/root/.red_env/configs/zsh",
        "-e",
        "TERMINFO_DIRS=/etc/terminfo:/lib/terminfo:/usr/share/terminfo",
        "-e",
        "TERM=xterm-256color",
        "-e",
        "RED_ENV_DISABLE_ZSH_256COLOR=1",
        "--entrypoint",
        "zsh",
        image_tag,
        "-l",
        "-c",
        "stty erase '\\177' && exec zsh -l",
    ]


def run_verifier(artifact: Path, arch: str, dockerfile: Path, interactive: bool = False) -> None:
    with tempfile.TemporaryDirectory(prefix="red-env-verify-") as temp_dir:
        staged = prepare_verifier_context(artifact, dockerfile, Path(temp_dir))
        image_tag = verifier_image_tag(arch)
        subprocess.run(
            verifier_build_command(
                arch=arch,
                dockerfile=staged.dockerfile_path,
                package_file=staged.artifact_name,
                context_dir=staged.context_dir,
                image_tag=image_tag,
            ),
            check=True,
        )
        if interactive:
            subprocess.run(
                verifier_run_command(arch=arch, image_tag=image_tag),
                check=False,
            )
