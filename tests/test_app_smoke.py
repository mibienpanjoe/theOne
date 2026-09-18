from __future__ import annotations

import re
from pathlib import Path

import pytest

from theone.app import BRAND, DownloadDirScreen, TheOneApp, progress_bar
from theone.config import Config
from theone.widgets import render_brand

_ALIGN_RE = re.compile(r"\balign:\s*(\S+)\s+(\S+)\s*;")
_VALID_H = {"left", "center", "right"}
_VALID_V = {"top", "middle", "bottom"}


def test_align_values_are_valid() -> None:
    for css in (TheOneApp.CSS, DownloadDirScreen.CSS):
        for match in _ALIGN_RE.finditer(css):
            horizontal, vertical = match.group(1), match.group(2)
            assert horizontal in _VALID_H, f"bad horizontal align: {horizontal}"
            assert vertical in _VALID_V, f"bad vertical align: {vertical}"


def test_brand_glyphs_spell_theone() -> None:
    assert BRAND == render_brand("theOne")
    assert "████" in BRAND
    # capital O glyph is the rounded 5-row form, not a lowercase n-style
    lines = BRAND.splitlines()
    assert len(lines) == 5


def test_progress_bar_fill() -> None:
    assert progress_bar(0, width=10) == "░" * 10
    assert progress_bar(100, width=10) == "█" * 10
    assert progress_bar(50, width=10).count("█") == 5


@pytest.mark.asyncio
async def test_grab_stays_inside_linkbar(tmp_path: Path) -> None:
    config = Config(download_dir=tmp_path / "dl")
    app = TheOneApp(
        config=config,
        config_path=tmp_path / "config.toml",
        history_path=tmp_path / "history.json",
    )
    async with app.run_test(size=(100, 40)) as pilot:
        linkbar = app.query_one("#linkbar")
        btn = app.query_one("#grab-btn")
        assert btn.parent is linkbar
        # Button must sit within the linkbar region (not a sibling outside the border)
        assert linkbar.region.contains(btn.region.x, btn.region.y)
        assert linkbar.border_title == "Paste a link"
        assert app.query_one("#prompt").render().plain.strip() == ">"
        hints = app.query_one("#hints").render().plain
        assert "⏎ grab" in hints
        assert app.theme == "theone-dark"
        await pilot.pause()
