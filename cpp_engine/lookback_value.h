#ifndef LOOKBACK_VALUE_H
#define LOOKBACK_VALUE_H

#include <deque>
#include <optional>

class LookbackValue {
private:
    int lookback;
    std::deque<double> history;

public:
    LookbackValue(int lookback_period) : lookback(lookback_period) {}

    std::optional<double> update(double value) {
        history.push_back(value);

        if (history.size() > static_cast<size_t>(lookback) + 1) {
            history.pop_front();
        }

        if (history.size() < static_cast<size_t>(lookback) + 1) {
            return std::nullopt;  // not enough history yet
        }

        return history.front();  // the value from exactly `lookback` bars ago
    }
};

#endif