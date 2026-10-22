from pathlib import Path
from types import SimpleNamespace

import pytest

from red_env.fetchers.token import reset_token_cache
from red_env.packaging import docker_builder
from red_env.packaging.docker_builder import DockerBuildError, run_build_in_docker


def _args(workspace: Path, **overrides) -> SimpleNamespace:
    values = {
        "profile": "core",
        "arch": "x86_64",
        "manifest_root": str(workspace / "manifests"),
        "build_root": str(workspace / "build"),
        "dist_root": str(workspace / "dist"),
        "cache_root": None,
        "builder_image": "red-env-builder:test",
        "builder_dockerfile": None,
        "rebuild_builder": False,
        "in_docker": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class _Recorder:
    def __init__(self, image_present: bool = True):
        self.calls: list[list[str]] = []
        self.image_present = image_present

    def __call__(self, cmd, **kwargs):
        self.calls.append(list(cmd))
        if cmd[1:3] == ["image", "inspect"]:
            return SimpleNamespace(returncode=0 if self.image_present else 1)
        return SimpleNamespace(returncode=0)

    @property
    def run_call(self) -> list[str]:
        return next(call for call in self.calls if call[1] == "run")

    @property
    def build_calls(self) -> list[list[str]]:
        return [call for call in self.calls if call[1] == "build"]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "manifests").mkdir(parents=True)
    return root


