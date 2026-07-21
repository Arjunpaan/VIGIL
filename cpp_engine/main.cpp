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
#include "market_feed.h"

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

struct PositionSizedTrade {
    std::string date;
    double pnl_pct;
    int win;
    std::string exit_reason;
};

struct PositionSizedResult {
    double final_equity;
    double total_return_pct;
    int total_trades;
    int stopped_out_trades;
    double win_rate;
};

PositionSizedResult run_backtest_position_sized(
    const std::vector<ASTNodePtr>& program,
    const std::vector<PriceBar>& bars,
    double starting_equity = 100000.0,
    double risk_per_trade_pct = 0.02,
    double stop_loss_pct = 0.05
) {
    Interpreter interp(program);

    bool in_position = false;
    double entry_price = 0.0, units = 0.0, stop_price = 0.0;
    std::vector<PositionSizedTrade> trades;
    double equity = starting_equity;

    const double SLIPPAGE_PCT = 0.05;
    const double COMMISSION_PCT = 0.03;

    MarketDataFeed feed(bars);
    while (feed.advance()) {
        const PriceBar& bar_row = feed.current_bar();
        std::map<std::string, double> bar = {
            {"close", bar_row.close}, {"open", bar_row.open},
            {"high", bar_row.high}, {"low", bar_row.low}
        };

        std::vector<std::string> signals = interp.run_bar(bar);
        bool has_buy = std::find(signals.begin(), signals.end(), "BUY") != signals.end();
        bool has_sell = std::find(signals.begin(), signals.end(), "SELL") != signals.end();

        // Check stop-loss first, before any new signal — same priority as Python
        if (in_position && bar_row.close <= stop_price) {
            double exit_price = stop_price * (1 - SLIPPAGE_PCT / 100.0);
            double pnl = (exit_price - entry_price) * units;
            equity += pnl;
            trades.push_back({bar_row.date, (pnl / (entry_price * units)) * 100.0, pnl > 0 ? 1 : 0, "stop_loss"});
            in_position = false;
        }
        else if (has_buy && !in_position) {
            entry_price = bar_row.close * (1 + SLIPPAGE_PCT / 100.0) * (1 + COMMISSION_PCT / 100.0);
            stop_price = entry_price * (1 - stop_loss_pct);
            double risk_amount = equity * risk_per_trade_pct;
            double stop_distance = entry_price - stop_price;
            units = risk_amount / stop_distance;
            in_position = true;
        }
        else if (has_sell && in_position) {
            double exit_price = bar_row.close * (1 - SLIPPAGE_PCT / 100.0) * (1 - COMMISSION_PCT / 100.0);
            double pnl = (exit_price - entry_price) * units;
            equity += pnl;
            trades.push_back({bar_row.date, (pnl / (entry_price * units)) * 100.0, pnl > 0 ? 1 : 0, "signal"});
            in_position = false;
        }
    }

    int wins = 0, stop_outs = 0;
    for (const auto& t : trades) {
        wins += t.win;
        if (t.exit_reason == "stop_loss") stop_outs++;
    }

    return {
        equity,
        (equity - starting_equity) / starting_equity * 100.0,
        static_cast<int>(trades.size()),
        stop_outs,
        trades.empty() ? 0.0 : (static_cast<double>(wins) / trades.size() * 100.0)
    };
}



BacktestResult run_backtest(const std::vector<ASTNodePtr>& program, const std::vector<PriceBar>& bars) {
    Interpreter interp(program);

    bool in_position = false;
    double entry_price = 0.0;
    std::vector<TradeRecord> trades;
    double equity = 1.0;
    std::vector<double> equity_curve;

    const double SLIPPAGE_PCT = 0.05;
    const double COMMISSION_PCT = 0.03;

    MarketDataFeed feed(bars);
    while (feed.advance()) {
        const PriceBar& bar_row = feed.current_bar();
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

    std::cout << "\n--- Position-Sized Backtest ---" << std::endl;
    json position_sized_results;

    for (const auto& entry : fs::directory_iterator("data")) {
        if (entry.path().extension() != ".csv") continue;
        std::string filename = entry.path().filename().string();
        std::string ticker = filename.substr(0, filename.find("_daily.csv"));

        std::vector<PriceBar> bars = load_csv(entry.path().string());
        PositionSizedResult result = run_backtest_position_sized(program, bars);

        std::cout << ticker << ": Rs " << result.final_equity << " (" << result.total_return_pct
                  << "%), " << result.stopped_out_trades << " stop-outs" << std::endl;

        position_sized_results[ticker] = {
            {"final_equity", result.final_equity},
            {"total_return_pct", result.total_return_pct},
            {"total_trades", result.total_trades},
            {"stopped_out_trades", result.stopped_out_trades},
            {"win_rate", result.win_rate}
        };
    }

    std::ofstream ps_out("cpp_position_sized_results.json");
    ps_out << position_sized_results.dump(2);
    std::cout << "\nExported cpp_position_sized_results.json" << std::endl;
    return 0;
}