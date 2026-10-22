from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from red_env.fetchers.token import github_token

DEFAULT_BUILDER_IMAGE = "red-env-builder:full"
DEFAULT_BUILDER_DOCKERFILE = Path("docker") / "builder-full.Dockerfile"
# Builds and the builder container only need outbound network access. Host
# networking keeps them working on machines where the daemon cannot create
# veth pairs (missing ``veth`` kernel module, restricted CI sandboxes), while
# bridge networking fails there with "failed to add the host <=> sandbox pair".
DEFAULT_DOCKER_NETWORK = "host"

_PLATFORM_MAP = {
    "x86_64": "linux/amd64",
    "arm64": "linux/arm64",
}


class DockerBuildError(RuntimeError):
    pass


def _docker_binary() -> str:
    docker = shutil.which("docker")
    if docker is None:
        raise DockerBuildError("docker is required for --in-docker builds but was not found on PATH")
    return docker


def _container_path(path: Path, workspace: Path) -> str:
    try:
        relative = path.resolve().relative_to(workspace)
    except ValueError as exc:
        raise DockerBuildError(
            f"{path} is outside the build workspace {workspace}. --in-docker only supports paths inside "
            "the repository, because the workspace is the only directory bind-mounted into the container."
        ) from exc
    return "/workspace" if relative == Path(".") else f"/workspace/{relative.as_posix()}"


def image_exists(image: str, docker: str = "docker") -> bool:
    completed = subprocess.run(
        [docker, "image", "inspect", image], capture_output=True, text=True, check=False
    )
    return completed.returncode == 0


def build_builder_image(
    image: str,
    dockerfile: Path,
    docker: str = "docker",
    build_args: dict[str, str] | None = None,
    network: str = DEFAULT_DOCKER_NETWORK,
) -> None:
    cmd = [docker, "build", "--network", network, "--file", str(dockerfile), "--tag", image]
    for key, value in (build_args or {}).items():
        cmd.extend(["--build-arg", f"{key}={value}"])
    cmd.append(str(dockerfile.parent))
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        raise DockerBuildError(f"failed to build builder image {image} from {dockerfile}")


def run_build_in_docker(args) -> int:
    """Run ``red_env build`` inside the hermetic builder image.

    The workspace is bind-mounted at /workspace and the toolchain cache at
    /cache so that rebuilds reuse downloaded registries. The container runs as
    root (the image installs its toolchains as root) and hands the produced
    files back to the invoking user afterwards.
    """
    docker = _docker_binary()
    platform = _PLATFORM_MAP.get(args.arch)
    if platform is None:
        raise DockerBuildError(f"unsupported architecture for docker builds: {args.arch}")

    manifest_root = Path(args.manifest_root).resolve()
    workspace = manifest_root.parent
    build_root = Path(args.build_root).resolve()
    dist_root = Path(args.dist_root).resolve()
    cache_root = Path(args.cache_root).resolve() if getattr(args, "cache_root", None) else build_root / "cache"

    build_root.mkdir(parents=True, exist_ok=True)
    dist_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)

    image = getattr(args, "builder_image", None) or DEFAULT_BUILDER_IMAGE
    dockerfile_arg = getattr(args, "builder_dockerfile", None)
    dockerfile = Path(dockerfile_arg).resolve() if dockerfile_arg else workspace / DEFAULT_BUILDER_DOCKERFILE
    network = getattr(args, "docker_network", None) or DEFAULT_DOCKER_NETWORK
    if getattr(args, "rebuild_builder", False) or not image_exists(image, docker):
        build_builder_image(image, dockerfile, docker, network=network)

    container_build_root = _container_path(build_root, workspace)
    container_dist_root = _container_path(dist_root, workspace)

    volumes = ["--volume", f"{workspace}:/workspace"]
    if cache_root.is_relative_to(workspace):
        container_cache_root = _container_path(cache_root, workspace)
    else:
        container_cache_root = "/cache"
        volumes.extend(["--volume", f"{cache_root}:/cache"])

    inner = [
        "python",
        "-m",
        "red_env",
        "build",
        "--profile",
        args.profile,
        "--arch",
        args.arch,
        "--manifest-root",
        _container_path(manifest_root, workspace),
        "--build-root",
        container_build_root,
        "--dist-root",
        container_dist_root,
        "--cache-root",
        container_cache_root,
    ]

    # The container writes as root; give the files back to the invoking user so
    # the next host-side build can clean and overwrite them.
    chown = f"chown -R {os.getuid()}:{os.getgid()} {shlex.quote(container_build_root)} {shlex.quote(container_dist_root)}"
    script = f"{shlex.join(inner)}; status=$?; {chown} >/dev/null 2>&1 || true; exit $status"

    # The container has no access to the host's `gh` credentials, so forward the
    # resolved token by name. Passing it by name (instead of `-e GH_TOKEN=...`)
    # keeps the secret out of the process command line.
    container_env = dict(os.environ)
    token = github_token()
    if token:
        container_env["GH_TOKEN"] = token

    cmd = [
        docker,
        "run",
        "--rm",
        "--network",
        network,
        "--platform",
        platform,
        *volumes,
        "--workdir",
        "/workspace",
        "-e",
        "RED_ENV_IN_DOCKER=1",
        "-e",
        "PYTHONPATH=/workspace/src",
        "-e",
        "GH_TOKEN",
        "-e",
        "CARGO_INCREMENTAL=0",
        "-e",
        f"CARGO_HOME={container_cache_root}/cargo",
        "-e",
        f"CARGO_ZIGBUILD_CACHE_DIR={container_cache_root}/zig",
        "-e",
        f"GOCACHE={container_cache_root}/go-build",
        "-e",
        f"GOMODCACHE={container_cache_root}/go-mod",
        image,
        "sh",
        "-c",
        script,
    ]
    return subprocess.run(cmd, check=False, env=container_env).returncode
