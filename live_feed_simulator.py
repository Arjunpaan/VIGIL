import time
from market_feed import MarketDataFeed


class LiveFeedSimulator:
    """
    Wraps a MarketDataFeed and replays it as if bars are arriving in real
    time, with a real wall-clock delay between each bar. This simulates
    a live market data stream without requiring an actual live data
    subscription — the underlying zero-look-ahead guarantee from
    MarketDataFeed is preserved unchanged.
    """

    def __init__(self, df, delay_seconds=1.0):
        self.feed = MarketDataFeed(df)
        self.delay_seconds = delay_seconds

    def advance(self):
        result = self.feed.advance()
        if result:
            time.sleep(self.delay_seconds)
        return result

    def current_bar(self):
        return self.feed.current_bar()

    def has_more(self):
        return self.feed.has_more()