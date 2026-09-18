from pathlib import Path

from theone.platforms import (
    platform_subdir,
    prefers_instant_best,
    resolve_download_dir,
)


def test_prefers_instant_best_hosts() -> None:
    assert prefers_instant_best("https://www.instagram.com/reel/abc/")
    assert prefers_instant_best("https://www.tiktok.com/@x/video/1")
    assert prefers_instant_best("https://x.com/user/status/1")
    assert prefers_instant_best("https://twitter.com/user/status/1")
    assert prefers_instant_best("https://www.threads.net/@u/post/1")
    assert not prefers_instant_best("https://www.youtube.com/watch?v=1")


def test_prefers_instant_best_extractors() -> None:
    assert prefers_instant_best("https://example.com/x", extractor="Instagram")
    assert prefers_instant_best("https://example.com/x", extractor="TikTok")
    assert not prefers_instant_best("https://example.com/x", extractor="Youtube")


def test_platform_subdir_known_hosts() -> None:
    assert platform_subdir("https://www.youtube.com/watch?v=1") == "youtube"
    assert platform_subdir("https://youtu.be/abc") == "youtube"
    assert platform_subdir("https://m.youtube.com/watch?v=1") == "youtube"
    assert platform_subdir("https://www.instagram.com/p/abc/") == "instagram"
    assert platform_subdir("https://www.tiktok.com/@u/video/1") == "tiktok"
    assert platform_subdir("https://vm.tiktok.com/ZMabc/") == "tiktok"
    assert platform_subdir("https://x.com/u/status/1") == "x"
    assert platform_subdir("https://twitter.com/u/status/1") == "x"
    assert platform_subdir("https://www.threads.net/@u/post/1") == "threads"
    assert platform_subdir("https://vimeo.com/123") == "vimeo"
    assert platform_subdir("https://www.reddit.com/r/x/comments/1/") == "reddit"


def test_platform_subdir_extractor_fallback() -> None:
    assert platform_subdir("https://example.com/share/1", extractor="Youtube") == "youtube"
    assert platform_subdir("https://example.com/share/1", extractor="TikTok") == "tiktok"
    assert platform_subdir("https://example.com/share/1", extractor="Twitter") == "x"


def test_platform_subdir_unknown_uses_host_or_other() -> None:
    assert platform_subdir("https://www.obscurevids.example/v/1") == "obscurevids"
    assert platform_subdir("not-a-url") == "other"


def test_resolve_download_dir(tmp_path: Path) -> None:
    base = tmp_path / "theOne"
    dest = resolve_download_dir(base, "https://www.youtube.com/watch?v=1")
    assert dest == base / "youtube"
