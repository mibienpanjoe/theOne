"""URL / extractor helpers for download UX."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

# Platforms where a long format menu is rarely useful — grab best immediately.
_INSTANT_BEST_HOST_BITS = (
    "instagram.com",
    "cdninstagram.com",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "t.co",
    "threads.net",
)

_INSTANT_BEST_EXTRACTORS = (
    "instagram",
    "tiktok",
    "twitter",
    "threads",
)

# (host suffix, folder name) — matched with exact host or subdomain.
_HOST_FOLDERS: tuple[tuple[str, str], ...] = (
    ("youtube.com", "youtube"),
    ("youtu.be", "youtube"),
    ("instagram.com", "instagram"),
    ("cdninstagram.com", "instagram"),
    ("tiktok.com", "tiktok"),
    ("twitter.com", "x"),
    ("x.com", "x"),
    ("t.co", "x"),
    ("threads.net", "threads"),
    ("facebook.com", "facebook"),
    ("fb.watch", "facebook"),
    ("fb.com", "facebook"),
    ("vimeo.com", "vimeo"),
    ("reddit.com", "reddit"),
    ("redd.it", "reddit"),
    ("twitch.tv", "twitch"),
    ("soundcloud.com", "soundcloud"),
    ("bilibili.com", "bilibili"),
    ("dailymotion.com", "dailymotion"),
    ("bandcamp.com", "bandcamp"),
    ("pinterest.com", "pinterest"),
    ("pin.it", "pinterest"),
    ("linkedin.com", "linkedin"),
    ("rumble.com", "rumble"),
)

# yt-dlp extractor_key prefixes → folder (when host is unknown / share links).
_EXTRACTOR_FOLDERS: tuple[tuple[str, str], ...] = (
    ("youtube", "youtube"),
    ("instagram", "instagram"),
    ("tiktok", "tiktok"),
    ("twitter", "x"),
    ("threads", "threads"),
    ("facebook", "facebook"),
    ("vimeo", "vimeo"),
    ("reddit", "reddit"),
    ("twitch", "twitch"),
    ("soundcloud", "soundcloud"),
    ("bilibili", "bilibili"),
    ("dailymotion", "dailymotion"),
    ("bandcamp", "bandcamp"),
    ("pinterest", "pinterest"),
    ("linkedin", "linkedin"),
    ("rumble", "rumble"),
)

_SAFE_FOLDER = re.compile(r"[^a-z0-9]+")


def prefers_instant_best(url: str, extractor: str | None = None) -> bool:
    """True when we should skip the format picker and download best."""
    host = _normalize_host(url)
    if any(_host_matches(host, bit) for bit in _INSTANT_BEST_HOST_BITS):
        return True
    key = (extractor or "").lower()
    return any(key.startswith(prefix) for prefix in _INSTANT_BEST_EXTRACTORS)


def platform_subdir(url: str, extractor: str | None = None) -> str:
    """Return a short folder name for separating downloads by platform."""
    host = _normalize_host(url)
    for suffix, folder in _HOST_FOLDERS:
        if _host_matches(host, suffix):
            return folder

    key = (extractor or "").lower()
    for prefix, folder in _EXTRACTOR_FOLDERS:
        if key.startswith(prefix):
            return folder

    if key and key not in {"generic", "html5"}:
        slug = _SAFE_FOLDER.sub("-", key).strip("-")
        if slug:
            return slug[:40]

    if host:
        labels = host.split(".")
        if labels[0] == "www":
            labels = labels[1:]
        if labels:
            slug = _SAFE_FOLDER.sub("-", labels[0]).strip("-")
            if slug:
                return slug[:40]

    return "other"


def resolve_download_dir(
    base: Path,
    url: str,
    extractor: str | None = None,
) -> Path:
    """Base download dir plus platform subfolder (e.g. …/theOne/youtube)."""
    return base / platform_subdir(url, extractor)


def _normalize_host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _host_matches(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith("." + suffix)
