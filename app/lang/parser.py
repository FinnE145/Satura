from .tokens import Token, TokenType
from .nodes import (
    Program, Assign, ExprStmt, If, For, While, Halt, Break, Return, FuncDef,
    BinOp, UnaryOp, VarRef, IntLit, FloatLit, Constant, Call,
    Min, Max, RangeExpr, Push, Pop, Index, Length, ListConstructor,
    Move, Paint, GetFriction, HasAgent, MyPaint, OppPaint,
    Expr, Stmt,
)


class ParseError(Exception):
    def __init__(self, message: str, line: int, col: int):
        super().__init__(f"Line {line}, col {col}: {message}")
        self.line = line
        self.col  = col


# Token sets used across multiple methods.

_CONSTANT_TYPES = frozenset({
    TokenType.UP, TokenType.DOWN, TokenType.LEFT, TokenType.RIGHT, TokenType.HERE,
    TokenType.NULL,
})

_COMPARISON_OPS = frozenset({
    TokenType.EQ, TokenType.NEQ, TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE,
})

_ADDITIVE_OPS = frozenset({TokenType.PLUS, TokenType.MINUS})

_MULT_OPS = frozenset({TokenType.STAR, TokenType.SLASH, TokenType.PERCENT})

# All token types that can legally begin an expression.
# Used by _parse_return to decide whether a bare `return` has a value.
_EXPR_START = frozenset({
    TokenType.INT_LIT, TokenType.FLOAT_LIT,
    TokenType.DOLLAR,
    TokenType.UP, TokenType.DOWN, TokenType.LEFT, TokenType.RIGHT, TokenType.HERE,
    TokenType.NULL,
    TokenType.LPAREN,
    TokenType.MINUS,
    TokenType.NOT,
    TokenType.LIST,
    TokenType.MIN, TokenType.MAX,
    TokenType.PUSH, TokenType.POP, TokenType.INDEX, TokenType.LENGTH,
    TokenType.MOVE, TokenType.PAINT, TokenType.GET_FRICTION,
    TokenType.HAS_AGENT, TokenType.MY_PAINT, TokenType.OPP_PAINT,
    TokenType.CALL,
})


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos    = 0

    # ------------------------------------------------------------------ public

    def parse(self) -> Program:
        stmts = []
        while not self._at_end():
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return Program(stmts)

    # --------------------------------------------------------------- navigation

    def _at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self, offset: int = 0) -> Token:
        """Return the token at pos+offset without consuming it."""
        p = self.pos + offset
        return self.tokens[p] if p < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        """Consume and return the current token."""
        tok = self.tokens[self.pos]
        if not self._at_end():
            self.pos += 1
        return tok

    def _check(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _match(self, *types: TokenType) -> bool:
        """Consume the current token if it matches any of types. Returns whether it matched."""
        if self._check(*types):
            self._advance()
            return True
        return False

    def _expect(self, type: TokenType, msg: str) -> Token:
        """Consume and return the current token if it matches type, else raise ParseError."""
        if self._check(type):
            return self._advance()
        tok = self._peek()
        raise ParseError(f"{msg} (got {tok.type.name} {tok.value!r})", tok.line, tok.col)

    # --------------------------------------------------------- statement parsing

    def _parse_statement(self) -> Stmt | None:
        # Skip bare semicolons (optional statement terminators)
        while self._check(TokenType.SEMICOLON):
            self._advance()
        if self._at_end():
            return None

        if self._check(TokenType.DEF):
            return self._parse_funcdef()
        if self._check(TokenType.IF):
            return self._parse_if()
        if self._check(TokenType.FOR):
            return self._parse_for()
        if self._check(TokenType.WHILE):
            return self._parse_while()
        if self._check(TokenType.HALT):
            tok = self._expect(TokenType.HALT, "expected 'halt'")
            self._match(TokenType.SEMICOLON)
            return Halt(line=tok.line, col=tok.col)
        if self._check(TokenType.BREAK):
            tok = self._expect(TokenType.BREAK, "expected 'break'")
            self._match(TokenType.SEMICOLON)
            return Break(line=tok.line, col=tok.col)
        if self._check(TokenType.RETURN):
            return self._parse_return()

        # Assignment requires exactly: $ IDENT =
        # Two-token lookahead to distinguish from an expression starting with $var
        if (self._check(TokenType.DOLLAR)
                and self._peek(1).type == TokenType.IDENT
                and self._peek(2).type == TokenType.ASSIGN):
            return self._parse_assign()

        # Everything else is a standalone expression (board ops, calls, etc.)
        tok = self._peek()
        expr = self._parse_expr()
        self._match(TokenType.SEMICOLON)
        return ExprStmt(expr, line=tok.line, col=tok.col)

    def _parse_block(self) -> list[Stmt]:
        self._expect(TokenType.LBRACE, "expected '{'")
        stmts = []
        while not self._check(TokenType.RBRACE) and not self._at_end():
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        self._expect(TokenType.RBRACE, "expected '}'")
        return stmts

    def _parse_assign(self) -> Assign:
        tok = self._expect(TokenType.DOLLAR, "expected '$'")
        name = self._expect(TokenType.IDENT, "expected variable name").value
        self._expect(TokenType.ASSIGN, "expected '='")
        value = self._parse_expr()
        self._match(TokenType.SEMICOLON)
        return Assign(name, value, line=tok.line, col=tok.col)

    def _parse_if(self) -> If:
        tok = self._expect(TokenType.IF, "expected 'if'")
        cond = self._parse_expr()
        body = self._parse_block()
        branches = [(cond, body)]

        while self._check(TokenType.ELIF):
            self._advance()
            cond = self._parse_expr()
            body = self._parse_block()
            branches.append((cond, body))

        else_body = None
        if self._match(TokenType.ELSE):
            else_body = self._parse_block()

        return If(branches, else_body, line=tok.line, col=tok.col)

    def _parse_for(self) -> For:
        tok = self._expect(TokenType.FOR, "expected 'for'")
        self._expect(TokenType.DOLLAR, "expected '$' before loop variable")
        var = self._expect(TokenType.IDENT, "expected loop variable name").value
        self._expect(TokenType.IN, "expected 'in'")
        iterable = self._parse_range_or_expr()
        body = self._parse_block()
        return For(var, iterable, body, line=tok.line, col=tok.col)

    def _parse_range_or_expr(self) -> Expr:
        """Parse either a range(...) expression (for-loop only) or a regular expression."""
        if not self._check(TokenType.RANGE):
            return self._parse_expr()
        tok = self._expect(TokenType.RANGE, "expected 'range'")
        self._expect(TokenType.LPAREN, "expected '(' after 'range'")
        first = self._parse_expr()
        if not self._match(TokenType.COMMA):
            # range(stop)
            self._expect(TokenType.RPAREN, "expected ')'")
            return RangeExpr(start=None, stop=first, step=None, line=tok.line, col=tok.col)
        second = self._parse_expr()
        if not self._match(TokenType.COMMA):
            # range(start, stop)
            self._expect(TokenType.RPAREN, "expected ')'")
            return RangeExpr(start=first, stop=second, step=None, line=tok.line, col=tok.col)
        # range(start, stop, step)
        third = self._parse_expr()
        self._expect(TokenType.RPAREN, "expected ')'")
        return RangeExpr(start=first, stop=second, step=third, line=tok.line, col=tok.col)

    def _parse_while(self) -> While:
        tok = self._expect(TokenType.WHILE, "expected 'while'")
        cond = self._parse_expr()
        body = self._parse_block()
        return While(cond, body, line=tok.line, col=tok.col)

    def _parse_return(self) -> Return:
        tok = self._expect(TokenType.RETURN, "expected 'return'")
        if self._check(*_EXPR_START):
            value = self._parse_expr()
        else:
            value = None
        self._match(TokenType.SEMICOLON)
        return Return(value=value, line=tok.line, col=tok.col)

    def _parse_funcdef(self) -> FuncDef:
        tok = self._expect(TokenType.DEF, "expected 'def'")
        name = self._expect(TokenType.IDENT, "expected function name").value
        self._expect(TokenType.LPAREN, "expected '('")
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._expect(TokenType.IDENT, "expected parameter name").value)
            while self._match(TokenType.COMMA):
                params.append(self._expect(TokenType.IDENT, "expected parameter name").value)
        self._expect(TokenType.RPAREN, "expected ')'")
        body = self._parse_block()
        return FuncDef(name, params, body, line=tok.line, col=tok.col)

    # --------------------------------------------------------- expression parsing
    # Precedence (low → high):
    #   or → and → not → comparison → additive → multiplicative → unary → primary

    def _parse_expr(self) -> Expr:
        return self._parse_or()

    def _parse_or(self) -> Expr:
        left = self._parse_and()
        while self._check(TokenType.OR):
            op = self._advance()
            right = self._parse_and()
            left = BinOp(op.type, left, right, line=op.line, col=op.col)
        return left

    def _parse_and(self) -> Expr:
        left = self._parse_not()
        while self._check(TokenType.AND):
            op = self._advance()
            right = self._parse_not()
            left = BinOp(op.type, left, right, line=op.line, col=op.col)
        return left

    def _parse_not(self) -> Expr:
        if self._check(TokenType.NOT):
            op = self._advance()
            return UnaryOp(op.type, self._parse_not(), line=op.line, col=op.col)
        return self._parse_comparison()

    def _parse_comparison(self) -> Expr:
        left = self._parse_additive()
        while self._check(*_COMPARISON_OPS):
            op = self._advance()
            right = self._parse_additive()
            left = BinOp(op.type, left, right, line=op.line, col=op.col)
        return left

    def _parse_additive(self) -> Expr:
        left = self._parse_multiplicative()
        while self._check(*_ADDITIVE_OPS):
            op = self._advance()
            right = self._parse_multiplicative()
            left = BinOp(op.type, left, right, line=op.line, col=op.col)
        return left

    def _parse_multiplicative(self) -> Expr:
        left = self._parse_unary()
        while self._check(*_MULT_OPS):
            op = self._advance()
            right = self._parse_unary()
            left = BinOp(op.type, left, right, line=op.line, col=op.col)
        return left

    def _parse_unary(self) -> Expr:
        if self._check(TokenType.MINUS):
            op = self._advance()
            return UnaryOp(op.type, self._parse_unary(), line=op.line, col=op.col)
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        tok = self._peek()  # saved here; used as position for all nodes in this method

        # Grouped expression
        if self._match(TokenType.LPAREN):
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return expr

        # Integer and float literals
        if self._check(TokenType.INT_LIT):
            return IntLit(int(self._advance().value), line=tok.line, col=tok.col)
        if self._check(TokenType.FLOAT_LIT):
            return FloatLit(float(self._advance().value), line=tok.line, col=tok.col)

        # Direction / location constants
        if self._check(*_CONSTANT_TYPES):
            return Constant(self._advance().value, line=tok.line, col=tok.col)

        # Variable reference: $ IDENT
        if self._check(TokenType.DOLLAR):
            self._advance()
            name = self._expect(TokenType.IDENT, "expected variable name after '$'").value
            return VarRef(name, line=tok.line, col=tok.col)

        # list()
        if self._check(TokenType.LIST):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '(' after 'list'")
            self._expect(TokenType.RPAREN, "expected ')'")
            return ListConstructor(line=tok.line, col=tok.col)

        # min(a, b) / max(a, b)
        if self._check(TokenType.MIN, TokenType.MAX):
            is_min = self._advance().type == TokenType.MIN
            self._expect(TokenType.LPAREN, "expected '('")
            left = self._parse_expr()
            self._expect(TokenType.COMMA, "expected ','")
            right = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return Min(left, right, line=tok.line, col=tok.col) if is_min else Max(left, right, line=tok.line, col=tok.col)

        # push(list, value [, pos])
        if self._check(TokenType.PUSH):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            lst = self._parse_expr()
            self._expect(TokenType.COMMA, "expected ','")
            value = self._parse_expr()
            pos = self._parse_expr() if self._match(TokenType.COMMA) else None
            self._expect(TokenType.RPAREN, "expected ')'")
            return Push(lst, value, pos, line=tok.line, col=tok.col)

        # pop(list [, pos])
        if self._check(TokenType.POP):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            lst = self._parse_expr()
            pos = self._parse_expr() if self._match(TokenType.COMMA) else None
            self._expect(TokenType.RPAREN, "expected ')'")
            return Pop(lst, pos, line=tok.line, col=tok.col)

        # index(list [, pos])
        if self._check(TokenType.INDEX):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            lst = self._parse_expr()
            pos = self._parse_expr() if self._match(TokenType.COMMA) else None
            self._expect(TokenType.RPAREN, "expected ')'")
            return Index(lst, pos, line=tok.line, col=tok.col)

        # length(list)
        if self._check(TokenType.LENGTH):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            lst = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return Length(lst, line=tok.line, col=tok.col)

        # Board operations — each takes exactly one argument
        if self._check(TokenType.MOVE):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            arg = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return Move(arg, line=tok.line, col=tok.col)

        if self._check(TokenType.PAINT):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            arg = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return Paint(arg, line=tok.line, col=tok.col)

        if self._check(TokenType.GET_FRICTION):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            arg = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return GetFriction(arg, line=tok.line, col=tok.col)

        if self._check(TokenType.HAS_AGENT):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            arg = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return HasAgent(arg, line=tok.line, col=tok.col)

        if self._check(TokenType.MY_PAINT):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            arg = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return MyPaint(arg, line=tok.line, col=tok.col)

        if self._check(TokenType.OPP_PAINT):
            self._advance()
            self._expect(TokenType.LPAREN, "expected '('")
            arg = self._parse_expr()
            self._expect(TokenType.RPAREN, "expected ')'")
            return OppPaint(arg, line=tok.line, col=tok.col)

        # call function_name([args...])
        if self._check(TokenType.CALL):
            self._advance()
            name = self._expect(TokenType.IDENT, "expected function name after 'call'").value
            self._expect(TokenType.LPAREN, "expected '('")
            args = []
            if not self._check(TokenType.RPAREN):
                args.append(self._parse_expr())
                while self._match(TokenType.COMMA):
                    args.append(self._parse_expr())
            self._expect(TokenType.RPAREN, "expected ')'")
            return Call(name, args, line=tok.line, col=tok.col)

        # range() outside a for loop
        if self._check(TokenType.RANGE):
            raise ParseError(
                "'range' can only be used in a for loop (e.g. 'for $i in range(5)')",
                tok.line, tok.col,
            )

        raise ParseError(
            f"unexpected token {tok.type.name} {tok.value!r}", tok.line, tok.col
        )


def parse(tokens: list[Token]) -> Program:
    """Parse a token list (from the lexer) and return the AST root."""
    return Parser(tokens).parse()
