from theone.formats import pick_image_url, probe_from_info
from theone.twitter import (
    enrich_twitter_info,
    syndication_token,
    tweet_id_from_info,
)


def test_syndication_token_matches_known_value() -> None:
    # Verified against yt-dlp's Twitter syndication helper for this id.
    assert syndication_token("2082901388703526933") == "51rmlih9w9"


def test_tweet_id_from_status_url() -> None:
    assert (
        tweet_id_from_info({}, "https://x.com/mibienpan26/status/2082901388703526933/photo/1")
        == "2082901388703526933"
    )
    assert tweet_id_from_info({"id": "2082901388703526933"}, "") == "2082901388703526933"


def test_pick_image_url_accepts_twimg_without_ext() -> None:
    url = "https://pbs.twimg.com/media/HOfzxVWXIAAqx_9.jpg?name=orig"
    assert pick_image_url({"url": url}) == url
    bare = "https://pbs.twimg.com/media/HOfzxVWXIAAqx_9"
    assert pick_image_url({"url": bare}) == bare


def test_enrich_twitter_info_from_fixture() -> None:
    empty = {
        "id": "2082901388703526933",
        "title": "PARE Mibienpan - https://t.co/BdLIfb8eHc",
        "extractor_key": "Twitter",
        "formats": [],
        "original_url": "https://t.co/BdLIfb8eHc",
    }

    def fake_fetch(tweet_id: str):
        assert tweet_id == "2082901388703526933"
        return {
            "user": {"name": "PARE Mibienpan", "screen_name": "mibienpan26"},
            "text": "https://t.co/BdLIfb8eHc",
            "photos": [
                {
                    "url": "https://pbs.twimg.com/media/HOfzxVWXIAAqx_9.jpg",
                    "width": 736,
                    "height": 673,
                }
            ],
        }

    import theone.twitter as twitter_mod

    original = twitter_mod.fetch_syndication_tweet
    twitter_mod.fetch_syndication_tweet = fake_fetch  # type: ignore[assignment]
    try:
        enriched = enrich_twitter_info(empty, "https://t.co/BdLIfb8eHc")
    finally:
        twitter_mod.fetch_syndication_tweet = original

    assert "pbs.twimg.com/media/" in (enriched.get("url") or "")
    probe = probe_from_info(enriched, "https://t.co/BdLIfb8eHc")
    assert probe.items[0].kind == "image"
    assert probe.items[0].image_url
    assert "twimg.com" in probe.items[0].image_url
