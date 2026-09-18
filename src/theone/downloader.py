"""yt-dlp argv building, progress parsing, and async runner."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import signal
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from pathlib import Path

from theone.config import QualityName
from theone.naming import output_template

PROGRESS_RE = re.compile(
    r"\[download\]\s+"
    r"(?P<percent>\d+(?:\.\d+)?)%\s+"
    r"of\s+(?:~?\s*)?(?P<total>\S+)\s+"
    r"at\s+(?P<speed>\S+)\s+"
    r"ETA\s+(?P<eta>\S+)"
)

DEST_RE = re.compile(r"\[download\]\s+Destination:\s+(?P<path>.+)$")
MERGED_RE = re.compile(r"\[Merger\]\s+Merging formats into\s+\"(?P<path>.+)\"")
EXTRACT_RE = re.compile(r"\[ExtractAudio\]\s+Destination:\s+(?P<path>.+)$")
TITLE_RE = re.compile(r"^\[info\]\s+(?P<title>.+?): Downloading")


class YtDlpNotFoundError(RuntimeError):
    """Raised when yt-dlp is not on PATH."""


@dataclass(frozen=True)
class ProgressUpdate:
    percent: float | None = None
    total: str | None = None
    speed: str | None = None
    eta: str | None = None
    destination: str | None = None
    title: str | None = None
    raw: str = ""
    done: bool = False
    success: bool = False
    cancelled: bool = False
    error: str | None = None


QUALITY_FORMATS: dict[QualityName, str | None] = {
    "best": None,
    "1080": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "720": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
}


def ensure_yt_dlp() -> str:
    path = shutil.which("yt-dlp")
    if not path:
        raise YtDlpNotFoundError(
            "yt-dlp not found on PATH. Install it, then retry "
            "(e.g. uv tool install yt-dlp)."
        )
    return path


def format_download_error(lines: list[str], *, exit_code: int) -> str:
    """Turn noisy yt-dlp logs into a short UI message."""
    text = "\n".join(lines)
    lowered = text.lower()

    error_lines = [
        line for line in lines if line.startswith("ERROR:") or line.startswith("ERROR ")
    ]
    summary = error_lines[-1] if error_lines else (lines[-1] if lines else f"exit {exit_code}")

    outdated = any(
        needle in lowered
        for needle in (
            "unable to extract",
            "nsig",
            "n function",
            "signature extraction failed",
            "confirm you are on the latest version",
        )
    )
    if outdated:
        return (
            "YouTube blocked this yt-dlp build (extractor outdated).\n"
            "Update with:  uv tool install --force yt-dlp\n"
            "Then confirm:  yt-dlp --version   (should be 2025+)"
        )
    if "403" in lowered and "forbidden" in lowered:
        return (
            "HTTP 403 Forbidden — the site refused the media URL.\n"
            "Common fixes:\n"
            "1) Install a JS runtime (deno or node) for YouTube\n"
            "2) Add to ~/.config/theOne/config.toml:\n"
            '   cookies_from_browser = "firefox"   # or chrome\n'
            "3) Update yt-dlp:  uv tool install --force yt-dlp\n"
            "4) Retry a lower quality, or check region/login walls"
        )
    if "ffmpeg" in lowered:
        return f"{summary}\nHint: install ffmpeg for merges / audio extraction."
    # Prefer the ERROR line; drop traceback noise.
    if len(summary) > 240:
        summary = summary[:237] + "..."
    return summary


def detect_js_runtime() -> str | None:
    """Return yt-dlp --js-runtimes value when deno/node is available."""
    deno = shutil.which("deno")
    if deno:
        return f"deno:{deno}"
    node = shutil.which("node")
    if node:
        return f"node:{node}"
    return None


def build_yt_dlp_args(
    url: str,
    *,
    download_dir: Path,
    audio_only: bool,
    concurrent_fragments: int = 8,
    quality: QualityName = "best",
    use_aria2c: bool = False,
    format_spec: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp_bin: str = "yt-dlp",
    playlist_index: int | None = None,
) -> list[str]:
    args = [
        yt_dlp_bin,
        "--newline",
        "--progress",
        "-N",
        str(concurrent_fragments),
        "-P",
        str(download_dir),
        "-o",
        output_template(),
    ]
    if playlist_index is not None:
        args += ["--playlist-items", str(playlist_index)]
    else:
        args.append("--no-playlist")
    js_runtime = detect_js_runtime()
    if js_runtime:
        args += ["--js-runtimes", js_runtime]
    if cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    if use_aria2c and shutil.which("aria2c"):
        args += [
            "--downloader",
            "aria2c",
            "--downloader-args",
            "aria2c:-x 16 -s 16 -k 1M",
        ]
    if format_spec:
        args += ["-f", format_spec]
        if audio_only:
            args += ["-x", "--audio-format", "m4a", "--audio-quality", "0"]
    elif audio_only:
        args += ["-x", "--audio-format", "m4a", "--audio-quality", "0"]
    else:
        fmt = QUALITY_FORMATS.get(quality)
        if fmt:
            args += ["-f", fmt]
    args.append(url)
    return args


def parse_progress_line(line: str) -> ProgressUpdate | None:
    text = line.strip()
    if not text:
        return None

    if m := TITLE_RE.search(text):
        return ProgressUpdate(title=m.group("title"), raw=text)
    if m := DEST_RE.search(text):
        return ProgressUpdate(destination=m.group("path"), raw=text)
    if m := MERGED_RE.search(text):
        return ProgressUpdate(destination=m.group("path"), raw=text)
    if m := EXTRACT_RE.search(text):
        return ProgressUpdate(destination=m.group("path"), raw=text)
    if m := PROGRESS_RE.search(text):
        return ProgressUpdate(
            percent=float(m.group("percent")),
            total=m.group("total"),
            speed=m.group("speed"),
            eta=m.group("eta"),
            raw=text,
        )
    return ProgressUpdate(raw=text)


@dataclass
class DownloadJob:
    """Running yt-dlp process that can be cancelled."""

    _proc: asyncio.subprocess.Process | None = field(default=None, repr=False)
    _cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True
        proc = self._proc
        if proc is None or proc.returncode is not None:
            return
        try:
            proc.send_signal(signal.SIGTERM)
        except ProcessLookupError:
            return

    @property
    def cancelled(self) -> bool:
        return self._cancelled


async def run_download(
    url: str,
    *,
    download_dir: Path,
    audio_only: bool,
    concurrent_fragments: int = 8,
    quality: QualityName = "best",
    use_aria2c: bool = False,
    format_spec: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp_bin: str | None = None,
    playlist_index: int | None = None,
    job: DownloadJob | None = None,
    create_subprocess_exec: Callable[..., object] = asyncio.create_subprocess_exec,
) -> AsyncIterator[ProgressUpdate]:
    binary = yt_dlp_bin or ensure_yt_dlp()
    download_dir.mkdir(parents=True, exist_ok=True)
    args = build_yt_dlp_args(
        url,
        download_dir=download_dir,
        audio_only=audio_only,
        concurrent_fragments=concurrent_fragments,
        quality=quality,
        use_aria2c=use_aria2c,
        format_spec=format_spec,
        cookies_from_browser=cookies_from_browser,
        yt_dlp_bin=binary,
        playlist_index=playlist_index,
    )

    active = job or DownloadJob()
    proc = await create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    active._proc = proc  # noqa: SLF001 — intentional ownership
    assert proc.stdout is not None

    last_dest: str | None = None
    last_title: str | None = None
    stderr_tail: list[str] = []

    async for raw in proc.stdout:
        if active.cancelled:
            break
        line = raw.decode("utf-8", errors="replace").rstrip("\n")
        update = parse_progress_line(line)
        if update is None:
            continue
        if update.destination:
            last_dest = update.destination
        if update.title:
            last_title = update.title
        if update.raw and not update.percent and not update.destination and not update.title:
            stderr_tail.append(update.raw)
            if len(stderr_tail) > 40:
                stderr_tail.pop(0)
        yield update

    if active.cancelled:
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
        yield ProgressUpdate(
            done=True,
            success=False,
            cancelled=True,
            destination=last_dest,
            title=last_title,
            error="cancelled",
            raw="cancelled",
        )
        return

    code = await proc.wait()
    if code == 0:
        yield ProgressUpdate(
            percent=100.0,
            destination=last_dest,
            title=last_title,
            done=True,
            success=True,
            raw="done",
        )
    else:
        detail = format_download_error(stderr_tail, exit_code=code)
        yield ProgressUpdate(
            done=True,
            success=False,
            error=detail,
            destination=last_dest,
            title=last_title,
            raw=detail,
        )


_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _image_suffix(url: str) -> str:
    lower = url.lower().split("?", 1)[0]
    for ext in (".webp", ".png", ".jpeg", ".jpg"):
        if lower.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def _safe_image_stem(title: str | None, *, index: int | None) -> str:
    base = (title or "image").strip() or "image"
    # Keep it filesystem-friendly without nuking unicode letters.
    cleaned = "".join(ch if ch not in '/\\\0' else "_" for ch in base)[:120]
    if index is not None:
        return f"{cleaned} [{index}]"
    return cleaned


async def download_image(
    image_url: str,
    *,
    download_dir: Path,
    title: str | None = None,
    playlist_index: int | None = None,
    page_url: str | None = None,
    cookies_from_browser: str | None = None,
    yt_dlp_bin: str | None = None,
    job: DownloadJob | None = None,
) -> AsyncIterator[ProgressUpdate]:
    """Save an image slide (direct URL, else yt-dlp thumbnail fallback)."""
    import urllib.error
    import urllib.request

    download_dir.mkdir(parents=True, exist_ok=True)
    active = job or DownloadJob()
    stem = _safe_image_stem(title, index=playlist_index)
    dest = download_dir / f"{stem}{_image_suffix(image_url)}"
    # Avoid clobbering an existing file.
    if dest.exists():
        n = 2
        while True:
            candidate = download_dir / f"{stem} ({n}){_image_suffix(image_url)}"
            if not candidate.exists():
                dest = candidate
                break
            n += 1

    yield ProgressUpdate(percent=0.0, title=title, raw="image start")

    def _fetch() -> Path:
        req = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": _BROWSER_UA,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": "https://www.instagram.com/",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response, dest.open("wb") as out:
            data = response.read()
            if not data:
                raise OSError("empty image body")
            out.write(data)
        return dest

    try:
        if active.cancelled:
            yield ProgressUpdate(done=True, success=False, cancelled=True, error="cancelled")
            return
        path = await asyncio.to_thread(_fetch)
        if active.cancelled:
            path.unlink(missing_ok=True)
            yield ProgressUpdate(done=True, success=False, cancelled=True, error="cancelled")
            return
        yield ProgressUpdate(
            percent=100.0,
            destination=str(path),
            title=title,
            done=True,
            success=True,
            raw="done",
        )
        return
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError) as exc:
        # Fall through to yt-dlp thumbnail write when we have a page URL + index.
        if page_url is None or playlist_index is None:
            yield ProgressUpdate(
                done=True,
                success=False,
                error=f"image download failed: {exc}",
                raw=str(exc),
            )
            return

    binary = yt_dlp_bin or ensure_yt_dlp()
    out_tmpl = str(download_dir / f"{stem}.%(ext)s")
    args = [
        binary,
        "--playlist-items",
        str(playlist_index),
        "--skip-download",
        "--write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "--ignore-no-formats-error",
        "-o",
        out_tmpl,
    ]
    if cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    args.append(page_url)

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    active._proc = proc  # noqa: SLF001
    assert proc.stdout is not None
    async for raw in proc.stdout:
        if active.cancelled:
            break
        _ = raw
    if active.cancelled:
        if proc.returncode is None:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            await proc.wait()
        yield ProgressUpdate(done=True, success=False, cancelled=True, error="cancelled")
        return

    code = await proc.wait()
    # Pick newest jpg matching stem.
    matches = sorted(
        download_dir.glob(f"{stem}*.jpg"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if code == 0 and matches:
        yield ProgressUpdate(
            percent=100.0,
            destination=str(matches[0]),
            title=title,
            done=True,
            success=True,
            raw="done",
        )
    else:
        yield ProgressUpdate(
            done=True,
            success=False,
            error="Could not download image slide",
            raw="image failed",
        )
