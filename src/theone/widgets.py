"""UI widgets for theOne."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Input, Static

from theone.config import ThemeName

# Hand-built 5-row glyphs — capital O is clearly distinct from e/n.
_GLYPHS: dict[str, tuple[str, str, str, str, str]] = {
    "t": ("██████", "  ██  ", "  ██  ", "  ██  ", "  ██  "),
    "h": ("██  ██", "██  ██", "██████", "██  ██", "██  ██"),
    "e": ("██████", "██    ", "█████ ", "██    ", "██████"),
    "O": (" ████ ", "██  ██", "██  ██", "██  ██", " ████ "),
    "n": ("██  ██", "███ ██", "██ ███", "██  ██", "██  ██"),
}


def render_brand(text: str = "theOne") -> str:
    rows = ["", "", "", "", ""]
    for index, char in enumerate(text):
        glyph = _GLYPHS[char]
        gap = "  " if index else ""
        for row_i, piece in enumerate(glyph):
            rows[row_i] += gap + piece
    return "\n".join(rows)


class LinkBar(Horizontal):
    """One bordered field with > url and grab inside the same box."""

    DEFAULT_CSS = """
    LinkBar {
        layout: horizontal;
        width: 100%;
        height: 3;
        border: solid $foreground;
        background: $background;
        padding: 0 1;
        align: left middle;
    }
    LinkBar:focus-within {
        border: solid $foreground;
    }
    LinkBar #prompt {
        width: 2;
        height: 1;
        color: $foreground;
        content-align: left middle;
        padding: 0;
    }
    LinkBar #url {
        width: 1fr;
        height: 1;
        border: none !important;
        background: transparent !important;
        padding: 0;
        margin: 0;
        color: $foreground;
    }
    LinkBar #url:focus {
        border: none !important;
        background: transparent !important;
        padding-left: 0;
    }
    LinkBar #grab-btn {
        width: auto;
        min-width: 8;
        height: 1;
        margin: 0 0 0 1;
        border: none !important;
        background: $foreground;
        color: $background;
        text-style: bold;
        content-align: center middle;
        padding: 0 2;
    }
    LinkBar #grab-btn:focus {
        background: $foreground;
        color: $background;
        text-style: bold;
        border: none !important;
    }
    LinkBar #grab-btn:hover {
        text-style: bold reverse;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static(">", id="prompt")
        yield Input(
            placeholder="https://youtube.com/watch?v=...",
            id="url",
        )
        yield Button("grab", id="grab-btn", flat=True)

    def on_mount(self) -> None:
        self.border_title = "Paste a link"


class KeyHints(Static):
    """Sparse footer of key hints."""

    DEFAULT_CSS = """
    KeyHints {
        dock: bottom;
        width: 100%;
        height: 1;
        text-align: center;
        color: $text-muted;
        background: $background;
        padding: 0 1;
    }
    """

    def show(
        self,
        *,
        theme: ThemeName,
        audio_only: bool,
        quality: str = "best",
        busy: bool = False,
    ) -> None:
        parts = ["⏎ grab", "^c quit", f"^t theme:{theme}"]
        if audio_only:
            parts.insert(2, "^a audio")
        if quality != "best":
            parts.append(f"^q {quality}")
        if busy:
            parts.append("esc cancel")
        self.update("   ".join(parts))
