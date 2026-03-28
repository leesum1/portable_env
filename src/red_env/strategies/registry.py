from __future__ import annotations

from red_env.strategies.archive_extract import apply_archive_extract
from red_env.strategies.directory_copy import apply_directory_copy
from red_env.strategies.direct_binary import apply_direct_binary


STRATEGY_REGISTRY = {
    "direct_binary": apply_direct_binary,
    "archive_extract": apply_archive_extract,
    "directory_copy": apply_directory_copy,
}
