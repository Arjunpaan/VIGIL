import os
import json
import pandas as pd
from dsl_lexer import tokenize
from dsl_parser import Parser
from dsl_interpreter import Interpreter
from decay_detector import DecayDetector

STRATEGIES = {
    "momentum_crossover_5_20": """fast_ma = moving_average(close, 5)
slow_ma = moving_average(close, 20)
buy when fast_ma crosses_above slow_ma
sell when fast_ma crosses_below slow_ma""",

    "mean_reversion_6mo": """price_6mo_ago = price_n_days_ago(close, 126)
pct_change = percent_change(close, price_6mo_ago)
buy when pct_change < -10
sell when pct_change > 0"""
}

SLIPPAGE_PCT = 0.05
COMMISSION_PCT = 0.03


def run_backtest(source, df):
    tokens = tokenize(source)
    program = Parser(tokens).parse_program()
    interp = Interpreter(program)

    position = None
    trades = []
    equity = 1.0
    equity_curve = []

    from market_feed import MarketDataFeed

    feed = MarketDataFeed(df)
    while feed.advance():
        row = feed.current_bar()
        bar = {"close": row["Close"], "open": row["Open"], "high": row["High"], "low": row["Low"]}
        signals = interp.run_bar(bar)

        if "BUY" in signals and position is None:
            position = row["Close"] * (1 + SLIPPAGE_PCT / 100) * (1 + COMMISSION_PCT / 100)

        elif "SELL" in signals and position is not None:
            fill_price = row["Close"] * (1 - SLIPPAGE_PCT / 100) * (1 - COMMISSION_PCT / 100)
            pnl_pct = (fill_price - position) / position
            trades.append({
                "date": row["Date"],
                "pnl_pct": pnl_pct * 100,
                "win": 1 if pnl_pct > 0 else 0
            })
            equity *= (1 + pnl_pct)
            position = None

        if position is not None:
            unrealized_pct = (row["Close"] - position) / position
            equity_curve.append(equity * (1 + unrealized_pct))
        else:
            equity_curve.append(equity)

    equity_series = pd.Series(equity_curve)
    running_max = equity_series.cummax()
    drawdown = (equity_series - running_max) / running_max
    max_drawdown = drawdown.min() * 100 if len(drawdown) > 0 else 0

    daily_returns = equity_series.pct_change().dropna()
    if len(daily_returns) > 1 and daily_returns.std() != 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * (252 ** 0.5)
    else:
        sharpe = 0.0

    detector = DecayDetector(baseline_window=10, threshold=3.0)
    decay_flags = detector.detect(trades)

    MIN_TRADES_FOR_CONFIDENCE = 15  # fewer trades than this = we can't really trust the score

    if not trades:
        health_score = None
        confidence = "no_data"
    elif len(trades) < MIN_TRADES_FOR_CONFIDENCE:
        # Not enough trades to trust any health judgment — say so honestly
        health_score = None
        confidence = "insufficient_data"
    elif not decay_flags:
        health_score = 100
        confidence = "high"
    else:
        most_recent_flag_idx = decay_flags[-1][0]
        recency_ratio = most_recent_flag_idx / len(trades)
        health_score = max(0, round(100 - (recency_ratio * 60)))
        confidence = "high"


    return {
        "total_trades": len(trades),
        "win_rate": (len([t for t in trades if t["win"] == 1]) / len(trades) * 100) if trades else 0,
        "total_return_pct": (equity - 1) * 100,
        "max_drawdown_pct": max_drawdown,
        "sharpe_ratio": sharpe,
        "trades": trades,
        "equity_curve": equity_curve,
        "dates": df["Date"].tolist(),
        "decay_flags": [{"trade_index": idx, "date": date} for idx, date in decay_flags],
        "health_score": health_score,
        "confidence": confidence
    }


