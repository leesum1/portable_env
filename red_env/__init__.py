from __future__ import annotations

from pathlib import Path

_SRC_PACKAGE = Path(__file__).resolve().parent.parent / "src" / "red_env"
if str(_SRC_PACKAGE) not in __path__:
    __path__.append(str(_SRC_PACKAGE))

from ._version import __version__

__all__ = ["__version__"]
