"""Read clipboard via common Linux tools (no extra Python deps)."""

from __future__ import annotations

import shutil
import subprocess

# Keep short — a stuck wl-paste must not delay first paint.
_CLIP_TIMEOUT_S = 0.2


def read_clipboard() -> str | None:
    commands: list[list[str]] = []
    if shutil.which("wl-paste"):
        commands.append(["wl-paste", "-n"])
    if shutil.which("xclip"):
        commands.append(["xclip", "-selection", "clipboard", "-o"])
    if shutil.which("xsel"):
        commands.append(["xsel", "--clipboard", "--output"])

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=_CLIP_TIMEOUT_S,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            text = (result.stdout or "").strip()
            if text:
                return text
    return None


def looks_like_url(text: str) -> bool:
    lowered = text.lower()
    return lowered.startswith(("http://", "https://", "www."))
