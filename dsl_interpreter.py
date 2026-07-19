import pandas as pd
from dsl_lexer import tokenize
from dsl_parser import Parser, Assignment, BuyStatement, SellStatement, BinaryOp, Identifier, NumberLiteral, FunctionCall
from decay_detector import DecayDetector


class MovingAverage:
    def __init__(self, window):
        self.window = window
        self.history = []

    def update(self, value):
        self.history.append(value)
        if len(self.history) > self.window:
            self.history.pop(0)
        if len(self.history) < self.window:
            return None
        return sum(self.history) / len(self.history)

class LookbackValue:
    """Remembers the value from exactly N steps ago."""
    def __init__(self, lookback):
        self.lookback = lookback
        self.history = []

    def update(self, value):
        self.history.append(value)
        if len(self.history) > self.lookback + 1:
            self.history.pop(0)
        if len(self.history) < self.lookback + 1:
            return None
        return self.history[0]


class Interpreter:
    def __init__(self, program):
        self.program = program
        self.env = {}
        self.stateful_objects = {}
        self.lookback_objects = {}
        self.prev_env = {}

    def run_bar(self, bar):
        self.prev_env = dict(self.env)
        signals = []

        for stmt in self.program:
            if isinstance(stmt, Assignment):
                value = self.eval_expr(stmt.expression, bar, stmt.name)
                self.env[stmt.name] = value

            elif isinstance(stmt, BuyStatement):
                if self.eval_condition(stmt.condition):
                    signals.append("BUY")

            elif isinstance(stmt, SellStatement):
                if self.eval_condition(stmt.condition):
                    signals.append("SELL")

        return signals

    def eval_expr(self, node, bar, var_name):
        if isinstance(node, NumberLiteral):
            return node.value

        if isinstance(node, Identifier):
            if node.name in bar:
                return bar[node.name]
            return self.env.get(node.name)

        if isinstance(node, FunctionCall):
            if node.name == "moving_average":
                source = self.eval_expr(node.args[0], bar, var_name)
                window = int(node.args[1].value)
                if var_name not in self.stateful_objects:
                    self.stateful_objects[var_name] = MovingAverage(window)
                return self.stateful_objects[var_name].update(source)

            if node.name == "price_n_days_ago":
                source = self.eval_expr(node.args[0], bar, var_name)
                lookback = int(node.args[1].value)
                if var_name not in self.lookback_objects:
                    self.lookback_objects[var_name] = LookbackValue(lookback)
                return self.lookback_objects[var_name].update(source)

            if node.name == "percent_change":
                a = self.eval_expr(node.args[0], bar, var_name)
                b = self.eval_expr(node.args[1], bar, var_name)
                if a is None or b is None:
                    return None
                return (a - b) / b * 100

            raise ValueError(f"Unknown function: {node.name}")

        raise ValueError(f"Cannot evaluate node: {node}")

    def eval_condition(self, node: BinaryOp):
        left = self.eval_expr(node.left, {}, None) if not isinstance(node.left, Identifier) else self.env.get(node.left.name)
        right = self.eval_expr(node.right, {}, None) if not isinstance(node.right, Identifier) else self.env.get(node.right.name)

        if left is None or right is None:
            return False

        if node.operator == "<":
            return left < right
        if node.operator == ">":
            return left > right
        if node.operator == "crosses_above":
            prev_left = self.prev_env.get(node.left.name)
            prev_right = self.prev_env.get(node.right.name)
            if prev_left is None or prev_right is None:
                return False
            return prev_left <= prev_right and left > right
        if node.operator == "crosses_below":
            prev_left = self.prev_env.get(node.left.name)
            prev_right = self.prev_env.get(node.right.name)
            if prev_left is None or prev_right is None:
                return False
            return prev_left >= prev_right and left < right

        raise ValueError(f"Unknown operator: {node.operator}")


