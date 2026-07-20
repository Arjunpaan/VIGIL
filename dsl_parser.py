from dsl_lexer import tokenize, TokenType

class BinaryOp:
    """Represents: left OPERATOR right, e.g. fast_ma crosses_above slow_ma"""
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def __repr__(self):
        return f"BinaryOp({self.left!r} {self.operator!r} {self.right!r})"

class LogicalOp:
    """Represents: left AND/OR right, e.g. (a > b) and (c < d)"""
    def __init__(self, left, operator, right):
        self.left = left
        self.operator = operator
        self.right = right

    def __repr__(self):
        return f"LogicalOp({self.left!r} {self.operator!r} {self.right!r})"


class Identifier:
    """Represents a name reference, e.g. fast_ma"""
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"Identifier({self.name!r})"

class NumberLiteral:
    """Represents a fixed numeric value, e.g. -10 or 126"""
    def __init__(self, value):
        self.value = float(value)

    def __repr__(self):
        return f"NumberLiteral({self.value})"


class BuyStatement:
    """Represents: buy when <condition>"""
    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"BuyStatement({self.condition!r})"


class SellStatement:
    """Represents: sell when <condition>"""
    def __init__(self, condition):
        self.condition = condition

    def __repr__(self):
        return f"SellStatement({self.condition!r})"

class Assignment:
    """Represents: name = expression, e.g. fast_ma = moving_average(close, 10)"""
    def __init__(self, name, expression):
        self.name = name
        self.expression = expression

    def __repr__(self):
        return f"Assignment({self.name!r} = {self.expression!r})"


class FunctionCall:
    """Represents: func_name(arg1, arg2, ...)"""
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return f"FunctionCall({self.name!r}, {self.args!r})"



class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        return self.tokens[self.pos]

    def advance(self):
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def parse_condition(self):
        # left side: expect an IDENTIFIER
        left_token = self.advance()
        if left_token.type != TokenType.IDENTIFIER:
            raise ValueError(f"Expected identifier, got {left_token}")
        left = Identifier(left_token.value)

        # operator: expect an OPERATOR
        op_token = self.advance()
        if op_token.type != TokenType.OPERATOR:
            raise ValueError(f"Expected operator, got {op_token}")
        operator = op_token.value

        # right side: could be an IDENTIFIER or a NUMBER
        right_token = self.advance()
        if right_token.type == TokenType.IDENTIFIER:
            right = Identifier(right_token.value)
        elif right_token.type == TokenType.NUMBER:
            right = NumberLiteral(right_token.value)
        else:
            raise ValueError(f"Expected identifier or number, got {right_token}")

        return BinaryOp(left, operator, right)
    
    def parse_logical_condition(self):
        left = self.parse_condition()

        while self.current().type == TokenType.KEYWORD and self.current().value in ("and", "or"):
            op_token = self.advance()
            right = self.parse_condition()
            left = LogicalOp(left, op_token.value, right)

        return left


    def parse_statement(self):
        token = self.current()

        if token.type == TokenType.KEYWORD and token.value == "buy":
            self.advance()
            self.expect_keyword("when")
            condition = self.parse_logical_condition()
            return BuyStatement(condition)

        if token.type == TokenType.KEYWORD and token.value == "sell":
            self.advance()
            self.expect_keyword("when")
            condition = self.parse_logical_condition()
            return SellStatement(condition)

        if token.type == TokenType.IDENTIFIER:
            name = token.value
            self.advance()
            self.expect_operator("=")
            expression = self.parse_value()
            return Assignment(name, expression)

        raise ValueError(f"Unexpected token at start of statement: {token}")

    def expect_keyword(self, expected_word):
        token = self.advance()
        if token.type != TokenType.KEYWORD or token.value != expected_word:
            raise ValueError(f"Expected keyword '{expected_word}', got {token}")

    def expect_operator(self, expected_symbol):
        token = self.advance()
        if token.type != TokenType.OPERATOR or token.value != expected_symbol:
            raise ValueError(f"Expected operator '{expected_symbol}', got {token}")

    def parse_program(self):
        statements = []
        while self.current().type != TokenType.EOF:
            # skip blank lines
            if self.current().type == TokenType.NEWLINE:
                self.advance()
                continue
            stmt = self.parse_statement()
            statements.append(stmt)
        return statements

    def parse_value(self):
        """Parses a single value: either a number, or an identifier, or a function call."""
        token = self.advance()

        if token.type == TokenType.NUMBER:
            return NumberLiteral(token.value)

        if token.type == TokenType.IDENTIFIER:
            # Could be a plain identifier OR a function call — check what comes next
            if self.current().type == TokenType.LPAREN:
                return self.parse_function_call(token.value)
            return Identifier(token.value)

        raise ValueError(f"Expected a value, got {token}")

    def parse_function_call(self, func_name):
        self.advance()  # consume '('
        args = []

        # handle the case of zero arguments: func()
        if self.current().type != TokenType.RPAREN:
            args.append(self.parse_value())
            while self.current().type == TokenType.COMMA:
                self.advance()  # consume ','
                args.append(self.parse_value())

        self.advance()  # consume ')'
        return FunctionCall(func_name, args)


if __name__ == "__main__":
    source = "buy when close > 100 and volume >= 500"
    tokens = tokenize(source)
    parser = Parser(tokens)
    stmt = parser.parse_statement()
    print(stmt)