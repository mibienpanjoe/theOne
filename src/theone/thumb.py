"""In-TUI thumbnail widget — TGP when Kitty, else half-cell (never unicode)."""

from __future__ import annotations

import os
from pathlib import Path

from textual.widget import Widget

# Import halfcell modules directly — avoid textual_image.renderable.__init__
# which probes the terminal and can ZeroDivisionError when COLUMNS=0.
from textual_image.renderable.halfcell import Image as HalfcellRenderable
from textual_image.widget._base import Image as BaseImage


class HalfcellThumb(BaseImage, Renderable=HalfcellRenderable):
    """Truecolor half-cell thumbnail (works in any terminal)."""


def _looks_like_kitty() -> bool:
    if os.environ.get("KITTY_WINDOW_ID"):
        return True
    return os.environ.get("TERM", "").startswith("xterm-kitty")


def _looks_like_sixel_term() -> bool:
    term = os.environ.get("TERM", "")
    # Skip probing in terminals that never do sixel — keeps startup snappy.
    if term.startswith("xterm-kitty") or "dumb" in term:
        return False
    return term.startswith(("xterm", "mlterm", "foot", "wezterm", "contour", "tmux", "screen"))


def _try_tgp_widget() -> type[Widget] | None:
    """Return TGP widget if this terminal supports Kitty graphics."""
    if not _looks_like_kitty():
        return None
    try:
        from textual_image.renderable import tgp as tgp_mod
        from textual_image.renderable.tgp import Image as TGPRenderable

        if not tgp_mod.query_terminal_support():
            return None

        class TGPThumb(BaseImage, Renderable=TGPRenderable):
            """Kitty Terminal Graphics Protocol thumbnail."""

        return TGPThumb
    except Exception:
        return None


def _try_sixel_widget() -> type[Widget] | None:
    """Return Sixel widget if this terminal supports sixel graphics."""
    if not _looks_like_sixel_term():
        return None
    try:
        from textual_image.renderable import sixel as sixel_mod
        from textual_image.widget.sixel import Image as SixelImage

        if not sixel_mod.query_terminal_support():
            return None
        return SixelImage
    except Exception:
        return None


def _best_image_widget() -> type[Widget]:
    """Sharpest available widget. Never unicode dither (looks like gray mush)."""
    tgp = _try_tgp_widget()
    if tgp is not None:
        return tgp
    sixel = _try_sixel_widget()
    if sixel is not None:
        return sixel
    return HalfcellThumb


ThumbImage = _best_image_widget()


def make_thumb(path: Path | str, *, id: str | None = None) -> Widget:
    """Create an in-TUI thumbnail widget for a local image file."""
    return ThumbImage(str(path), id=id)
