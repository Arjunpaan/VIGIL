#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <filesystem>
#include <fstream>
#include "json_to_ast.h"
#include "interpreter.h"
#include "data_loader.h"
#include "decay_detector.h"
#include "json.hpp"

namespace fs = std::filesystem;
using json = nlohmann::json;

struct BacktestResult {
    int total_trades;
    double win_rate;
    double total_return_pct;
    double max_drawdown_pct;
    double sharpe_ratio;
    std::vector<TradeRecord> trades;
    std::vector<double> equity_curve;
    std::vector<DecayFlag> decay_flags;
};

BacktestResult run_backtest(const std::vector<ASTNodePtr>& program, const std::vector<PriceBar>& bars) {
    Interpreter interp(program);

    bool in_position = false;
    double entry_price = 0.0;
    std::vector<TradeRecord> trades;
    double equity = 1.0;
    std::vector<double> equity_curve;

    const double SLIPPAGE_PCT = 0.05;
    const double COMMISSION_PCT = 0.03;

    for (const auto& bar_row : bars) {
        std::map<std::string, double> bar = {
            {"close", bar_row.close}, {"open", bar_row.open},
            {"high", bar_row.high}, {"low", bar_row.low}
        };

        std::vector<std::string> signals = interp.run_bar(bar);
        bool has_buy = std::find(signals.begin(), signals.end(), "BUY") != signals.end();
        bool has_sell = std::find(signals.begin(), signals.end(), "SELL") != signals.end();

        if (has_buy && !in_position) {
            entry_price = bar_row.close * (1 + SLIPPAGE_PCT / 100.0) * (1 + COMMISSION_PCT / 100.0);
            in_position = true;
        }

        if (has_sell && in_position) {
            double exit_price = bar_row.close * (1 - SLIPPAGE_PCT / 100.0) * (1 - COMMISSION_PCT / 100.0);
            double pnl_pct = (exit_price - entry_price) / entry_price;
            trades.push_back({bar_row.date, pnl_pct * 100.0, pnl_pct > 0 ? 1 : 0});
            equity *= (1 + pnl_pct);
            in_position = false;
        }

        if (in_position) {
            double unrealized = (bar_row.close - entry_price) / entry_price;
            equity_curve.push_back(equity * (1 + unrealized));
        } else {
            equity_curve.push_back(equity);
        }
    }

    double running_max = equity_curve.empty() ? 1.0 : equity_curve[0];
    double max_drawdown = 0.0;
    for (double e : equity_curve) {
        running_max = std::max(running_max, e);
        max_drawdown = std::min(max_drawdown, (e - running_max) / running_max);
    }

    std::vector<double> daily_returns;
    for (size_t i = 1; i < equity_curve.size(); i++) {
        daily_returns.push_back((equity_curve[i] - equity_curve[i-1]) / equity_curve[i-1]);
    }

    double sharpe = 0.0;
    if (daily_returns.size() > 1) {
        double mean = 0.0;
        for (double r : daily_returns) mean += r;
        mean /= daily_returns.size();

        double variance = 0.0;
        for (double r : daily_returns) variance += (r - mean) * (r - mean);
        variance /= daily_returns.size();
        double stddev = std::sqrt(variance);

        if (stddev != 0.0) sharpe = (mean / stddev) * std::sqrt(252.0);
    }

    DecayDetector detector(10, 3.0);
    std::vector<DecayFlag> flags = detector.detect(trades);

    int wins = 0;
    for (const auto& t : trades) wins += t.win;
    double win_rate = trades.empty() ? 0.0 : (static_cast<double>(wins) / trades.size() * 100.0);

    return {
        static_cast<int>(trades.size()), win_rate, (equity - 1.0) * 100.0,
        max_drawdown * 100.0, sharpe, trades, equity_curve, flags
    };
}

int main() {
    std::vector<ASTNodePtr> program = load_program("strategy.json");

    json portfolio_results;

    for (const auto& entry : fs::directory_iterator("data")) {
        if (entry.path().extension() != ".csv") continue;

        std::string filename = entry.path().filename().string();
        std::string ticker = filename.substr(0, filename.find("_daily.csv"));

        std::vector<PriceBar> bars = load_csv(entry.path().string());
        BacktestResult result = run_backtest(program, bars);

        std::cout << ticker << ": " << result.total_trades << " trades, "
                  << result.win_rate << "% win rate" << std::endl;

        json trades_json = json::array();
        for (const auto& t : result.trades) {
            trades_json.push_back({{"date", t.date}, {"pnl_pct", t.pnl_pct}, {"win", t.win}});
        }

        json flags_json = json::array();
        for (const auto& f : result.decay_flags) {
            flags_json.push_back({{"trade_index", f.trade_index}, {"date", f.date}});
        }

        portfolio_results[ticker] = {
            {"total_trades", result.total_trades},
            {"win_rate", result.win_rate},
            {"total_return_pct", result.total_return_pct},
            {"max_drawdown_pct", result.max_drawdown_pct},
            {"sharpe_ratio", result.sharpe_ratio},
            {"trades", trades_json},
            {"equity_curve", result.equity_curve},
            {"decay_flags", flags_json}
        };
    }

    std::ofstream out("cpp_portfolio_results.json");
    out << portfolio_results.dump(2);

    std::cout << "\nExported cpp_portfolio_results.json" << std::endl;
    return 0;
}