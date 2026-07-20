#ifndef MARKET_FEED_H
#define MARKET_FEED_H

#include <deque>
#include <optional>
#include "price_bar.h"

// Wraps historical price data and exposes it strictly one bar at a time,
// in chronological order. Once a bar has been consumed, it is physically
// removed from this object's internal storage — there is no way to access
// it or any future bar through this class. This makes look-ahead bias
// structurally impossible, not just avoided by convention.
class MarketDataFeed {
private:
    std::deque<PriceBar> remaining;
    std::optional<PriceBar> current;
    int bars_seen_count = 0;

public:
    MarketDataFeed(const std::vector<PriceBar>& bars)
        : remaining(bars.begin(), bars.end()) {}

    // Move to the next bar. Returns false when the stream is exhausted.
    bool advance() {
        if (remaining.empty()) return false;
        current = remaining.front();
        remaining.pop_front();
        bars_seen_count++;
        return true;
    }

    // The only way to access data: the single bar just advanced to.
    const PriceBar& current_bar() const {
        return current.value();
    }

    int bars_seen() const {
        return bars_seen_count;
    }

    bool has_more() const {
        return !remaining.empty();
    }
};

#endif