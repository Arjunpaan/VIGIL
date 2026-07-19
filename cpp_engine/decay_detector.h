#ifndef DECAY_DETECTOR_H
#define DECAY_DETECTOR_H

#include <vector>
#include <string>
#include <algorithm>

struct DecayFlag {
    int trade_index;
    std::string date;
};

struct TradeRecord {
    std::string date;
    double pnl_pct;
    int win;  // 1 or 0
};

class DecayDetector {
private:
    int baseline_window;
    double threshold;

public:
    DecayDetector(int baseline_window_, double threshold_)
        : baseline_window(baseline_window_), threshold(threshold_) {}

    std::vector<DecayFlag> detect(const std::vector<TradeRecord>& trades) {
        std::vector<DecayFlag> flags;

        if (static_cast<int>(trades.size()) <= baseline_window) {
            return flags;  // not enough data for a baseline
        }

        double baseline_sum = 0.0;
        for (int i = 0; i < baseline_window; i++) {
            baseline_sum += trades[i].win;
        }
        double baseline_rate = baseline_sum / baseline_window;

        double cusum_pos = 0.0;
        double cusum_neg = 0.0;

        for (size_t i = baseline_window; i < trades.size(); i++) {
            double deviation = trades[i].win - baseline_rate;

            cusum_pos = std::max(0.0, cusum_pos + deviation);
            cusum_neg = std::min(0.0, cusum_neg + deviation);

            if (cusum_pos > threshold || std::abs(cusum_neg) > threshold) {
                flags.push_back({static_cast<int>(i), trades[i].date});
                cusum_pos = 0.0;
                cusum_neg = 0.0;
            }
        }

        return flags;
    }
};

#endif