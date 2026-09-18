from __future__ import annotations

from pathlib import Path

import pytest

from theone.downloader import DownloadJob, run_download


class FakeStdout:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines
        self._i = 0

    def __aiter__(self) -> FakeStdout:
        return self

    async def __anext__(self) -> bytes:
        if self._i >= len(self._lines):
            raise StopAsyncIteration
        line = self._lines[self._i]
        self._i += 1
        return line


class FakeProc:
    def __init__(self, lines: list[bytes], returncode: int = 0) -> None:
        self.stdout = FakeStdout(lines)
        self.returncode = returncode
        self.signals: list[int] = []

    async def wait(self) -> int:
        return self.returncode

    def send_signal(self, sig: int) -> None:
        self.signals.append(sig)
        self.returncode = -sig

    def kill(self) -> None:
        self.returncode = -9


@pytest.mark.asyncio
async def test_run_download_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [
        b"[info] Cool: Downloading 1 format(s): 22\n",
        b"[download] Destination: /tmp/video [id].mp4\n",
        b"[download]  50.0% of  2.00MiB at  1.00MiB/s ETA 00:01\n",
        b"[download] 100.0% of  2.00MiB at  1.00MiB/s ETA 00:00\n",
    ]

    async def fake_exec(*_args, **_kwargs):
        return FakeProc(lines, returncode=0)

    monkeypatch.setattr("theone.downloader.ensure_yt_dlp", lambda: "yt-dlp")

    updates = [
        u
        async for u in run_download(
            "https://example.com/v",
            download_dir=tmp_path,
            audio_only=False,
            create_subprocess_exec=fake_exec,
        )
    ]
    assert any(u.title == "Cool" for u in updates)
    assert any(u.percent == 50.0 for u in updates)
    assert updates[-1].done and updates[-1].success
    assert updates[-1].destination == "/tmp/video [id].mp4"


@pytest.mark.asyncio
async def test_run_download_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lines = [b"ERROR: Unsupported URL\n"]

    async def fake_exec(*_args, **_kwargs):
        return FakeProc(lines, returncode=1)

    monkeypatch.setattr("theone.downloader.ensure_yt_dlp", lambda: "yt-dlp")

    updates = [
        u
        async for u in run_download(
            "https://example.com/bad",
            download_dir=tmp_path,
            audio_only=False,
            create_subprocess_exec=fake_exec,
        )
    ]
    assert updates[-1].done
    assert not updates[-1].success
    assert updates[-1].error
    assert "Unsupported URL" in updates[-1].error


@pytest.mark.asyncio
async def test_run_download_cancel(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    job = DownloadJob()

    class SlowStdout:
        def __aiter__(self):
            return self

        async def __anext__(self):
            job.cancel()
            raise StopAsyncIteration

    class SlowProc(FakeProc):
        def __init__(self) -> None:
            super().__init__([], returncode=None)
            self.stdout = SlowStdout()

    async def fake_exec(*_args, **_kwargs):
        return SlowProc()

    monkeypatch.setattr("theone.downloader.ensure_yt_dlp", lambda: "yt-dlp")

    updates = [
        u
        async for u in run_download(
            "https://example.com/v",
            download_dir=tmp_path,
            audio_only=False,
            job=job,
            create_subprocess_exec=fake_exec,
        )
    ]
    assert updates[-1].cancelled
    assert updates[-1].done
    assert not updates[-1].success
