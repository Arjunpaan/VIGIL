from dsl_lexer import tokenize
from dsl_parser import Parser
from dsl_interpreter import Interpreter
import pandas as pd

source = """rsi_val = rsi(close, 14)
buy when rsi_val < 30
sell when rsi_val > 70"""

program = Parser(tokenize(source)).parse_program()
interp = Interpreter(program)

df = pd.read_csv("data/RELIANCE_daily.csv")
signal_count = 0
for _, row in df.iterrows():
    bar = {"close": row["Close"], "open": row["Open"], "high": row["High"], "low": row["Low"]}
    signals = interp.run_bar(bar)
    if signals:
        print(row["Date"], signals)
        signal_count += 1

print(f"\nTotal signals: {signal_count}")