def main():
    data_dir = "data"
    csv_files = [f for f in os.listdir(data_dir) if f.endswith("_daily.csv")]

    portfolio_results = {}

    for csv_file in csv_files:
        ticker = csv_file.replace("_daily.csv", "")
        df = pd.read_csv(os.path.join(data_dir, csv_file))

        portfolio_results[ticker] = {}

        for strategy_name, strategy_source in STRATEGIES.items():
            print(f"Running {strategy_name} on {ticker}...")
            result = run_backtest(strategy_source, df)
            portfolio_results[ticker][strategy_name] = result
            print(f"  -> {result['total_trades']} trades, {result['win_rate']:.1f}% win rate, health score: {result['health_score']}")

    with open("portfolio_data.json", "w") as f:
        json.dump(portfolio_results, f, indent=2)

    print(f"\nExported portfolio_data.json — {len(csv_files)} stocks x {len(STRATEGIES)} strategies")

    # Quick aggregate summary across everything
    total_trades_all = sum(
        r["total_trades"] for stock in portfolio_results.values() for r in stock.values()
    )
    print(f"Total trades across entire portfolio: {total_trades_all}")

def run_backtest_with_position_sizing(source, df, starting_equity=100000, risk_per_trade_pct=0.02, stop_loss_pct=0.05):
    tokens = tokenize(source)
    program = Parser(tokens).parse_program()
    interp = Interpreter(program)

    position = None          # None, or dict: {entry_price, units, stop_price}
    trades = []
    equity = starting_equity
    equity_curve = []

    for _, row in df.iterrows():
        bar = {"close": row["Close"], "open": row["Open"], "high": row["High"], "low": row["Low"]}
        signals = interp.run_bar(bar)

        # Check stop-loss first, before processing new signals —
        # a real risk system always checks "am I already about to lose too much"
        # before considering a new trade.
        if position is not None and row["Close"] <= position["stop_price"]:
            exit_price = position["stop_price"] * (1 - SLIPPAGE_PCT / 100)
            pnl = (exit_price - position["entry_price"]) * position["units"]
            equity += pnl
            trades.append({
                "date": row["Date"], "pnl_pct": (pnl / (position["entry_price"] * position["units"])) * 100,
                "win": 1 if pnl > 0 else 0, "exit_reason": "stop_loss"
            })
            position = None

        elif "BUY" in signals and position is None:
            entry_price = row["Close"] * (1 + SLIPPAGE_PCT / 100) * (1 + COMMISSION_PCT / 100)
            stop_price = entry_price * (1 - stop_loss_pct)
            risk_amount = equity * risk_per_trade_pct
            stop_distance = entry_price - stop_price
            units = risk_amount / stop_distance

            position = {"entry_price": entry_price, "units": units, "stop_price": stop_price}

        elif "SELL" in signals and position is not None:
            exit_price = row["Close"] * (1 - SLIPPAGE_PCT / 100) * (1 - COMMISSION_PCT / 100)
            pnl = (exit_price - position["entry_price"]) * position["units"]
            equity += pnl
            trades.append({
                "date": row["Date"], "pnl_pct": (pnl / (position["entry_price"] * position["units"])) * 100,
                "win": 1 if pnl > 0 else 0, "exit_reason": "signal"
            })
            position = None

        if position is not None:
            unrealized = (row["Close"] - position["entry_price"]) * position["units"]
            equity_curve.append(equity + unrealized)
        else:
            equity_curve.append(equity)

    return trades, equity_curve, equity

def run_position_sized_portfolio():
    import os
    data_dir = "data"
    csv_files = [f for f in os.listdir(data_dir) if f.endswith("_daily.csv")]

    results = {}
    for csv_file in csv_files:
        ticker = csv_file.replace("_daily.csv", "")
        df = pd.read_csv(os.path.join(data_dir, csv_file))
        results[ticker] = {}

        for strategy_name, strategy_source in STRATEGIES.items():
            trades, equity_curve, final_equity = run_backtest_with_position_sizing(
                strategy_source, df, starting_equity=100000, risk_per_trade_pct=0.02, stop_loss_pct=0.05
            )
            stop_outs = len([t for t in trades if t.get("exit_reason") == "stop_loss"])
            results[ticker][strategy_name] = {
                "final_equity": final_equity,
                "total_return_pct": (final_equity - 100000) / 100000 * 100,
                "total_trades": len(trades),
                "stopped_out_trades": stop_outs,
                "win_rate": (len([t for t in trades if t["win"] == 1]) / len(trades) * 100) if trades else 0
            }
            print(f"{ticker} / {strategy_name}: ₹{final_equity:,.0f} final ({results[ticker][strategy_name]['total_return_pct']:+.1f}%), {stop_outs} stop-outs")

    with open("position_sized_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\nExported position_sized_results.json")


if __name__ == "__main__":
    main()
    run_position_sized_portfolio()