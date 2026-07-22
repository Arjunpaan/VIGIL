#ifndef RSI_H
#define RSI_H

#include <deque>
#include <optional>
#include <algorithm>

// Relative Strength Index — measures momentum via the ratio of average
// gains to average losses over a rolling window. Classic values:
// RSI < 30 = oversold, RSI > 70 = overbought.
class RSI {
private:
    int window;
    bool has_prev_price = false;
    double prev_price = 0.0;
    std::deque<double> gains;
    std::deque<double> losses;

public:
    RSI(int window_size) : window(window_size) {}

    std::optional<double> update(double price) {
        if (!has_prev_price) {
            prev_price = price;
            has_prev_price = true;
            return std::nullopt;  // no prior price yet, can't compute a change
        }

        double change = price - prev_price;
        prev_price = price;

        double gain = std::max(change, 0.0);
        double loss = std::max(-change, 0.0);

        gains.push_back(gain);
        losses.push_back(loss);
        if (static_cast<int>(gains.size()) > window) {
            gains.pop_front();
            losses.pop_front();
        }

        if (static_cast<int>(gains.size()) < window) {
            return std::nullopt;  // not enough history yet
        }

        double avg_gain = 0.0, avg_loss = 0.0;
        for (double g : gains) avg_gain += g;
        for (double l : losses) avg_loss += l;
        avg_gain /= window;
        avg_loss /= window;

        if (avg_loss == 0.0) {
            return 100.0;  // no losses at all in the window — maximally overbought
        }

        double rs = avg_gain / avg_loss;
        return 100.0 - (100.0 / (1.0 + rs));
    }
};

#endif