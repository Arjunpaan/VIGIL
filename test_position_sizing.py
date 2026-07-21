import pandas as pd
from run_portfolio import run_backtest_with_position_sizing, STRATEGIES

df = pd.read_csv("data/RELIANCE_daily.csv")
trades, equity_curve, final_equity = run_backtest_with_position_sizing(
    STRATEGIES["momentum_crossover_5_20"], df,
    starting_equity=100000, risk_per_trade_pct=0.02, stop_loss_pct=0.05
)

print(f"Starting equity: ₹100,000")
print(f"Final equity: ₹{final_equity:,.2f}")
print(f"Total trades: {len(trades)}")
stop_outs = [t for t in trades if t.get("exit_reason") == "stop_loss"]
print(f"Trades stopped out: {len(stop_outs)}")
for t in trades[:5]:
    print(t)