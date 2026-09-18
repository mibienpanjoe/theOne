from __future__ import annotations

from pathlib import Path

import pytest

from theone.downloader import DownloadJob, download_image


@pytest.mark.asyncio
async def test_download_image_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    dest_dir = tmp_path / "out"
    payload = b"\xff\xd8\xff\xe0" + b"fake-jpeg-bytes"

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return payload

    def fake_urlopen(req, timeout=30):  # noqa: ANN001, ARG001
        return _Resp()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    updates = []
    async for update in download_image(
        "https://cdn.example/photo.jpg",
        download_dir=dest_dir,
        title="Court shot",
        playlist_index=2,
        job=DownloadJob(),
    ):
        updates.append(update)

    assert updates[-1].done and updates[-1].success
    assert updates[-1].destination is not None
    path = Path(updates[-1].destination)
    assert path.is_file()
    assert path.read_bytes() == payload
    assert "Court shot" in path.name
    assert "[2]" in path.name
