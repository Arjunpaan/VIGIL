from enum import Enum, auto

class TokenType(Enum):
    KEYWORD = auto()      # strategy, buy, sell, when
    IDENTIFIER = auto()   # fast_ma, close, slow_ma
    NUMBER = auto()        # 10, 126, -10
    OPERATOR = auto()      # =, <, >, crosses_above, crosses_below
    LPAREN = auto()         # (
    RPAREN = auto()         # )
    COMMA = auto()          # ,
    COLON = auto()          # :
    NEWLINE = auto()
    EOF = auto()            # marks end of input

class Token:
    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return f"Token({self.type}, {repr(self.value)})"



KEYWORDS = {"strategy", "buy", "sell", "when", "and", "or"}
WORD_OPERATORS = {"crosses_above", "crosses_below"}

def tokenize(source: str):
    tokens = []
    i = 0
    n = len(source)

    while i < n:
        char = source[i]

        # Skip spaces and tabs (but not newlines — those matter in our DSL)
        if char == " " or char == "\t":
            i += 1
            continue

        # Newline
        if char == "\n":
            tokens.append(Token(TokenType.NEWLINE, "\n"))
            i += 1
            continue

        # Numbers (handles things like 10, 126, and decimals like 0.5)
        if char.isdigit() or (char == "-" and i + 1 < n and source[i+1].isdigit()):
            start = i
            i += 1  # consume the digit or the '-'
            while i < n and (source[i].isdigit() or source[i] == "."):
                i += 1
            tokens.append(Token(TokenType.NUMBER, source[start:i]))
            continue

        # Identifiers and keywords (letters, digits, underscores — but must start with a letter or _)


        if char.isalpha() or char == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            word = source[start:i]
            if word in KEYWORDS:
                tokens.append(Token(TokenType.KEYWORD, word))
            elif word in WORD_OPERATORS:
                tokens.append(Token(TokenType.OPERATOR, word))
            else:
                tokens.append(Token(TokenType.IDENTIFIER, word))
            continue

        # Single-character symbols
        if char == "(":
            tokens.append(Token(TokenType.LPAREN, char))
            i += 1
            continue
        if char == ")":
            tokens.append(Token(TokenType.RPAREN, char))
            i += 1
            continue
        if char == ",":
            tokens.append(Token(TokenType.COMMA, char))
            i += 1
            continue
        if char == ":":
            tokens.append(Token(TokenType.COLON, char))
            i += 1
            continue
        if char == "=":
            tokens.append(Token(TokenType.OPERATOR, char))
            i += 1
            continue
        if char == "<":
            if i + 1 < n and source[i+1] == "=":
                tokens.append(Token(TokenType.OPERATOR, "<="))
                i += 2
            else:
                tokens.append(Token(TokenType.OPERATOR, "<"))
                i += 1
            continue
        if char == ">":
            if i + 1 < n and source[i+1] == "=":
                tokens.append(Token(TokenType.OPERATOR, ">="))
                i += 2
            else:
                tokens.append(Token(TokenType.OPERATOR, ">"))
                i += 1
            continue
        if char == "!":
            if i + 1 < n and source[i+1] == "=":
                tokens.append(Token(TokenType.OPERATOR, "!="))
                i += 2
                continue
            raise ValueError(f"Unexpected character '!' at position {i}")

        # If we hit something we don't recognize, fail loudly rather than silently skip it
        raise ValueError(f"Unexpected character {char!r} at position {i}")

    tokens.append(Token(TokenType.EOF, None))
    return tokens


if __name__ == "__main__":
    sample = "price_6mo_ago = price_n_days_ago(close, 126)"
    for token in tokenize(sample):
        print(token)