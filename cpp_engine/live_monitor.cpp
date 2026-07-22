#include <iostream>
#include <iomanip>
#include "json_to_ast.h"
#include "interpreter.h"
#include "data_loader.h"
#include "decay_detector.h"
#include "live_feed_simulator.h"

int main() {
    std::vector<ASTNodePtr> program = load_program("strategy.json");
    std::vector<PriceBar> bars = load_csv("data/RELIANCE_daily.csv");

    Interpreter interp(program);
    DecayDetector detector(10, 3.0);

    bool in_position = false;
    double entry_price = 0.0;
    std::vector<TradeRecord> trades;
    int bars_processed = 0;
    const int max_bars = 300;

    std::cout << "Starting live monitor -- replaying RELIANCE at 0.05s/bar" << std::endl;
    std::cout << "------------------------------------------------------------" << std::endl;

    LiveFeedSimulator feed(bars, 0.05);

    while (feed.advance() && bars_processed < max_bars) {
        const PriceBar& bar_row = feed.current_bar();
        bars_processed++;

        std::map<std::string, double> bar = {
            {"close", bar_row.close}, {"open", bar_row.open},
            {"high", bar_row.high}, {"low", bar_row.low}
        };

        std::vector<std::string> signals = interp.run_bar(bar);
        bool has_buy = std::find(signals.begin(), signals.end(), "BUY") != signals.end();
        bool has_sell = std::find(signals.begin(), signals.end(), "SELL") != signals.end();

        if (has_buy && !in_position) {
            entry_price = bar_row.close;
            in_position = true;
            std::cout << "[" << bar_row.date << "] LIVE SIGNAL: BUY @ " << entry_price << std::endl;
        }

        if (has_sell && in_position) {
            double exit_price = bar_row.close;
            double pnl_pct = (exit_price - entry_price) / entry_price;
            trades.push_back({bar_row.date, pnl_pct * 100.0, pnl_pct > 0 ? 1 : 0});
            std::cout << "[" << bar_row.date << "] LIVE SIGNAL: SELL @ " << exit_price
                      << "  P&L: " << (pnl_pct * 100.0) << "%" << std::endl;
            in_position = false;

            // Re-check decay after every new trade -- continuous monitoring,
            // not a single end-of-run report.
            std::vector<DecayFlag> flags = detector.detect(trades);
            if (!flags.empty() && flags.back().trade_index == static_cast<int>(trades.size()) - 1) {
                std::cout << "    !! DECAY DETECTED at trade #" << trades.size()
                          << " -- win rate has shifted from baseline" << std::endl;
            }
        }
    }

    std::cout << "------------------------------------------------------------" << std::endl;
    std::cout << "Live monitor stopped. " << bars_processed << " bars processed, "
              << trades.size() << " trades executed." << std::endl;

    return 0;
}