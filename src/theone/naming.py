"""Output filename templates for yt-dlp."""

from __future__ import annotations

# Keep unicode; yt-dlp still replaces path-illegal characters.
# No --restrict-filenames (that would ASCII-fold titles).
OUTPUT_TEMPLATE = "%(title).200B [%(id)s].%(ext)s"


def output_template() -> str:
    return OUTPUT_TEMPLATE
