from dsl_lexer import tokenize
from dsl_parser import Parser, BinaryOp, Identifier, NumberLiteral, Assignment, BuyStatement, SellStatement, FunctionCall


def test_parse_simple_condition():
    tokens = tokenize("fast_ma crosses_above slow_ma")
    tree = Parser(tokens).parse_condition()
    assert isinstance(tree, BinaryOp)
    assert isinstance(tree.left, Identifier)
    assert tree.left.name == "fast_ma"
    assert tree.operator == "crosses_above"
    assert isinstance(tree.right, Identifier)
    assert tree.right.name == "slow_ma"


def test_parse_condition_with_number():
    tokens = tokenize("pct_change < -10")
    tree = Parser(tokens).parse_condition()
    assert isinstance(tree.right, NumberLiteral)
    assert tree.right.value == -10.0


def test_parse_assignment_with_function_call():
    tokens = tokenize("fast_ma = moving_average(close, 10)")
    tree = Parser(tokens).parse_statement()
    assert isinstance(tree, Assignment)
    assert tree.name == "fast_ma"
    assert isinstance(tree.expression, FunctionCall)
    assert tree.expression.name == "moving_average"
    assert len(tree.expression.args) == 2
    assert tree.expression.args[0].name == "close"
    assert tree.expression.args[1].value == 10.0


def test_parse_buy_statement():
    tokens = tokenize("buy when fast_ma crosses_above slow_ma")
    tree = Parser(tokens).parse_statement()
    assert isinstance(tree, BuyStatement)
    assert isinstance(tree.condition, BinaryOp)


def test_parse_sell_statement():
    tokens = tokenize("sell when fast_ma crosses_below slow_ma")
    tree = Parser(tokens).parse_statement()
    assert isinstance(tree, SellStatement)


def test_parse_full_program():
    source = """fast_ma = moving_average(close, 5)
slow_ma = moving_average(close, 20)
buy when fast_ma crosses_above slow_ma
sell when fast_ma crosses_below slow_ma"""
    tokens = tokenize(source)
    program = Parser(tokens).parse_program()
    assert len(program) == 4
    assert isinstance(program[0], Assignment)
    assert isinstance(program[1], Assignment)
    assert isinstance(program[2], BuyStatement)
    assert isinstance(program[3], SellStatement)


def test_parse_invalid_statement_raises():
    tokens = tokenize("123 abc")
    try:
        Parser(tokens).parse_statement()
        assert False, "Expected a ValueError for invalid statement"
    except ValueError:
        pass