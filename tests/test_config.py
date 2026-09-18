from __future__ import annotations

from pathlib import Path

from theone.config import Config, cycle_quality, cycle_theme, load_config, save_config


def test_load_missing_returns_defaults(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / "missing.toml")
    assert cfg.download_dir is None
    assert cfg.theme == "auto"
    assert cfg.audio_only is False
    assert cfg.concurrent_fragments == 8
    assert cfg.quality == "best"
    assert cfg.use_aria2c is False


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "theOne" / "config.toml"
    original = Config(
        download_dir=tmp_path / "Videos" / "theOne",
        theme="dark",
        audio_only=True,
        concurrent_fragments=16,
        quality="1080",
        use_aria2c=True,
    )
    save_config(original, path)
    loaded = load_config(path)
    assert loaded.download_dir == original.download_dir
    assert loaded.theme == "dark"
    assert loaded.audio_only is True
    assert loaded.concurrent_fragments == 16
    assert loaded.quality == "1080"
    assert loaded.use_aria2c is True


def test_cycle_theme() -> None:
    assert cycle_theme("auto") == "dark"
    assert cycle_theme("dark") == "light"
    assert cycle_theme("light") == "auto"


def test_cycle_quality() -> None:
    assert cycle_quality("best") == "1080"
    assert cycle_quality("1080") == "720"
    assert cycle_quality("720") == "best"
