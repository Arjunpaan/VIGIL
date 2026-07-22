import pandas as pd
from dsl_lexer import tokenize
from dsl_parser import Parser
from dsl_interpreter import Interpreter
from decay_detector import DecayDetector
from live_feed_simulator import LiveFeedSimulator

STRATEGY_SOURCE = """fast_ma = moving_average(close, 5)
slow_ma = moving_average(close, 20)
buy when fast_ma crosses_above slow_ma
sell when fast_ma crosses_below slow_ma"""


def run_live_monitor(csv_path, delay_seconds=0.05, max_bars=200):
    df = pd.read_csv(csv_path)
    program = Parser(tokenize(STRATEGY_SOURCE)).parse_program()
    interp = Interpreter(program)

    feed = LiveFeedSimulator(df, delay_seconds=delay_seconds)
    detector = DecayDetector(baseline_window=10, threshold=3.0)

    position = None
    trades = []
    bars_processed = 0

    print(f"Starting live monitor — replaying {csv_path} at {delay_seconds}s/bar")
    print("-" * 60)

    while feed.advance() and bars_processed < max_bars:
        row = feed.current_bar()
        bars_processed += 1
        bar = {"close": row["Close"], "open": row["Open"], "high": row["High"], "low": row["Low"]}
        signals = interp.run_bar(bar)

        if "BUY" in signals and position is None:
            position = row["Close"]
            print(f"[{row['Date']}] LIVE SIGNAL: BUY @ {position:.2f}")

        elif "SELL" in signals and position is not None:
            pnl_pct = (row["Close"] - position) / position
            trades.append({"date": row["Date"], "pnl_pct": pnl_pct * 100, "win": 1 if pnl_pct > 0 else 0})
            print(f"[{row['Date']}] LIVE SIGNAL: SELL @ {row['Close']:.2f}  P&L: {pnl_pct*100:+.2f}%")
            position = None

            # Re-run decay detection after every new trade — this is the
            # actual point of live monitoring: continuous re-evaluation,
            # not a one-time end-of-backtest check.
            flags = detector.detect(trades)
            if flags and flags[-1][0] == len(trades) - 1:
                print(f"    ⚠ DECAY DETECTED at trade #{len(trades)} — win rate has shifted from baseline")

    print("-" * 60)
    print(f"Live monitor stopped. {bars_processed} bars processed, {len(trades)} trades executed.")


if __name__ == "__main__":
    run_live_monitor("data/RELIANCE_daily.csv", delay_seconds=0.05, max_bars=300)