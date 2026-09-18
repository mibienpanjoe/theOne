"""Discover and curate download format choices via yt-dlp -J."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field

from theone.downloader import ensure_yt_dlp
from theone.platforms import prefers_instant_best


@dataclass(frozen=True)
class FormatChoice:
    """One option in the pre-download picker / confirm grab."""

    format_spec: str
    label: str
    kind: str  # "video" | "audio" | "image"
    height: int | None = None
    audio_only: bool = False
    # Carousel slide (1-based yt-dlp playlist index). None = whole URL / first item.
    playlist_index: int | None = None
    # Direct image URL when kind == "image".
    image_url: str | None = None


@dataclass(frozen=True)
class MediaItem:
    """One slide in a carousel (or the sole media for a single post)."""

    index: int  # 1-based
    kind: str  # "video" | "image"
    title: str | None
    thumbnail_urls: tuple[str, ...]
    duration: str | None
    choices: tuple[FormatChoice, ...]
    image_url: str | None = None
    id: str | None = None

    @property
    def thumbnail_url(self) -> str | None:
        return self.thumbnail_urls[0] if self.thumbnail_urls else None


@dataclass(frozen=True)
class ProbeResult:
    """Metadata + formats discovered before download."""

    title: str | None
    uploader: str | None
    duration: str | None
    thumbnail_url: str | None
    thumbnail_urls: tuple[str, ...]
    choices: list[FormatChoice]
    url: str
    extractor: str | None = None
    items: tuple[MediaItem, ...] = field(default_factory=tuple)

    @property
    def is_carousel(self) -> bool:
        return len(self.items) > 1


def _filesize_label(fmt: dict) -> str:
    size = fmt.get("filesize") or fmt.get("filesize_approx")
    if not size:
        return ""
    mb = float(size) / (1024 * 1024)
    if mb >= 1024:
        return f" · {mb / 1024:.1f} GiB"
    return f" · {mb:.0f} MiB"


def entry_has_video(info: dict) -> bool:
    """True when yt-dlp reports at least one real video stream."""
    formats = info.get("formats") or []
    for fmt in formats:
        if not isinstance(fmt, dict):
            continue
        vcodec = fmt.get("vcodec") or "none"
        if vcodec != "none":
            return True
    vcodec = info.get("vcodec") or "none"
    return vcodec != "none"


def _looks_like_image_url(url: str) -> bool:
    lower = url.lower()
    path = lower.split("?", 1)[0]
    if any(path.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif")):
        return True
    # Twitter CDN often omits a file extension and uses ?format=jpg&name=orig
    if "pbs.twimg.com/media/" in lower or "twimg.com/media/" in lower:
        return True
    if "format=jpg" in lower or "format=png" in lower or "format=webp" in lower:
        return True
    return False


def pick_image_url(info: dict) -> str | None:
    """Best direct image URL from an image-only entry (full-frame, not square crop)."""
    for key in ("url", "original_url"):
        value = info.get(key)
        if isinstance(value, str) and value.startswith("http") and _looks_like_image_url(value):
            return value
    thumbs = pick_thumbnail_urls(info)
    return thumbs[0] if thumbs else None


def build_format_choices(info: dict) -> list[FormatChoice]:
    """Turn yt-dlp info JSON into a short, pickable menu."""
    formats = info.get("formats") or []
    choices: list[FormatChoice] = [
        FormatChoice(
            format_spec="bv*+ba/b",
            label="Best · video + audio",
            kind="video",
        )
    ]

    by_height: dict[int, dict] = {}
    for fmt in formats:
        height = fmt.get("height")
        if not isinstance(height, int) or height <= 0:
            continue
        vcodec = fmt.get("vcodec") or "none"
        if vcodec == "none":
            continue
        prev = by_height.get(height)
        score = (
            1 if (fmt.get("acodec") or "none") != "none" else 0,
            fmt.get("tbr") or 0,
            fmt.get("filesize") or fmt.get("filesize_approx") or 0,
        )
        prev_score = (
            (
                1 if (prev.get("acodec") or "none") != "none" else 0,
                prev.get("tbr") or 0,
                prev.get("filesize") or prev.get("filesize_approx") or 0,
            )
            if prev
            else (-1, -1, -1)
        )
        if score >= prev_score:
            by_height[height] = fmt

    for height in sorted(by_height, reverse=True):
        fmt = by_height[height]
        ext = fmt.get("ext") or "mp4"
        note = _filesize_label(fmt)
        choices.append(
            FormatChoice(
                format_spec=(
                    f"bv*[height<={height}]+ba/b[height<={height}]/best[height<={height}]"
                ),
                label=f"{height}p · {ext}{note}",
                kind="video",
                height=height,
            )
        )

    choices.append(
        FormatChoice(
            format_spec="ba/b",
            label="Audio only · best",
            kind="audio",
            audio_only=True,
        )
    )
    return choices


def pick_thumbnail_urls(info: dict) -> list[str]:
    """Ordered thumbnail candidates (best first), deduped.

    YouTube often advertises maxresdefault.webp that 404s — callers should try
    several URLs until one downloads.

    Instagram lists both square crops (stp contains c0.… / sNxN) and full-frame
    display URLs; prefer the uncropped largest image so previews/downloads
    aren't center-cropped.
    """
    ordered: list[str] = []
    seen: set[str] = set()

    def add(url: object) -> None:
        if not isinstance(url, str) or not url.startswith("http"):
            return
        if url in seen:
            return
        seen.add(url)
        ordered.append(url)

    thumbs = [t for t in (info.get("thumbnails") or []) if isinstance(t, dict)]

    def url_dims(url: str) -> tuple[int, int]:
        """Best-effort WxH from Instagram CDN stp / path hints."""
        import re

        # Cropped square exports: c0.y.w.h…_s1024x1024
        m = re.search(r"_s(\d+)x(\d+)", url)
        if m:
            return int(m.group(1)), int(m.group(2))
        # Portrait-friendly: _p720x720 often still serves non-square pixels;
        # prefer explicit pWxH only as a weak signal.
        m = re.search(r"_p(\d+)x(\d+)", url)
        if m:
            return int(m.group(1)), int(m.group(2))
        return 0, 0

    def is_cropped_square(url: str) -> bool:
        lower = url.lower()
        # IG center-crop marker in stp=, e.g. c0.128.1024.1024a_dst-jpg_e35_s1024x1024
        if "c0." in lower or "c1." in lower:
            return True
        if "_s" in lower and "x" in lower and "c0." in lower.replace("%", ""):
            return True
        # sNxN with equal sides after a crop token
        import re

        return bool(re.search(r"c\d+\.\d+\.\d+\.\d+", lower))

    def rank(thumb: dict) -> tuple[int, int, int, int, int]:
        url = str(thumb.get("url") or "")
        lower = url.lower()
        # Penalize notorious YouTube placeholders that frequently 404.
        penalty = 0
        if "maxresdefault" in lower:
            penalty -= 50
        if lower.endswith(".webp") or "vi_webp" in lower:
            penalty -= 5
        # Prefer full-frame Instagram images over square crops.
        if is_cropped_square(url):
            penalty -= 1000

        width = int(thumb.get("width") or 0)
        height = int(thumb.get("height") or 0)
        if width <= 0 or height <= 0:
            width, height = url_dims(url)
        # Uncropped full display URLs often omit WxH in metadata — boost e35
        # without an sNxN square export.
        if "dst-jpg_e35" in lower and "_s" not in lower and not is_cropped_square(url):
            if width <= 0:
                width = 1080
            if height <= 0:
                height = 1350
            penalty += 50

        # Prefer non-square (original IG feed aspect) over 1:1 crops.
        aspect_bonus = 0
        if width > 0 and height > 0 and width != height:
            aspect_bonus = 100

        area = width * height
        return (
            penalty + int(thumb.get("preference") or 0) + aspect_bonus,
            area,
            height,
            width,
            0,
        )

    for thumb in sorted(thumbs, key=rank, reverse=True):
        add(thumb.get("url"))

    add(info.get("thumbnail"))
    return ordered


def pick_thumbnail_url(info: dict) -> str | None:
    urls = pick_thumbnail_urls(info)
    return urls[0] if urls else None


def _format_duration(info: dict) -> str | None:
    duration = info.get("duration_string")
    if duration:
        return str(duration)
    if isinstance(info.get("duration"), (int, float)):
        total = int(info["duration"])
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        return (
            f"{hours}:{minutes:02d}:{seconds:02d}"
            if hours
            else f"{minutes}:{seconds:02d}"
        )
    return None


def media_item_from_entry(entry: dict, index: int) -> MediaItem:
    """Build a MediaItem from one yt-dlp playlist entry / video info dict."""
    thumb_urls = tuple(pick_thumbnail_urls(entry))
    title = entry.get("title") or entry.get("fulltitle")
    entry_id = entry.get("id")
    if isinstance(entry_id, (int, float)):
        entry_id = str(entry_id)
    elif not isinstance(entry_id, str):
        entry_id = None

    if entry_has_video(entry):
        choices = tuple(
            FormatChoice(
                format_spec=c.format_spec,
                label=c.label,
                kind=c.kind,
                height=c.height,
                audio_only=c.audio_only,
                playlist_index=index,
            )
            for c in build_format_choices(entry)
        )
        return MediaItem(
            index=index,
            kind="video",
            title=title if isinstance(title, str) else None,
            thumbnail_urls=thumb_urls,
            duration=_format_duration(entry),
            choices=choices,
            id=entry_id,
        )

    image_url = pick_image_url(entry)
    if not image_url and thumb_urls:
        image_url = thumb_urls[0]
    image_choice = FormatChoice(
        format_spec="",
        label="Image · original",
        kind="image",
        playlist_index=index,
        image_url=image_url,
    )
    return MediaItem(
        index=index,
        kind="image",
        title=title if isinstance(title, str) else None,
        thumbnail_urls=thumb_urls,
        duration=None,
        choices=(image_choice,),
        image_url=image_url,
        id=entry_id,
    )


def probe_from_info(info: dict, url: str) -> ProbeResult:
    extractor = info.get("extractor_key") or info.get("extractor") or None
    uploader = info.get("uploader") or info.get("channel") or info.get("creator")
    if isinstance(uploader, str):
        pass
    else:
        uploader = None

    entries: list[dict] = []
    if info.get("_type") == "playlist" and info.get("entries"):
        entries = [e for e in info["entries"] if isinstance(e, dict) and e]
    elif isinstance(info, dict) and (info.get("formats") is not None or info.get("url")):
        entries = [info]

    if not entries:
        raise RuntimeError("No downloadable media found.")

    items = tuple(media_item_from_entry(entry, index) for index, entry in enumerate(entries, 1))
    first = items[0]
    if first.kind == "image" and not first.image_url and not first.thumbnail_urls:
        raise RuntimeError(
            "No image URL found for this post.\n"
            "X/Twitter photos sometimes need a retry, or cookies_from_browser in config."
        )
    # Flatten choices for non-carousel UX / format picker: first item's choices
    # without forcing playlist_index when there's only one slide.
    if len(items) == 1:
        choices = [
            FormatChoice(
                format_spec=c.format_spec,
                label=c.label,
                kind=c.kind,
                height=c.height,
                audio_only=c.audio_only,
                playlist_index=None if c.kind != "image" else 1,
                image_url=c.image_url,
            )
            for c in first.choices
        ]
    else:
        choices = list(first.choices)

    if not choices:
        raise RuntimeError("No downloadable formats found.")

    title = info.get("title") or info.get("fulltitle") or first.title
    if info.get("_type") == "playlist" and not title:
        title = first.title

    return ProbeResult(
        title=title if isinstance(title, str) else None,
        uploader=uploader,
        duration=first.duration if len(items) == 1 else None,
        thumbnail_url=first.thumbnail_url,
        thumbnail_urls=first.thumbnail_urls,
        choices=choices,
        url=url,
        extractor=extractor if isinstance(extractor, str) else None,
        items=items,
    )


def _should_expand_playlist(url: str) -> bool:
    """Expand playlists for IG/TikTok/X carousels; keep YouTube as a single video."""
    return prefers_instant_best(url)


async def fetch_probe(
    url: str,
    *,
    yt_dlp_bin: str | None = None,
    cookies_from_browser: str | None = None,
) -> ProbeResult:
    """Probe a URL for metadata, thumbnail, and format choices."""
    from theone.downloader import detect_js_runtime

    binary = yt_dlp_bin or ensure_yt_dlp()
    args = [binary, "--skip-download", "-J"]
    if not _should_expand_playlist(url):
        args.insert(1, "--no-playlist")
    js_runtime = detect_js_runtime()
    if js_runtime:
        args += ["--js-runtimes", js_runtime]
    if cookies_from_browser:
        args += ["--cookies-from-browser", cookies_from_browser]
    # Image-only carousel slides error without this when expanding playlists.
    if _should_expand_playlist(url):
        args.append("--ignore-no-formats-error")
    args.append(url)

    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        out = stdout.decode("utf-8", errors="replace").strip()
        detail = err or out or f"yt-dlp exited {proc.returncode}"
        for line in reversed(detail.splitlines()):
            if line.startswith("ERROR:"):
                raise RuntimeError(line)
        raise RuntimeError(detail.splitlines()[-1] if detail else "format probe failed")

    raw = stdout.decode("utf-8", errors="replace")
    try:
        info = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Could not parse yt-dlp JSON: {exc}") from exc

    # yt-dlp skips still photos on X/Twitter — fill from syndication when needed.
    from theone.twitter import enrich_twitter_info

    info = await asyncio.to_thread(enrich_twitter_info, info, url)
    return probe_from_info(info, url)


# Back-compat alias used by older call sites / tests.
async def fetch_format_choices(
    url: str,
    *,
    yt_dlp_bin: str | None = None,
) -> tuple[str | None, list[FormatChoice]]:
    probe = await fetch_probe(url, yt_dlp_bin=yt_dlp_bin)
    return probe.title, probe.choices
