"""Load and save ~/.config/theOne/config.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

ThemeName = Literal["auto", "dark", "light"]
QualityName = Literal["best", "1080", "720"]

DEFAULT_CONCURRENT_FRAGMENTS = 8
QUALITY_ORDER: tuple[QualityName, ...] = ("best", "1080", "720")


@dataclass
class Config:
    download_dir: Path | None = None
    theme: ThemeName = "auto"
    audio_only: bool = False
    concurrent_fragments: int = DEFAULT_CONCURRENT_FRAGMENTS
    quality: QualityName = "best"
    use_aria2c: bool = False
    # e.g. "firefox", "chrome", "chromium", "brave", "edge"
    cookies_from_browser: str | None = None

    def with_updates(self, **kwargs: object) -> Config:
        data = asdict(self)
        data.update(kwargs)
        if data["download_dir"] is not None and not isinstance(data["download_dir"], Path):
            data["download_dir"] = Path(data["download_dir"])
        return Config(**data)


def default_config_path() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "theOne" / "config.toml"


def load_config(path: Path | None = None) -> Config:
    config_path = path or default_config_path()
    if not config_path.is_file():
        return Config()

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    download_dir = raw.get("download_dir")
    theme = raw.get("theme", "auto")
    if theme not in ("auto", "dark", "light"):
        theme = "auto"

    quality = raw.get("quality", "best")
    if quality not in QUALITY_ORDER:
        quality = "best"

    cookies = raw.get("cookies_from_browser")
    if cookies is not None:
        cookies = str(cookies).strip() or None

    return Config(
        download_dir=Path(download_dir).expanduser() if download_dir else None,
        theme=theme,
        audio_only=bool(raw.get("audio_only", False)),
        concurrent_fragments=int(
            raw.get("concurrent_fragments", DEFAULT_CONCURRENT_FRAGMENTS)
        ),
        quality=quality,
        use_aria2c=bool(raw.get("use_aria2c", False)),
        cookies_from_browser=cookies,
    )


def save_config(config: Config, path: Path | None = None) -> Path:
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f'theme = "{config.theme}"',
        f"audio_only = {'true' if config.audio_only else 'false'}",
        f"concurrent_fragments = {config.concurrent_fragments}",
        f'quality = "{config.quality}"',
        f"use_aria2c = {'true' if config.use_aria2c else 'false'}",
    ]
    if config.cookies_from_browser:
        lines.append(f'cookies_from_browser = "{config.cookies_from_browser}"')
    if config.download_dir is not None:
        lines.insert(0, f'download_dir = "{config.download_dir}"')

    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config_path


def cycle_theme(current: ThemeName) -> ThemeName:
    order: tuple[ThemeName, ...] = ("auto", "dark", "light")
    return order[(order.index(current) + 1) % len(order)]


def cycle_quality(current: QualityName) -> QualityName:
    return QUALITY_ORDER[(QUALITY_ORDER.index(current) + 1) % len(QUALITY_ORDER)]
