from dsl_lexer import tokenize
from dsl_parser import Parser
from dsl_interpreter import Interpreter

source = "buy when close > 100 and volume >= 500"
tokens = tokenize(source)
program = Parser(tokens).parse_program()
interp = Interpreter(program)

signals = interp.run_bar({"close": 150, "volume": 600})
print("Test 1 (both true):", signals)

signals = interp.run_bar({"close": 50, "volume": 600})
print("Test 2 (one false):", signals)