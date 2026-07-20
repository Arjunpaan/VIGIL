from collections import deque


class MarketDataFeed:
    """
    Wraps historical price data and exposes it strictly one bar at a time,
    in chronological order. Once a bar has been consumed, it is physically
    removed from the feed's internal storage — there is no way to access
    it or any future bar through this object. This makes look-ahead bias
    structurally impossible, not just avoided by convention.
    """

    def __init__(self, df):
        # Convert to a deque of dicts up front. Using popleft() means a
        # consumed bar is permanently gone from this object — there is no
        # "peek ahead" or "index into" method exposed anywhere below.
        self._remaining = deque(df.to_dict("records"))
        self._current = None
        self._bars_seen = 0

    def advance(self):
        """Move to the next bar. Returns False when the stream is exhausted."""
        if not self._remaining:
            return False
        self._current = self._remaining.popleft()
        self._bars_seen += 1
        return True

    def current_bar(self):
        """The only way to access data: the single bar just advanced to."""
        if self._current is None:
            raise RuntimeError("No current bar — call advance() first")
        return self._current

    def bars_seen(self):
        return self._bars_seen

    def has_more(self):
        return len(self._remaining) > 0