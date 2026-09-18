from theone.formats import FormatChoice, build_format_choices, probe_from_info


def test_build_format_choices_curates_heights_and_audio() -> None:
    info = {
        "title": "Demo",
        "formats": [
            {
                "format_id": "137",
                "height": 1080,
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "none",
                "tbr": 4000,
                "filesize": 50_000_000,
            },
            {
                "format_id": "136",
                "height": 720,
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "none",
                "tbr": 2000,
                "filesize": 25_000_000,
            },
            {
                "format_id": "18",
                "height": 360,
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
                "tbr": 500,
            },
            {
                "format_id": "140",
                "height": None,
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "mp4a",
                "tbr": 128,
            },
        ],
    }
    choices = build_format_choices(info)
    assert choices[0].format_spec == "bv*+ba/b"
    assert choices[-1].audio_only is True
    heights = [c.height for c in choices if c.height]
    assert heights == [1080, 720, 360]
    assert any("1080p" in c.label for c in choices)


def test_probe_from_info_includes_meta() -> None:
    info = {
        "title": "Me at the zoo",
        "uploader": "jawed",
        "duration": 19,
        "thumbnail": "https://example.com/t.jpg",
        "formats": [
            {
                "format_id": "18",
                "height": 360,
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
            }
        ],
    }
    probe = probe_from_info(info, "https://youtube.com/watch?v=1")
    assert probe.title == "Me at the zoo"
    assert probe.uploader == "jawed"
    assert probe.duration == "0:19"
    assert probe.thumbnail_url is not None
    assert probe.thumbnail_url.endswith("t.jpg")
    assert probe.thumbnail_urls
    assert probe.choices


def test_pick_thumbnail_prefers_largest_from_list() -> None:
    from theone.formats import pick_thumbnail_url, pick_thumbnail_urls

    info = {
        "thumbnail": "https://example.com/small.jpg",
        "thumbnails": [
            {"url": "https://example.com/small.jpg", "height": 100, "width": 100},
            {"url": "https://cdn.example/ig-large.jpg", "height": 720, "width": 720},
            {"url": "https://cdn.example/tiktok.jpg", "height": 480, "width": 480},
        ],
    }
    assert pick_thumbnail_url(info) == "https://cdn.example/ig-large.jpg"
    urls = pick_thumbnail_urls(info)
    assert urls[0] == "https://cdn.example/ig-large.jpg"
    assert "https://example.com/small.jpg" in urls


def test_pick_thumbnail_penalizes_maxres_webp() -> None:
    from theone.formats import pick_thumbnail_urls

    info = {
        "thumbnails": [
            {
                "url": "https://i.ytimg.com/vi_webp/x/maxresdefault.webp",
                "height": 1080,
                "width": 1920,
                "preference": 10,
            },
            {
                "url": "https://i.ytimg.com/vi/x/hqdefault.jpg",
                "height": 360,
                "width": 480,
                "preference": 0,
            },
        ]
    }
    urls = pick_thumbnail_urls(info)
    assert urls[0].endswith("hqdefault.jpg")


def test_pick_thumbnail_falls_back_to_direct() -> None:
    from theone.formats import pick_thumbnail_url

    assert (
        pick_thumbnail_url({"thumbnail": "https://example.com/only.jpg"})
        == "https://example.com/only.jpg"
    )


def test_pick_thumbnail_prefers_uncropped_instagram() -> None:
    from theone.formats import pick_image_url, pick_thumbnail_urls

    cropped = (
        "https://ig.cdn/x.jpg?stp=c0.128.1024.1024a_dst-jpg_e35_s1024x1024_tt6"
    )
    full = "https://ig.cdn/x.jpg?stp=dst-jpg_e35_tt6"
    info = {
        "thumbnail": full,
        "thumbnails": [
            {"url": cropped, "width": 1024, "height": 1024, "id": "0"},
            {"url": full, "width": 0, "height": 0, "id": "12"},
            {
                "url": "https://ig.cdn/x.jpg?stp=dst-jpg_e35_p720x720_tt6",
                "width": 720,
                "height": 900,
                "id": "11",
            },
        ],
    }
    urls = pick_thumbnail_urls(info)
    assert urls[0] == full
    assert "c0." not in urls[0]
    assert pick_image_url(info) == full


def test_format_choice_frozen() -> None:
    choice = FormatChoice("ba/b", "Audio only · best", "audio", audio_only=True)
    assert choice.audio_only


def test_probe_carousel_mixed_image_and_video() -> None:
    info = {
        "_type": "playlist",
        "title": "Post by athlete",
        "uploader": "courtifryed",
        "extractor_key": "Instagram",
        "entries": [
            {
                "id": "img1",
                "title": "Photo 1",
                "thumbnail": "https://cdn.example/1.jpg",
                "url": "https://cdn.example/full1.jpg",
                "formats": [],
            },
            {
                "id": "vid2",
                "title": "Clip 2",
                "duration": 8,
                "thumbnail": "https://cdn.example/2.jpg",
                "formats": [
                    {
                        "format_id": "0",
                        "height": 720,
                        "ext": "mp4",
                        "vcodec": "avc1",
                        "acodec": "mp4a",
                    }
                ],
            },
            {
                "id": "img3",
                "title": "Photo 3",
                "thumbnails": [{"url": "https://cdn.example/3.jpg", "height": 1080}],
                "formats": [],
            },
        ],
    }
    probe = probe_from_info(info, "https://instagram.com/p/abc/")
    assert probe.is_carousel
    assert len(probe.items) == 3
    assert probe.items[0].kind == "image"
    assert probe.items[0].image_url.endswith("full1.jpg")
    assert probe.items[1].kind == "video"
    assert probe.items[1].choices[0].playlist_index == 2
    assert probe.items[2].kind == "image"
    assert probe.uploader == "courtifryed"


def test_probe_single_video_still_works() -> None:
    info = {
        "title": "Me at the zoo",
        "uploader": "jawed",
        "duration": 19,
        "thumbnail": "https://example.com/t.jpg",
        "formats": [
            {
                "format_id": "18",
                "height": 360,
                "ext": "mp4",
                "vcodec": "avc1",
                "acodec": "mp4a",
            }
        ],
    }
    probe = probe_from_info(info, "https://youtube.com/watch?v=1")
    assert not probe.is_carousel
    assert len(probe.items) == 1
    assert probe.items[0].kind == "video"
