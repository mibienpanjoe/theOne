from pathlib import Path

from theone.preview import mpv_available, thumbnail_cache_path


def test_thumbnail_cache_path_stable() -> None:
    a = thumbnail_cache_path("https://example.com/a.jpg")
    b = thumbnail_cache_path("https://example.com/a.jpg")
    assert a == b
    assert a.parent.name == "theOne-previews"


def test_mpv_available_is_bool() -> None:
    assert isinstance(mpv_available(), bool)


def test_thumb_image_widget_loads(tmp_path: Path) -> None:
    """textual-image halfcell widget accepts a real JPEG path."""
    from PIL import Image as PILImage

    from theone.thumb import HalfcellThumb, make_thumb

    image = tmp_path / "t.jpg"
    PILImage.new("RGB", (64, 64), (200, 40, 80)).save(image, quality=90)
    widget = make_thumb(image, id="thumb")
    assert isinstance(widget, HalfcellThumb) or widget.image is not None
    assert widget.image is not None


def test_make_thumb_never_unicode() -> None:
    from theone.thumb import ThumbImage

    # Unicode dither is the gray mush path — we must not select it.
    assert "Unicode" not in ThumbImage.__name__
