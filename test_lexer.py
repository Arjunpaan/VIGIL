from dsl_lexer import tokenize, TokenType


def test_tokenize_simple_condition():
    tokens = tokenize("fast_ma crosses_above slow_ma")
    assert tokens[0].type == TokenType.IDENTIFIER
    assert tokens[0].value == "fast_ma"
    assert tokens[1].type == TokenType.OPERATOR
    assert tokens[1].value == "crosses_above"
    assert tokens[2].type == TokenType.IDENTIFIER
    assert tokens[2].value == "slow_ma"
    assert tokens[3].type == TokenType.EOF


def test_tokenize_negative_number():
    tokens = tokenize("pct_change < -10")
    assert tokens[0].value == "pct_change"
    assert tokens[1].type == TokenType.OPERATOR
    assert tokens[1].value == "<"
    assert tokens[2].type == TokenType.NUMBER
    assert tokens[2].value == "-10"


def test_tokenize_keywords():
    tokens = tokenize("buy when sell")
    assert tokens[0].type == TokenType.KEYWORD
    assert tokens[0].value == "buy"
    assert tokens[1].type == TokenType.KEYWORD
    assert tokens[1].value == "when"
    assert tokens[2].type == TokenType.KEYWORD
    assert tokens[2].value == "sell"


def test_tokenize_function_call():
    tokens = tokenize("moving_average(close, 10)")
    types = [t.type for t in tokens]
    assert types == [
        TokenType.IDENTIFIER, TokenType.LPAREN, TokenType.IDENTIFIER,
        TokenType.COMMA, TokenType.NUMBER, TokenType.RPAREN, TokenType.EOF
    ]


def test_tokenize_unknown_character_raises():
    try:
        tokenize("buy @ fast_ma")
        assert False, "Expected a ValueError for unknown character"
    except ValueError as e:
        assert "@" in str(e)


def test_tokenize_multiline():
    source = "buy when a > b\nsell when a < b"
    tokens = tokenize(source)
    newline_tokens = [t for t in tokens if t.type == TokenType.NEWLINE]
    assert len(newline_tokens) == 1