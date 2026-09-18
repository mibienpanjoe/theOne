"""Twitter/X helpers — yt-dlp skips still photos; we enrich via syndication."""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

_BROWSER_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_TWEET_ID_RE = re.compile(r"/(?:status|statuses)/(\d+)", re.I)


def tweet_id_from_info(info: dict, url: str = "") -> str | None:
    """Best-effort status id from yt-dlp info or URL."""
    for key in ("display_id", "id"):
        value = info.get(key)
        if isinstance(value, (int, float)):
            return str(int(value))
        if isinstance(value, str) and value.isdigit():
            return value
    for candidate in (
        url,
        str(info.get("webpage_url") or ""),
        str(info.get("original_url") or ""),
    ):
        match = _TWEET_ID_RE.search(candidate)
        if match:
            return match.group(1)
    return None


def is_twitter_extractor(info: dict) -> bool:
    key = str(info.get("extractor_key") or info.get("extractor") or "").lower()
    return key.startswith("twitter")


def _float_to_base36(val: float) -> str:
    """JS Number.prototype.toString(36) enough for syndication tokens."""
    if val == 0:
        return "0"
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    sign = val < 0
    val = abs(val)
    fraction, integer = math.modf(val)
    delta = max(math.nextafter(0.0, math.inf), math.ulp(val) / 2)
    digits: list[int] = []
    if fraction >= delta:
        digits.append(-2)  # '.'
    while fraction >= delta:
        delta *= 36
        fraction, digit = math.modf(fraction * 36)
        digits.append(int(digit))
        needs_rounding = fraction > 0.5 or (fraction == 0.5 and int(digit) & 1)
        if needs_rounding and fraction + delta > 1:
            for index in reversed(range(1, len(digits))):
                if digits[index] + 1 < 36:
                    digits[index] += 1
                    break
                digits.pop()
            else:
                integer += 1
            break
    head: list[int] = []
    integer_i = int(integer)
    integer_i, digit = divmod(integer_i, 36)
    head.append(digit)
    while integer_i > 0:
        integer_i, digit = divmod(integer_i, 36)
        head.insert(0, digit)
    chars: list[str] = []
    if sign:
        chars.append("-")
    for d in head + digits:
        if d == -2:
            chars.append(".")
        else:
            chars.append(alphabet[d])
    return "".join(chars)


def syndication_token(tweet_id: str) -> str:
    """Match yt-dlp Twitter syndication token generation."""
    raw = _float_to_base36((int(tweet_id) / 1e15) * math.pi)
    return raw.translate(str.maketrans(dict.fromkeys("0.")))


def fetch_syndication_tweet(tweet_id: str) -> dict[str, Any] | None:
    """Fetch public tweet JSON from Twitter's syndication CDN."""
    token = syndication_token(tweet_id) or "0"
    query = urllib.parse.urlencode({"id": tweet_id, "token": token})
    url = f"https://cdn.syndication.twimg.com/tweet-result?{query}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Googlebot",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.load(response)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def _photo_entries_from_syndication(data: dict[str, Any], tweet_id: str) -> list[dict]:
    photos: list[dict] = []
    seen: set[str] = set()

    def add(media_url: str, width: int = 0, height: int = 0) -> None:
        if not media_url.startswith("http") or media_url in seen:
            return
        seen.add(media_url)
        # Prefer original size when Twitter serves name variants.
        orig = media_url
        if "name=" not in media_url and "pbs.twimg.com/media/" in media_url:
            sep = "&" if "?" in media_url else "?"
            orig = f"{media_url}{sep}name=orig"
        thumbs = [
            {"url": orig, "width": width or 0, "height": height or 0, "id": "orig"},
            {"url": media_url, "width": width or 0, "height": height or 0, "id": "base"},
        ]
        photos.append(
            {
                "id": f"{tweet_id}-{len(photos) + 1}",
                "title": None,
                "url": orig,
                "original_url": orig,
                "thumbnail": orig,
                "thumbnails": thumbs,
                "formats": [],
                "extractor": "twitter",
                "extractor_key": "Twitter",
                "ext": "jpg",
            }
        )

    for photo in data.get("photos") or []:
        if not isinstance(photo, dict):
            continue
        media_url = photo.get("url")
        if isinstance(media_url, str):
            add(
                media_url,
                int(photo.get("width") or 0),
                int(photo.get("height") or 0),
            )

    if not photos:
        for detail in data.get("mediaDetails") or []:
            if not isinstance(detail, dict):
                continue
            if detail.get("type") and detail.get("type") != "photo":
                continue
            media_url = detail.get("media_url_https") or detail.get("media_url")
            if not isinstance(media_url, str):
                continue
            info = detail.get("original_info") or {}
            add(
                media_url,
                int(info.get("width") or 0),
                int(info.get("height") or 0),
            )

    return photos


def enrich_twitter_info(info: dict, url: str = "") -> dict:
    """Attach photo entries when yt-dlp returns an empty Twitter result.

    yt-dlp's Twitter extractor intentionally skips still photos. For image
    tweets we fill formats/thumbnails via the public syndication endpoint so
    preview + grab can work.
    """
    if not is_twitter_extractor(info):
        return info

    # Already has video streams — leave alone.
    formats = info.get("formats") or []
    for fmt in formats:
        if isinstance(fmt, dict) and (fmt.get("vcodec") or "none") != "none":
            return info
    entries = info.get("entries")
    if isinstance(entries, list) and any(
        isinstance(e, dict)
        and any(
            (f.get("vcodec") or "none") != "none"
            for f in (e.get("formats") or [])
            if isinstance(f, dict)
        )
        for e in entries
        if e
    ):
        return info

    # Already has a direct image URL / thumbs.
    if isinstance(info.get("url"), str) and "twimg.com" in info["url"]:
        return info
    thumbs = info.get("thumbnails") or []
    if thumbs:
        return info

    tweet_id = tweet_id_from_info(info, url)
    if not tweet_id:
        return info

    data = fetch_syndication_tweet(tweet_id)
    if not data:
        return info

    photos = _photo_entries_from_syndication(data, tweet_id)
    if not photos:
        return info

    user = data.get("user") if isinstance(data.get("user"), dict) else {}
    uploader = user.get("name") or user.get("screen_name")
    title = data.get("text") or info.get("title")
    if isinstance(title, str) and title.startswith("http") and uploader:
        title = str(uploader)

    if len(photos) == 1:
        photo = photos[0]
        enriched = {
            **info,
            **photo,
            "id": tweet_id,
            "display_id": tweet_id,
            "title": title if isinstance(title, str) else photo.get("title"),
            "uploader": uploader if isinstance(uploader, str) else info.get("uploader"),
            "extractor_key": "Twitter",
            "webpage_url": info.get("webpage_url") or url,
        }
        return enriched

    return {
        **info,
        "_type": "playlist",
        "id": tweet_id,
        "title": title if isinstance(title, str) else info.get("title"),
        "uploader": uploader if isinstance(uploader, str) else info.get("uploader"),
        "extractor_key": "Twitter",
        "entries": [
            {
                **photo,
                "title": f"{title} #{index}" if isinstance(title, str) else photo.get("title"),
                "uploader": uploader,
            }
            for index, photo in enumerate(photos, 1)
        ],
    }
