from pathlib import Path

from red_env.verification.docker import verifier_build_command


def test_verifier_build_command_uses_new_dockerfile_and_artifact_name(tmp_path: Path):
    artifact = tmp_path / "red_env_core_x86_64.tar.gz"
    artifact.write_text("tarball", encoding="utf-8")

    command = verifier_build_command(
        artifact=artifact,
        arch="x86_64",
        dockerfile=Path("docker/verifier.Dockerfile"),
    )

    assert command[:4] == ["docker", "buildx", "build", "--platform"]
    assert "linux/amd64" in command
    assert "docker/verifier.Dockerfile" in command
    assert str(artifact) in command
