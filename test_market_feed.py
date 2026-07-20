from market_feed import MarketDataFeed
import pandas as pd


def test_feed_only_exposes_current_bar():
    df = pd.DataFrame({"Close": [10, 20, 30], "Date": ["d1", "d2", "d3"]})
    feed = MarketDataFeed(df)

    feed.advance()
    assert feed.current_bar()["Close"] == 10

    # Confirm there is no way to reach ahead — the object exposes no
    # indexing, no peek, nothing beyond current_bar() and advance().
    assert not hasattr(feed, "__getitem__")
    assert not hasattr(feed, "peek")

    feed.advance()
    assert feed.current_bar()["Close"] == 20  # moved forward, old bar inaccessible


def test_feed_exhausts_correctly():
    df = pd.DataFrame({"Close": [10, 20], "Date": ["d1", "d2"]})
    feed = MarketDataFeed(df)

    assert feed.advance() is True
    assert feed.advance() is True
    assert feed.advance() is False  # no more bars
    assert feed.has_more() is False


def test_feed_bars_seen_count():
    df = pd.DataFrame({"Close": [10, 20, 30], "Date": ["d1", "d2", "d3"]})
    feed = MarketDataFeed(df)

    while feed.advance():
        pass

    assert feed.bars_seen() == 3