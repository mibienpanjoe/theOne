from pathlib import Path

import pytest

from theone.downloader import (
    YtDlpNotFoundError,
    build_yt_dlp_args,
    ensure_yt_dlp,
    format_download_error,
    parse_progress_line,
)


def test_build_video_args(tmp_path: Path) -> None:
    args = build_yt_dlp_args(
        "https://example.com/watch?v=1",
        download_dir=tmp_path,
        audio_only=False,
        concurrent_fragments=4,
    )
    assert args[0] == "yt-dlp"
    assert "--no-playlist" in args
    assert "-N" in args
    assert "4" in args
    assert "-P" in args
    assert str(tmp_path) in args
    assert "-x" not in args
    assert args[-1] == "https://example.com/watch?v=1"


def test_build_playlist_item_args(tmp_path: Path) -> None:
    args = build_yt_dlp_args(
        "https://instagram.com/p/abc/",
        download_dir=tmp_path,
        audio_only=False,
        playlist_index=3,
        format_spec="bv*+ba/b",
    )
    assert "--no-playlist" not in args
    assert "--playlist-items" in args
    assert "3" in args


def test_build_with_format_spec(tmp_path: Path) -> None:
    args = build_yt_dlp_args(
        "https://example.com/a",
        download_dir=tmp_path,
        audio_only=False,
        format_spec="bv*[height<=720]+ba/b",
    )
    assert "-f" in args
    assert "bv*[height<=720]+ba/b" in args

    args = build_yt_dlp_args(
        "https://example.com/a",
        download_dir=tmp_path,
        audio_only=False,
        quality="1080",
    )
    assert "-f" in args
    assert "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" in args


def test_build_audio_args(tmp_path: Path) -> None:
    args = build_yt_dlp_args(
        "https://example.com/a",
        download_dir=tmp_path,
        audio_only=True,
        quality="720",
    )
    assert "-x" in args
    assert "--audio-format" in args
    assert "m4a" in args
    assert "-f" not in args  # audio path ignores video quality format


def test_parse_progress_percent() -> None:
    line = "[download]  45.2% of  10.00MiB at  1.50MiB/s ETA 00:07"
    update = parse_progress_line(line)
    assert update is not None
    assert update.percent == 45.2
    assert update.total == "10.00MiB"
    assert update.speed == "1.50MiB/s"
    assert update.eta == "00:07"


def test_parse_destination() -> None:
    line = "[download] Destination: /tmp/Cool Title [abc].mp4"
    update = parse_progress_line(line)
    assert update is not None
    assert update.destination == "/tmp/Cool Title [abc].mp4"


def test_parse_title() -> None:
    line = "[info] Cool Video: Downloading 1 format(s): 22"
    update = parse_progress_line(line)
    assert update is not None
    assert update.title == "Cool Video"


def test_ensure_yt_dlp_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("theone.downloader.shutil.which", lambda _name: None)
    with pytest.raises(YtDlpNotFoundError):
        ensure_yt_dlp()


def test_format_outdated_extractor_message() -> None:
    lines = [
        "Traceback (most recent call last):",
        '  File "youtube.py", line 1',
        "ERROR: Fn6w-B0cXHQ: Unable to extract Initial JS player n function name; "
        "Confirm you are on the latest version using yt-dlp -U.",
    ]
    msg = format_download_error(lines, exit_code=1)
    assert "outdated" in msg.lower() or "Update with" in msg
    assert "Traceback" not in msg


def test_format_403_message() -> None:
    msg = format_download_error(
        ["ERROR: unable to download video data: HTTP Error 403: Forbidden"],
        exit_code=1,
    )
    assert "403" in msg
    assert "cookies_from_browser" in msg
    assert "JS runtime" in msg


def test_build_args_includes_js_runtime_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "theone.downloader.detect_js_runtime", lambda: "node:/usr/bin/node"
    )
    args = build_yt_dlp_args(
        "https://example.com/a",
        download_dir=tmp_path,
        audio_only=False,
    )
    assert "--js-runtimes" in args
    assert "node:/usr/bin/node" in args
