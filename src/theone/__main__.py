"""CLI entrypoint for theOne."""

from __future__ import annotations

import argparse
import sys

from theone import __version__


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="theOne", description="Personal yt-dlp TUI")
    parser.add_argument(
        "--version",
        action="version",
        version=f"theOne {__version__}",
    )
    parser.parse_args(argv)

    # Textual turns all colors into grayscale when NO_COLOR is set — fine for
    # logs, useless for thumbnail previews. Drop it for this visual TUI.
    import os

    os.environ.pop("NO_COLOR", None)
    os.environ.setdefault("COLORTERM", "truecolor")

    # Import Textual app only after CLI parsing so --version stays fast.
    from theone.app import TheOneApp

    TheOneApp().run()


if __name__ == "__main__":
    main(sys.argv[1:])
