from pathlib import Path

from red_env.verification.docker import prepare_verifier_context, run_verifier, verifier_build_command


def test_prepare_verifier_context_stages_outside_artifact_into_context(tmp_path: Path):
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    artifact = outside_dir / "red_env_core_x86_64.tar.gz"
    artifact.write_text("tarball", encoding="utf-8")

    dockerfile_dir = tmp_path / "docker"
    dockerfile_dir.mkdir()
    dockerfile = dockerfile_dir / "verifier.Dockerfile"
    dockerfile.write_text("FROM scratch\nARG PACKAGE_FILE\nCOPY ${PACKAGE_FILE} /package.tar.gz\n", encoding="utf-8")

    context_dir = tmp_path / "context"
    context_dir.mkdir()

    staged = prepare_verifier_context(
        artifact=artifact,
        dockerfile=dockerfile,
        context_dir=context_dir,
    )

    assert staged.context_dir == context_dir
    assert staged.artifact_name == "red_env_core_x86_64.tar.gz"
    assert (context_dir / staged.artifact_name).read_text(encoding="utf-8") == "tarball"
    assert staged.dockerfile_path == context_dir / "verifier.Dockerfile"


def test_verifier_build_command_uses_staged_context_and_relative_artifact_name(tmp_path: Path):
    context_dir = tmp_path / "context"
    context_dir.mkdir()
    dockerfile = context_dir / "verifier.Dockerfile"
    dockerfile.write_text("FROM scratch\n", encoding="utf-8")

    command = verifier_build_command(
        arch="x86_64",
        dockerfile=dockerfile,
        package_file="red_env_core_x86_64.tar.gz",
        context_dir=context_dir,
    )

    assert command == [
        "docker",
        "buildx",
        "build",
        "--platform",
        "linux/amd64",
        "-f",
        str(dockerfile),
        "--build-arg",
        "PACKAGE_FILE=red_env_core_x86_64.tar.gz",
        "--load",
        str(context_dir),
    ]


def test_run_verifier_builds_using_staged_context_for_outside_artifact(tmp_path: Path, monkeypatch):
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    artifact = outside_dir / "red_env_core_x86_64.tar.gz"
    artifact.write_text("tarball", encoding="utf-8")

    dockerfile_dir = tmp_path / "docker"
    dockerfile_dir.mkdir()
    dockerfile = dockerfile_dir / "verifier.Dockerfile"
    dockerfile.write_text("FROM scratch\nARG PACKAGE_FILE\nCOPY ${PACKAGE_FILE} /package.tar.gz\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_run(command, check):
        captured["command"] = command
        captured["check"] = check

    monkeypatch.setattr("red_env.verification.docker.subprocess.run", fake_run)

    run_verifier(artifact=artifact, arch="x86_64", dockerfile=dockerfile)

    command = captured["command"]
    assert captured["check"] is True
    assert f"PACKAGE_FILE={artifact.name}" in command
    assert command[-1] != "."


def test_verifier_dockerfile_uses_bundle_metadata_not_hardcoded_binary_names():
    dockerfile = Path("docker/verifier.Dockerfile").read_text(encoding="utf-8")

    assert "bundle-manifest.json" in dockerfile
    assert "fzf" not in dockerfile