if __name__ == "__main__":
    source = """fast_ma = moving_average(close, 5)
slow_ma = moving_average(close, 20)
buy when fast_ma crosses_above slow_ma
sell when fast_ma crosses_below slow_ma"""

    tokens = tokenize(source)
    program = Parser(tokens).parse_program()
    interp = Interpreter(program)

    df = pd.read_csv("aapl_daily.csv")

    SLIPPAGE_PCT = 0.00
    COMMISSION_PCT = 0.00

    position = None
    entry_price = None
    trades = []
    equity = 1.0
    equity_curve = []

    for _, row in df.iterrows():
        bar = {"close": row["Close"], "open": row["Open"], "high": row["High"], "low": row["Low"]}
        signals = interp.run_bar(bar)

        if "BUY" in signals and position is None:
            entry_price = row["Close"] * (1 + SLIPPAGE_PCT / 100) * (1 + COMMISSION_PCT / 100)
            position = entry_price

        elif "SELL" in signals and position is not None:
            fill_price = row["Close"] * (1 - SLIPPAGE_PCT / 100) * (1 - COMMISSION_PCT / 100)
            pnl_pct = (fill_price - position) / position
            trades.append({
                "date": row["Date"],
                "pnl_pct": pnl_pct * 100,
                "win": 1 if pnl_pct > 0 else 0
            })
            print(f"{row['Date']}  SELL @ {fill_price:.2f}   P&L: {pnl_pct*100:+.4f}%")
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
    max_drawdown = drawdown.min() * 100

    daily_returns = equity_series.pct_change().dropna()
    sharpe = (daily_returns.mean() / daily_returns.std()) * (252 ** 0.5)

    print("--- Summary ---")
    print(f"Total trades: {len(trades)}")
    if trades:
        win_trades = [t for t in trades if t["win"] == 1]
        print(f"Win rate: {len(win_trades)/len(trades)*100:.1f}%")
        print(f"Average P&L per trade: {sum(t['pnl_pct'] for t in trades)/len(trades):+.2f}%")
    print(f"Total return: {(equity - 1) * 100:+.2f}%")
    print(f"Max drawdown: {max_drawdown:.2f}%")
    print(f"Sharpe ratio: {sharpe:.2f}")

    print("\n--- Decay Detection (threshold sensitivity check) ---")
    for t in [2.0, 3.0, 4.0, 5.0]:
        detector = DecayDetector(baseline_window=10, threshold=t)
        flags = detector.detect(trades)
        print(f"threshold={t}: {len(flags)} flag(s) -> {[d for _, d in flags]}")

    import json as json_module

    detector = DecayDetector(baseline_window=10, threshold=3.0)
    decay_flags = detector.detect(trades)

    # Health score: simple logic — 100 if no decay ever flagged, drops if flagged,
    # and drops further the more recently a flag occurred relative to total trades
    if not trades:
        health_score = None
    elif not decay_flags:
        health_score = 100
    else:
        most_recent_flag_idx = decay_flags[-1][0]
        recency_ratio = most_recent_flag_idx / len(trades)  # closer to 1.0 = more recent = worse
        health_score = max(0, round(100 - (recency_ratio * 60)))  # flagged recently -> bigger penalty

    dashboard_data = {
        "strategy_name": "momentum_crossover_5_20",
        "total_trades": len(trades),
        "win_rate": (len([t for t in trades if t["win"] == 1]) / len(trades) * 100) if trades else 0,
        "total_return_pct": (equity - 1) * 100,
        "max_drawdown_pct": max_drawdown,
        "sharpe_ratio": sharpe,
        "trades": trades,
        "equity_curve": equity_curve,
        "dates": df["Date"].tolist(),
        "decay_flags": [{"trade_index": idx, "date": date} for idx, date in decay_flags],
        "health_score": health_score
    }

    with open("dashboard_data.json", "w") as f:
        json_module.dump(dashboard_data, f, indent=2)

    print(f"\nExported dashboard data to dashboard_data.json")
    print(f"Health score: {health_score}")