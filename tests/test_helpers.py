from theone.clipboard import looks_like_url
from theone.theme_detect import terminal_prefers_dark


def test_looks_like_url() -> None:
    assert looks_like_url("https://youtube.com/watch?v=1")
    assert looks_like_url("http://example.com")
    assert looks_like_url("www.example.com/x")
    assert not looks_like_url("not a url")


def test_terminal_prefers_dark(monkeypatch) -> None:
    monkeypatch.setenv("COLORFGBG", "15;0")
    assert terminal_prefers_dark() is True
    monkeypatch.setenv("COLORFGBG", "0;15")
    assert terminal_prefers_dark() is False
    monkeypatch.delenv("COLORFGBG", raising=False)
    assert terminal_prefers_dark() is True
