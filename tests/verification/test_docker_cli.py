from pathlib import Path

from red_env.verification.docker import (
    prepare_verifier_context,
    run_verifier,
    verifier_build_command,
    verifier_run_command,
)


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

    def fake_run(command, check, capture_output=False):
        captured["command"] = command
        captured["check"] = check

    monkeypatch.setattr("red_env.verification.docker.subprocess.run", fake_run)

    run_verifier(artifact=artifact, arch="x86_64", dockerfile=dockerfile)

    command = captured["command"]
    assert captured["check"] is True
    assert f"PACKAGE_FILE={artifact.name}" in command
    assert command[-1] != "."


def test_verifier_run_command_launches_interactive_shell_for_arch():
    command = verifier_run_command(arch="x86_64", image_tag="red-env-verify:test")

    assert command == [
        "docker",
        "run",
        "--rm",
        "-it",
        "--init",
        "--security-opt",
        "seccomp=unconfined",
        "--platform",
        "linux/amd64",
        "-e",
        "PATH=/root/.red_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "-e",
        "LANG=en_US.UTF-8",
        "-e",
        "LC_ALL=en_US.UTF-8",
        "-e",
        "TERM=xterm-256color",
        "-e",
        "RED_ENV_DISABLE_ZSH_256COLOR=1",
        "-e",
        "RED_ENV_VERIFY_INTERACTIVE=1",
        "-e",
        "ZDOTDIR=/root/.red_env/configs/zsh",
        "--entrypoint",
        "sh",
        "red-env-verify:test",
        "-c",
        "stty erase '^?' kill '^U' intr '^C' eof '^D' sane; if [ -x /root/.red_env/bin/zsh ]; then exec /root/.red_env/bin/zsh -l -i; else exec bash -i; fi",
    ]


def test_run_verifier_interactive_builds_then_runs_shell(tmp_path: Path, monkeypatch):
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    artifact = outside_dir / "red_env_core_x86_64.tar.gz"
    artifact.write_text("tarball", encoding="utf-8")

    dockerfile_dir = tmp_path / "docker"
    dockerfile_dir.mkdir()
    dockerfile = dockerfile_dir / "verifier.Dockerfile"
    dockerfile.write_text("FROM scratch\nARG PACKAGE_FILE\nCOPY ${PACKAGE_FILE} /package.tar.gz\n", encoding="utf-8")

    captured: list[list[str]] = []

    def fake_run(command, check, capture_output=False):
        captured.append(command)

    monkeypatch.setattr("red_env.verification.docker.subprocess.run", fake_run)

    run_verifier(artifact=artifact, arch="x86_64", dockerfile=dockerfile, interactive=True)

    assert len(captured) == 2
    assert captured[0][:3] == ["docker", "buildx", "build"]
    assert "-t" in captured[0]
    assert captured[1] == [
        "docker",
        "run",
        "--rm",
        "-it",
        "--init",
        "--security-opt",
        "seccomp=unconfined",
        "--platform",
        "linux/amd64",
        "-e",
        "PATH=/root/.red_env/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "-e",
        "LANG=en_US.UTF-8",
        "-e",
        "LC_ALL=en_US.UTF-8",
        "-e",
        "TERM=xterm-256color",
        "-e",
        "RED_ENV_DISABLE_ZSH_256COLOR=1",
        "-e",
        "RED_ENV_VERIFY_INTERACTIVE=1",
        "-e",
        "ZDOTDIR=/root/.red_env/configs/zsh",
        "--entrypoint",
        "sh",
        captured[0][captured[0].index("-t") + 1],
        "-c",
        "stty erase '^?' kill '^U' intr '^C' eof '^D' sane; if [ -x /root/.red_env/bin/zsh ]; then exec /root/.red_env/bin/zsh -l -i; else exec bash -i; fi",
    ]


def test_run_verifier_interactive_does_not_require_zero_exit_from_shell(tmp_path: Path, monkeypatch):
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    artifact = outside_dir / "red_env_core_x86_64.tar.gz"
    artifact.write_text("tarball", encoding="utf-8")

    dockerfile_dir = tmp_path / "docker"
    dockerfile_dir.mkdir()
    dockerfile = dockerfile_dir / "verifier.Dockerfile"
    dockerfile.write_text("FROM scratch\nARG PACKAGE_FILE\nCOPY ${PACKAGE_FILE} /package.tar.gz\n", encoding="utf-8")

    checks: list[bool] = []

    def fake_run(command, check, capture_output=False):
        checks.append(check)

    monkeypatch.setattr("red_env.verification.docker.subprocess.run", fake_run)

    run_verifier(artifact=artifact, arch="x86_64", dockerfile=dockerfile, interactive=True)

    assert checks == [True, False]


def test_verifier_dockerfile_uses_bundle_metadata_not_hardcoded_binary_names():
    dockerfile = Path("docker/verifier.Dockerfile").read_text(encoding="utf-8")

    assert "bundle-manifest.json" in dockerfile
    assert "installed_files" in dockerfile
    assert "fzf" not in dockerfile


def test_verifier_dockerfile_installs_vim_and_checks_zsh_startup():
    dockerfile = Path("docker/verifier.Dockerfile").read_text(encoding="utf-8")

    assert "vim" in dockerfile
    assert "zsh -i -c" in dockerfile
    assert "oh-my-zsh.sh" in dockerfile
    assert "ZDOTDIR=/root/.red_env/configs/zsh" in dockerfile


def test_verifier_run_command_sets_utf8_locale_for_interactive_shell():
    command = verifier_run_command(arch="x86_64", image_tag="red-env-verify:test")

    assert "LANG=en_US.UTF-8" in command
    assert "LC_ALL=en_US.UTF-8" in command
    assert "TERM=xterm-256color" in command
    assert "RED_ENV_DISABLE_ZSH_256COLOR=1" in command
    assert "RED_ENV_VERIFY_INTERACTIVE=1" in command
