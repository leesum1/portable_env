from __future__ import annotations

from pathlib import Path

_SRC_PATH = Path(__file__).resolve().parent.parent / "src" / "red_env"
if str(_SRC_PATH) not in __path__:
    __path__.append(str(_SRC_PATH))
