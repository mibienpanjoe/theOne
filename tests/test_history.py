from pathlib import Path

from theone.history import load_history, push_history, save_history


def test_history_push_dedupes_and_caps(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    push_history("https://a.example/1", path)
    push_history("https://a.example/2", path)
    push_history("https://a.example/1", path)
    items = load_history(path)
    assert items[0] == "https://a.example/1"
    assert items[1] == "https://a.example/2"
    assert len(items) == 2


def test_save_history_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "history.json"
    save_history(["https://x.test/a", "https://x.test/b"], path)
    assert load_history(path) == ["https://x.test/a", "https://x.test/b"]
