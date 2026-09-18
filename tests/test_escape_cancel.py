from __future__ import annotations

from pathlib import Path

import pytest

from theone.app import ConfirmGrabScreen, FormatPickerScreen, TheOneApp
from theone.config import Config
from theone.formats import FormatChoice, ProbeResult


def _probe(*, title: str = "Test") -> ProbeResult:
    return ProbeResult(
        url="https://example.com/v",
        title=title,
        uploader="u",
        duration="0:10",
        thumbnail_url=None,
        thumbnail_urls=(),
        choices=[
            FormatChoice(format_spec="bv*+ba/b", label="best", kind="video"),
            FormatChoice(
                format_spec="ba/b",
                label="audio",
                kind="audio",
                audio_only=True,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_escape_cancels_confirm_screen(tmp_path: Path) -> None:
    config = Config(download_dir=tmp_path / "dl")
    app = TheOneApp(
        config=config,
        config_path=tmp_path / "config.toml",
        history_path=tmp_path / "history.json",
    )
    result: list[FormatChoice | None] = []

    async with app.run_test(size=(100, 40)) as pilot:
        app.push_screen(ConfirmGrabScreen(_probe()), result.append)
        await pilot.pause()
        assert isinstance(app.screen, ConfirmGrabScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert result == [None]
        assert not isinstance(app.screen, ConfirmGrabScreen)


@pytest.mark.asyncio
async def test_escape_cancels_format_picker(tmp_path: Path) -> None:
    config = Config(download_dir=tmp_path / "dl")
    app = TheOneApp(
        config=config,
        config_path=tmp_path / "config.toml",
        history_path=tmp_path / "history.json",
    )
    result: list[FormatChoice | None] = []

    async with app.run_test(size=(100, 40)) as pilot:
        app.push_screen(FormatPickerScreen(_probe()), result.append)
        await pilot.pause()
        assert isinstance(app.screen, FormatPickerScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert result == [None]
        assert not isinstance(app.screen, FormatPickerScreen)
