"""Detect whether the terminal looks dark (for theme=auto)."""

from __future__ import annotations

import os


def terminal_prefers_dark() -> bool:
    """Best-effort dark-terminal detection.

    Uses COLORFGBG when present (bg index < 8 ≈ dark). Defaults to dark.
    """
    colorfgbg = os.environ.get("COLORFGBG")
    if colorfgbg and ";" in colorfgbg:
        try:
            bg = int(colorfgbg.rsplit(";", 1)[-1])
        except ValueError:
            return True
        # Conventional: 0–7 dark-ish backgrounds, 8–15 light-ish.
        return bg < 8
    return True
