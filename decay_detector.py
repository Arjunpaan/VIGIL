import numpy as np


class DecayDetector:
    """
    Watches a strategy's trade outcomes over time and flags when the
    underlying win rate has shifted meaningfully from its baseline,
    using CUSUM (Cumulative Sum) change-point detection.
    """

    def __init__(self, baseline_window=10, threshold=3.0):
        # baseline_window: how many early trades define "normal" behavior
        # threshold: how far the cumulative sum must drift before we flag decay
        self.baseline_window = baseline_window
        self.threshold = threshold

    def detect(self, trades):
        """
        trades: list of dicts with a 'win' key (1 or 0), in chronological order.
        Returns a list of (trade_index, date) where decay was flagged.
        """
        wins = np.array([t["win"] for t in trades])

        if len(wins) <= self.baseline_window:
            return []  # not enough data to establish a baseline yet

        baseline_rate = wins[:self.baseline_window].mean()

        cusum_pos = 0.0
        cusum_neg = 0.0
        flags = []

        for i in range(self.baseline_window, len(wins)):
            deviation = wins[i] - baseline_rate

            cusum_pos = max(0, cusum_pos + deviation)
            cusum_neg = min(0, cusum_neg + deviation)

            if cusum_pos > self.threshold or abs(cusum_neg) > self.threshold:
                flags.append((i, trades[i]["date"]))
                cusum_pos = 0.0  # reset after flagging, so we can detect further shifts
                cusum_neg = 0.0

        return flags