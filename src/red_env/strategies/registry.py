from __future__ import annotations

from red_env.strategies.archive_extract import apply_archive_extract
from red_env.strategies.archive_tree import apply_archive_tree
from red_env.strategies.directory_copy import apply_directory_copy
from red_env.strategies.direct_binary import apply_direct_binary
from red_env.strategies.go_build import apply_go_build
from red_env.strategies.zig_build import apply_zig_build


STRATEGY_REGISTRY = {
    "direct_binary": apply_direct_binary,
    "archive_extract": apply_archive_extract,
    "archive_tree": apply_archive_tree,
    "directory_copy": apply_directory_copy,
    "zig_build": apply_zig_build,
    "go_build": apply_go_build,
}
