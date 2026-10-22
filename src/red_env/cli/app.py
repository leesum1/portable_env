from __future__ import annotations

import argparse
from typing import Sequence

from red_env.cli.commands.build import build_command
from red_env.cli.commands.manifest import lint_command
from red_env.cli.commands.profile import show_command
from red_env.cli.commands.release import release_command
from red_env.cli.commands.verify import verify_command



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="red_env")
    subparsers = parser.add_subparsers(dest="command")

    manifest_parser = subparsers.add_parser("manifest")
    manifest_subcommands = manifest_parser.add_subparsers(dest="manifest_command")
    lint_parser = manifest_subcommands.add_parser("lint")
    lint_parser.add_argument("--manifest-root", default="manifests")
    lint_parser.set_defaults(handler=lint_command)

    profile_parser = subparsers.add_parser("profile")
    profile_subcommands = profile_parser.add_subparsers(dest="profile_command")
    show_parser = profile_subcommands.add_parser("show")
    show_parser.add_argument("profile_name")
    show_parser.add_argument("--manifest-root", default="manifests")
    show_parser.set_defaults(handler=show_command)

    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--profile", required=True)
    build_parser.add_argument("--arch", required=True)
    build_parser.add_argument("--manifest-root", default="manifests")
    build_parser.add_argument("--build-root", default="build")
    build_parser.add_argument("--dist-root", default="dist")
    build_parser.add_argument(
        "--cache-root",
        default=None,
        help="Directory for reusable toolchain caches (defaults to <build-root>/cache).",
    )
    build_parser.add_argument(
        "--in-docker",
        action="store_true",
        help="Run the build inside the hermetic builder image instead of the host.",
    )
    build_parser.add_argument(
        "--builder-image",
        default=None,
        help="Builder image used by --in-docker (defaults to red-env-builder:full).",
    )
    build_parser.add_argument(
        "--builder-dockerfile",
        default=None,
        help="Dockerfile used to build the builder image (defaults to docker/builder-full.Dockerfile).",
    )
    build_parser.add_argument(
        "--rebuild-builder",
        action="store_true",
        help="Rebuild the builder image before running an --in-docker build.",
    )
    build_parser.add_argument(
        "--docker-network",
        default=None,
        help=(
            "Docker network mode for --in-docker (defaults to host, which also works on "
            "machines whose daemon cannot create veth pairs)."
        ),
    )
    build_parser.set_defaults(handler=build_command)

    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("--artifact", required=True)
    verify_parser.add_argument("--arch", required=True)
    verify_parser.add_argument("--dockerfile", default="docker/verifier.Dockerfile")
    verify_parser.add_argument("--interactive", action="store_true")
    verify_parser.add_argument(
        "--docker-network",
        default=None,
        help="Docker network mode for the verifier (defaults to host).",
    )
    verify_parser.set_defaults(handler=verify_command)

    release_parser = subparsers.add_parser("release")
    release_parser.add_argument("--artifact", required=True)
    release_parser.set_defaults(handler=release_command)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 0)

    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
