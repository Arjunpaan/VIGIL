#ifndef LIVE_FEED_SIMULATOR_H
#define LIVE_FEED_SIMULATOR_H

#include <thread>
#include <chrono>
#include "market_feed.h"

// Wraps a MarketDataFeed and replays it as if bars are arriving in real
// time, with a real wall-clock delay between each bar. The underlying
// zero-look-ahead guarantee from MarketDataFeed is preserved unchanged —
// this only adds pacing on top.
class LiveFeedSimulator {
private:
    MarketDataFeed feed;
    double delay_seconds;

public:
    LiveFeedSimulator(const std::vector<PriceBar>& bars, double delay_sec)
        : feed(bars), delay_seconds(delay_sec) {}

    bool advance() {
        bool result = feed.advance();
        if (result) {
            std::this_thread::sleep_for(std::chrono::milliseconds(static_cast<int>(delay_seconds * 1000)));
        }
        return result;
    }

    const PriceBar& current_bar() const {
        return feed.current_bar();
    }

    bool has_more() const {
        return feed.has_more();
    }
};

#endif