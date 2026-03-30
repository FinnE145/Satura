from .tokens import Token, TokenType, KEYWORDS


class LexError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"Line {line}, col {col}: {message}")
        self.line = line
        self.col  = col


# Operator lookup tables — defined at module level so they're built once.

_TWO_CHAR_OPS: dict[str, TokenType] = {
    "==": TokenType.EQ,
    "!=": TokenType.NEQ,
    "<=": TokenType.LTE,
    ">=": TokenType.GTE,
}

_ONE_CHAR_OPS: dict[str, TokenType] = {
    "=": TokenType.ASSIGN,
    "+": TokenType.PLUS,
    "-": TokenType.MINUS,
    "*": TokenType.STAR,
    "/": TokenType.SLASH,
    "%": TokenType.PERCENT,
    "<": TokenType.LT,
    ">": TokenType.GT,
    "(": TokenType.LPAREN,
    ")": TokenType.RPAREN,
    "{": TokenType.LBRACE,
    "}": TokenType.RBRACE,
    ",": TokenType.COMMA,
    ";": TokenType.SEMICOLON,
}


class Lexer:
    def __init__(self, source: str):
        self.source = source
        self.pos    = 0
        self.line   = 1
        self.col    = 1

    # ------------------------------------------------------------------ public

    def tokenize(self) -> list[Token]:
        tokens = []
        while not self._at_end():
            self._skip()
            if self._at_end():
                break
            tokens.append(self._next())
        tokens.append(Token(TokenType.EOF, "", self.line, self.col))
        return tokens

    # --------------------------------------------------------------- navigation

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        """Return the character at pos+offset without consuming it. Returns "" at end."""
        p = self.pos + offset
        return self.source[p] if p < len(self.source) else ""

    def _advance(self) -> str:
        """Consume and return the current character, updating line/col."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip(self) -> None:
        """Consume whitespace and // line comments."""
        while not self._at_end():
            if self._peek() in " \t\r\n":
                self._advance()
            elif self._peek() == "/" and self._peek(1) == "/":
                while not self._at_end() and self._peek() != "\n":
                    self._advance()
            else:
                break

    # ------------------------------------------------------------ token readers

    def _next(self) -> Token:
        """Dispatch to the appropriate reader based on the current character."""
        line, col = self.line, self.col
        ch = self._peek()

        if ch == "$":
            self._advance()
            return Token(TokenType.DOLLAR, "$", line, col)

        if ch.isdigit() or (ch == "." and self._peek(1).isdigit()):
            return self._read_number(line, col)

        if ch.isalpha() or ch == "_":
            return self._read_identifier(line, col)

        return self._read_symbol(line, col)

    def _read_number(self, line: int, col: int) -> Token:
        """Read an integer or float literal. Handles all four forms: 1.5  3.0  .5  42."""
        start = self.pos
        while not self._at_end() and self._peek().isdigit():
            self._advance()
        has_dot = not self._at_end() and self._peek() == "."
        if has_dot:
            self._advance()  # consume the dot
            while not self._at_end() and self._peek().isdigit():
                self._advance()
        value = self.source[start:self.pos]
        return Token(TokenType.FLOAT_LIT if has_dot else TokenType.INT_LIT, value, line, col)

    def _read_identifier(self, line: int, col: int) -> Token:
        """Read an identifier, then check if it's a reserved word or constant."""
        start = self.pos
        while not self._at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        value = self.source[start:self.pos]
        return Token(KEYWORDS.get(value, TokenType.IDENT), value, line, col)

    def _read_symbol(self, line: int, col: int) -> Token:
        """Read a one- or two-character operator or punctuation token."""
        ch = self._advance()
        two = ch + self._peek()
        if two in _TWO_CHAR_OPS:
            self._advance()
            return Token(_TWO_CHAR_OPS[two], two, line, col)
        if ch in _ONE_CHAR_OPS:
            return Token(_ONE_CHAR_OPS[ch], ch, line, col)
        raise LexError(f"unexpected character {ch!r}", line, col)


def tokenize(source: str) -> list[Token]:
    """Lex source text and return the complete token list (including EOF)."""
    return Lexer(source).tokenize()
