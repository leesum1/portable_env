from __future__ import annotations

import argparse
from typing import Sequence

from red_env.cli.commands.build import build_command
from red_env.cli.commands.manifest import lint_command
from red_env.cli.commands.profile import show_command


def _noop(_: argparse.Namespace) -> int:
    return 0


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
    build_parser.set_defaults(handler=build_command)

    for name in ("verify", "release"):
        command_parser = subparsers.add_parser(name)
        command_parser.set_defaults(handler=_noop)

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
