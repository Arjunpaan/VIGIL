import threading
import time
import pandas as pd
from flask import Flask, jsonify
from flask_cors import CORS

from dsl_lexer import tokenize
from dsl_parser import Parser
from dsl_interpreter import Interpreter
from decay_detector import DecayDetector
from live_feed_simulator import LiveFeedSimulator

app = Flask(__name__)
CORS(app)

STRATEGY_SOURCE = """fast_ma = moving_average(close, 5)
slow_ma = moving_average(close, 20)
buy when fast_ma crosses_above slow_ma
sell when fast_ma crosses_below slow_ma"""

# Shared state, updated by the background thread, read by the API.
# A lock protects it since two different threads touch it.
state_lock = threading.Lock()
live_state = {
    "ticker": "RELIANCE",
    "bars_processed": 0,
    "current_price": None,
    "current_date": None,
    "trades": [],
    "health_score": None,
    "confidence": "no_data",
    "status": "starting"
}


def run_live_loop():
    df = pd.read_csv("data/RELIANCE_daily.csv")
    program = Parser(tokenize(STRATEGY_SOURCE)).parse_program()
    interp = Interpreter(program)
    detector = DecayDetector(baseline_window=10, threshold=3.0)
    feed = LiveFeedSimulator(df, delay_seconds=1.0)

    position = None
    trades = []

    with state_lock:
        live_state["status"] = "running"

    while feed.advance():
        row = feed.current_bar()
        bar = {"close": row["Close"], "open": row["Open"], "high": row["High"], "low": row["Low"]}
        signals = interp.run_bar(bar)

        if "BUY" in signals and position is None:
            position = row["Close"]
        elif "SELL" in signals and position is not None:
            pnl_pct = (row["Close"] - position) / position
            trades.append({"date": row["Date"], "pnl_pct": pnl_pct * 100, "win": 1 if pnl_pct > 0 else 0})
            position = None

        flags = detector.detect(trades)
        if not trades or len(trades) < 10:
            health_score, confidence = None, "insufficient_data"
        elif not flags:
            health_score, confidence = 100, "high"
        else:
            recency = flags[-1][0] / len(trades)
            health_score, confidence = max(0, round(100 - recency * 60)), "high"

        with state_lock:
            live_state["bars_processed"] += 1
            live_state["current_price"] = row["Close"]
            live_state["current_date"] = row["Date"]
            live_state["trades"] = trades[-10:]  # last 10 trades only, keep payload small
            live_state["health_score"] = health_score
            live_state["confidence"] = confidence

    with state_lock:
        live_state["status"] = "finished"


@app.route("/api/live-status")
def get_live_status():
    with state_lock:
        return jsonify(dict(live_state))


if __name__ == "__main__":
    thread = threading.Thread(target=run_live_loop, daemon=True)
    thread.start()
    app.run(port=5000, debug=False)