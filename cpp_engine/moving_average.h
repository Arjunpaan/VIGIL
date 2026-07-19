#ifndef MOVING_AVERAGE_H
#define MOVING_AVERAGE_H

#include <deque>
#include <optional>

class MovingAverage {
private:
    int window;
    std::deque<double> history;
    double running_sum = 0.0;

public:
    MovingAverage(int window_size) : window(window_size) {}

    std::optional<double> update(double value) {
        history.push_back(value);
        running_sum += value;

        if (history.size() > static_cast<size_t>(window)) {
            running_sum -= history.front();
            history.pop_front();
        }

        if (history.size() < static_cast<size_t>(window)) {
            return std::nullopt;  // not enough data yet
        }

        return running_sum / window;
    }
};

#endif