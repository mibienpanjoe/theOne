from __future__ import annotations

from pathlib import Path

import pytest

from theone.app import ConfirmGrabScreen, TheOneApp
from theone.config import Config
from theone.formats import FormatChoice, MediaItem, ProbeResult


def _carousel_probe() -> ProbeResult:
    items = (
        MediaItem(
            index=1,
            kind="image",
            title="Photo 1",
            thumbnail_urls=("https://cdn.example/1.jpg",),
            duration=None,
            choices=(
                FormatChoice(
                    "",
                    "Image · original",
                    "image",
                    playlist_index=1,
                    image_url="https://cdn.example/full1.jpg",
                ),
            ),
            image_url="https://cdn.example/full1.jpg",
        ),
        MediaItem(
            index=2,
            kind="video",
            title="Clip 2",
            thumbnail_urls=("https://cdn.example/2.jpg",),
            duration="0:08",
            choices=(
                FormatChoice(
                    "bv*+ba/b",
                    "Best · video + audio",
                    "video",
                    playlist_index=2,
                ),
                FormatChoice(
                    "ba/b",
                    "Audio only · best",
                    "audio",
                    audio_only=True,
                    playlist_index=2,
                ),
            ),
        ),
        MediaItem(
            index=3,
            kind="image",
            title="Photo 3",
            thumbnail_urls=("https://cdn.example/3.jpg",),
            duration=None,
            choices=(
                FormatChoice(
                    "",
                    "Image · original",
                    "image",
                    playlist_index=3,
                    image_url="https://cdn.example/full3.jpg",
                ),
            ),
            image_url="https://cdn.example/full3.jpg",
        ),
    )
    return ProbeResult(
        url="https://instagram.com/p/abc/",
        title="Post by athlete",
        uploader="courtifryed",
        duration=None,
        thumbnail_url=items[0].thumbnail_url,
        thumbnail_urls=items[0].thumbnail_urls,
        choices=list(items[0].choices),
        extractor="Instagram",
        items=items,
    )


@pytest.mark.asyncio
async def test_carousel_arrows_change_slide(tmp_path: Path) -> None:
    config = Config(download_dir=tmp_path / "dl")
    app = TheOneApp(
        config=config,
        config_path=tmp_path / "config.toml",
        history_path=tmp_path / "history.json",
    )
    result: list[FormatChoice | None] = []
    probe = _carousel_probe()

    async with app.run_test(size=(100, 40)) as pilot:
        screen = ConfirmGrabScreen(probe)
        app.push_screen(screen, result.append)
        await pilot.pause()
        assert screen._index == 0
        assert "1/3" in screen.query_one("#confirm-meta").render().plain
        assert "● ○ ○" in screen.query_one("#confirm-dots").render().plain

        await pilot.press("right")
        await pilot.pause()
        assert screen._index == 1
        assert "video" in screen.query_one("#confirm-meta").render().plain
        assert "○ ● ○" in screen.query_one("#confirm-dots").render().plain

        await pilot.press("enter")
        await pilot.pause()
        assert len(result) == 1
        assert result[0] is not None
        assert result[0].playlist_index == 2
        assert result[0].kind == "video"


@pytest.mark.asyncio
async def test_carousel_grab_image_slide(tmp_path: Path) -> None:
    config = Config(download_dir=tmp_path / "dl")
    app = TheOneApp(
        config=config,
        config_path=tmp_path / "config.toml",
        history_path=tmp_path / "history.json",
    )
    result: list[FormatChoice | None] = []

    async with app.run_test(size=(100, 40)) as pilot:
        screen = ConfirmGrabScreen(_carousel_probe())
        app.push_screen(screen, result.append)
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert result[0] is not None
        assert result[0].kind == "image"
        assert result[0].image_url.endswith("full1.jpg")
