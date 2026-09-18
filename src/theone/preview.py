"""Terminal preview helpers — thumbnail download + stream (mpv)."""

from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from theone.downloader import ensure_yt_dlp, image_referer

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def preview_cache_dir() -> Path:
    base = Path(tempfile.gettempdir()) / "theOne-previews"
    base.mkdir(parents=True, exist_ok=True)
    return base


def thumbnail_cache_path(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
    return preview_cache_dir() / f"{digest}.img"


def _suffix_for_url(url: str) -> str:
    lower = url.lower().split("?", 1)[0]
    for ext in (".webp", ".png", ".jpeg", ".jpg"):
        if lower.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


async def _download_one(thumbnail_url: str, *, page_url: str | None = None) -> Path | None:
    path = thumbnail_cache_path(thumbnail_url).with_suffix(_suffix_for_url(thumbnail_url))
    if path.is_file() and path.stat().st_size > 0:
        return path

    def _fetch() -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(
            thumbnail_url,
            headers={
                "User-Agent": _BROWSER_UA,
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                "Referer": image_referer(thumbnail_url, page_url),
            },
        )
        with urllib.request.urlopen(req, timeout=8) as response, path.open("wb") as out:
            data = response.read()
            if not data:
                raise OSError("empty thumbnail body")
            out.write(data)
        return path

    try:
        return await asyncio.to_thread(_fetch)
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, TimeoutError):
        if path.exists():
            path.unlink(missing_ok=True)
        return None


async def _download_via_ytdlp(page_url: str) -> Path | None:
    """Last resort: let yt-dlp write a converted JPEG thumbnail."""
    try:
        binary = ensure_yt_dlp()
    except Exception:
        return None

    out_tmpl = str(preview_cache_dir() / "%(id)s.%(ext)s")
    proc = await asyncio.create_subprocess_exec(
        binary,
        "--no-playlist",
        "--skip-download",
        "--write-thumbnail",
        "--convert-thumbnails",
        "jpg",
        "-o",
        out_tmpl,
        page_url,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    if proc.returncode != 0:
        return None

    # Pick newest jpg in cache written just now.
    jpgs = sorted(
        preview_cache_dir().glob("*.jpg"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return jpgs[0] if jpgs else None


async def download_thumbnail(
    thumbnail_url: str | None = None,
    *,
    candidates: list[str] | tuple[str, ...] | None = None,
    page_url: str | None = None,
) -> Path | None:
    """Download a remote thumbnail, trying several URLs then yt-dlp."""
    urls: list[str] = []
    if candidates:
        urls.extend(candidates)
    if thumbnail_url:
        urls.insert(0, thumbnail_url)
    # dedupe preserve order
    seen: set[str] = set()
    unique = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            unique.append(url)

    for url in unique:
        path = await _download_one(url, page_url=page_url)
        if path is not None:
            return path

    if page_url:
        return await _download_via_ytdlp(page_url)
    return None


def mpv_available() -> bool:
    return shutil.which("mpv") is not None


async def stream_preview(url: str) -> None:
    """Open a non-saving stream preview in mpv (separate window)."""
    if not mpv_available():
        raise RuntimeError("mpv not found — install mpv to preview streams.")
    await asyncio.create_subprocess_exec(
        "mpv",
        "--force-window=yes",
        "--keep-open=yes",
        "--title=theOne preview",
        "--ytdl=yes",
        url,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        start_new_session=True,
        env={**os.environ},
    )
