#ifndef PRICE_BAR_H
#define PRICE_BAR_H

#include <string>

struct PriceBar {
    std::string date;
    double close;
    double high;
    double low;
    double open;
    long volume;
};

#endif