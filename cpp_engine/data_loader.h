#ifndef DATA_LOADER_H
#define DATA_LOADER_H

#include <vector>
#include <string>
#include <fstream>
#include <sstream>
#include <iostream>
#include "price_bar.h"

std::vector<PriceBar> load_csv(const std::string& filepath) {
    std::vector<PriceBar> bars;
    std::ifstream file(filepath);

    if (!file.is_open()) {
        std::cerr << "Could not open file: " << filepath << std::endl;
        return bars;
    }

    std::string line;
    std::getline(file, line);  // skip header row

    while (std::getline(file, line)) {
        std::stringstream ss(line);
        std::string field;
        PriceBar bar;

        std::getline(ss, bar.date, ',');

        std::getline(ss, field, ',');
        bar.close = std::stod(field);

        std::getline(ss, field, ',');
        bar.high = std::stod(field);

        std::getline(ss, field, ',');
        bar.low = std::stod(field);

        std::getline(ss, field, ',');
        bar.open = std::stod(field);

        std::getline(ss, field, ',');
        bar.volume = std::stol(field);

        bars.push_back(bar);
    }

    return bars;
}

#endif