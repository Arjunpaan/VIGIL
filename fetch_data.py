import yfinance as yf
import os

nifty_tickers = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS",
    "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "WIPRO.NS", "NESTLEIND.NS"
]

os.makedirs("data", exist_ok=True)

successful = []
failed = []

for ticker in nifty_tickers:
    try:
        data = yf.download(ticker, start="2020-01-01", end="2025-01-01", progress=False)
        if data.empty:
            failed.append(ticker)
            continue

        data.columns = data.columns.get_level_values(0)
        missing = data.isna().sum().sum()

        clean_name = ticker.replace(".NS", "")
        filepath = f"data/{clean_name}_daily.csv"
        data.to_csv(filepath)

        print(f"{clean_name}: {data.shape[0]} rows, {missing} missing values -> {filepath}")
        successful.append(clean_name)
    except Exception as e:
        print(f"{ticker}: FAILED - {e}")
        failed.append(ticker)

print(f"\n--- Summary ---")
print(f"Success: {len(successful)} stocks -> {successful}")
print(f"Failed: {len(failed)} stocks -> {failed}")