#!/usr/bin/env python3
"""Visual demo: in-TUI thumbnail via textual-image (for ttyd / local check)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Textual monochromes everything when NO_COLOR is set.
os.environ.pop("NO_COLOR", None)
os.environ.setdefault("COLORTERM", "truecolor")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from textual.app import App, ComposeResult  # noqa: E402
from textual.containers import Vertical  # noqa: E402
from textual.widgets import Label  # noqa: E402

from theone.thumb import ThumbImage, make_thumb  # noqa: E402

DEFAULT_IMAGE = Path("/tmp/theone-test-thumb.jpg")


class PreviewDemo(App[None]):
    CSS = """
    Screen {
        align: center middle;
        background: #000000;
    }
    #box {
        width: 60;
        height: auto;
        border: solid #fafafa;
        background: #000000;
        padding: 1 2;
        align: center middle;
    }
    #title {
        text-style: bold;
        text-align: center;
        color: #fafafa;
        width: 100%;
        height: auto;
    }
    #meta {
        text-align: center;
        color: #737373;
        width: 100%;
        height: auto;
        margin-bottom: 1;
    }
    #thumb {
        width: 48;
        height: 28;
        margin: 0 0 1 0;
    }
    #hint {
        text-align: center;
        color: #737373;
        width: 100%;
    }
    """

    def __init__(self, image: Path) -> None:
        super().__init__()
        self._image = image

    def compose(self) -> ComposeResult:
        with Vertical(id="box"):
            yield Label("Preview demo — in-TUI thumbnail", id="title")
            yield Label(f"{ThumbImage.__name__} · no external viewer", id="meta")
            yield make_thumb(self._image, id="thumb")
            yield Label("q quit", id="hint")

    def on_key(self, event) -> None:  # noqa: ANN001
        if event.key in {"q", "escape"}:
            self.exit()


def main() -> None:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IMAGE
    if not path.is_file():
        raise SystemExit(f"missing image: {path}")
    PreviewDemo(path).run()


if __name__ == "__main__":
    main()