def _install(monkeypatch, recorder: _Recorder) -> None:
    monkeypatch.setattr(docker_builder.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(docker_builder.subprocess, "run", recorder)
    # Keep the tests independent of the host's GitHub CLI: the token comes from
    # the environment instead of shelling out to `gh auth token`.
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


def test_run_build_in_docker_mounts_the_workspace_and_shares_the_cache(monkeypatch, workspace: Path):
    recorder = _Recorder()
    _install(monkeypatch, recorder)

    exit_code = run_build_in_docker(_args(workspace))

    assert exit_code == 0
    cmd = recorder.run_call
    assert cmd[0] == "/usr/bin/docker"
    assert cmd[2] == "--rm"
    assert cmd[3:5] == ["--network", "host"]
    assert cmd[5:7] == ["--platform", "linux/amd64"]
    assert f"{workspace}:/workspace" in cmd
    assert "--workdir" in cmd
    assert "RED_ENV_IN_DOCKER=1" in cmd
    assert "PYTHONPATH=/workspace/src" in cmd
    assert "CARGO_HOME=/workspace/build/cache/cargo" in cmd
    assert "CARGO_ZIGBUILD_CACHE_DIR=/workspace/build/cache/zig" in cmd
    assert "GOCACHE=/workspace/build/cache/go-build" in cmd
    assert "GOMODCACHE=/workspace/build/cache/go-mod" in cmd
    assert cmd[-3:] == ["sh", "-c", cmd[-1]]
    assert "--cache-root /workspace/build/cache" in cmd[-1]
    assert "--manifest-root /workspace/manifests" in cmd[-1]
    assert f"chown -R {docker_builder.os.getuid()}:{docker_builder.os.getgid()}" in cmd[-1]
    assert "red-env-builder:test" in cmd
    assert recorder.build_calls == []


def test_run_build_in_docker_maps_the_arm64_platform(monkeypatch, workspace: Path):
    recorder = _Recorder()
    _install(monkeypatch, recorder)

    run_build_in_docker(_args(workspace, arch="arm64"))

    assert recorder.run_call[5:7] == ["--platform", "linux/arm64"]


def test_run_build_in_docker_rejects_unsupported_architectures(monkeypatch, workspace: Path):
    _install(monkeypatch, _Recorder())

    with pytest.raises(DockerBuildError, match="unsupported architecture"):
        run_build_in_docker(_args(workspace, arch="riscv64"))


def test_run_build_in_docker_mounts_a_cache_outside_the_workspace(monkeypatch, workspace: Path, tmp_path: Path):
    recorder = _Recorder()
    _install(monkeypatch, recorder)
    shared_cache = tmp_path / "shared-cache"

    run_build_in_docker(_args(workspace, cache_root=str(shared_cache)))

    cmd = recorder.run_call
    assert f"{shared_cache}:/cache" in cmd
    assert "CARGO_HOME=/cache/cargo" in cmd
    assert "GOCACHE=/cache/go-build" in cmd
    assert "--cache-root /cache" in cmd[-1]


def test_run_build_in_docker_rejects_paths_outside_the_workspace(monkeypatch, workspace: Path, tmp_path: Path):
    _install(monkeypatch, _Recorder())

    with pytest.raises(DockerBuildError, match="outside the build workspace"):
        run_build_in_docker(_args(workspace, build_root=str(tmp_path / "elsewhere" / "build")))


def test_run_build_in_docker_builds_the_builder_image_when_missing(monkeypatch, workspace: Path):
    recorder = _Recorder(image_present=False)
    _install(monkeypatch, recorder)

    run_build_in_docker(_args(workspace))

    build_calls = recorder.build_calls
    assert len(build_calls) == 1
    assert "--tag" in build_calls[0]
    assert "red-env-builder:test" in build_calls[0]
    assert str(workspace / "docker") in build_calls[0]


def test_run_build_in_docker_rebuilds_the_image_when_requested(monkeypatch, workspace: Path):
    recorder = _Recorder(image_present=True)
    _install(monkeypatch, recorder)

    run_build_in_docker(_args(workspace, rebuild_builder=True))

    assert len(recorder.build_calls) == 1


def test_run_build_in_docker_defaults_to_host_networking(monkeypatch, workspace: Path):
    recorder = _Recorder()
    _install(monkeypatch, recorder)

    run_build_in_docker(_args(workspace))

    assert recorder.run_call[3:5] == ["--network", "host"]


def test_run_build_in_docker_honours_a_custom_network(monkeypatch, workspace: Path):
    recorder = _Recorder()
    _install(monkeypatch, recorder)

    run_build_in_docker(_args(workspace, docker_network="bridge"))

    assert recorder.run_call[3:5] == ["--network", "bridge"]


def test_run_build_in_docker_passes_the_network_to_the_image_build(monkeypatch, workspace: Path):
    recorder = _Recorder(image_present=False)
    _install(monkeypatch, recorder)

    run_build_in_docker(_args(workspace, docker_network="bridge"))

    build_cmd = recorder.build_calls[0]
    assert build_cmd[build_cmd.index("--network") + 1] == "bridge"


def test_run_build_in_docker_forwards_the_github_token_by_name(monkeypatch, workspace: Path):
    recorder = _Recorder()
    _install(monkeypatch, recorder)

    run_build_in_docker(_args(workspace))

    cmd = recorder.run_call
    assert "GH_TOKEN" in cmd
    # The secret must not leak into the command line.
    assert not any(part.startswith("GH_TOKEN=test-token") for part in cmd)
    assert cmd[cmd.index("GH_TOKEN") - 1] == "-e"


def test_run_build_in_docker_passes_the_token_through_the_environment(monkeypatch, workspace: Path):
    recorder = _Recorder()
    _install(monkeypatch, recorder)
    captured: dict[str, object] = {}
    original = recorder.__call__

    def recording(cmd, **kwargs):
        captured["env"] = kwargs.get("env")
        return original(cmd, **kwargs)

    monkeypatch.setattr(docker_builder.subprocess, "run", recording)

    run_build_in_docker(_args(workspace))

    assert captured["env"]["GH_TOKEN"] == "test-token"


def test_run_build_in_docker_works_without_a_token(monkeypatch, workspace: Path):
    recorder = _Recorder()
    monkeypatch.setattr(docker_builder.shutil, "which", lambda name: "/usr/bin/docker")
    monkeypatch.setattr(docker_builder.subprocess, "run", recorder)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(
        "red_env.fetchers.token.shutil.which",
        lambda name: "/usr/bin/docker" if name == "docker" else None,
    )
    reset_token_cache()

    assert run_build_in_docker(_args(workspace)) == 0
    assert "GH_TOKEN" in recorder.run_call
