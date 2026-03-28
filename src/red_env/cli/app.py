from __future__ import annotations

import argparse
from typing import Sequence


def _noop(_: argparse.Namespace) -> int:
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="red_env")
    subparsers = parser.add_subparsers(dest="command")

    for name in ("manifest", "profile", "build", "verify", "release"):
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
