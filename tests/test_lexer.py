import pytest
from app.lang.lexer import tokenize, LexError
from app.lang.tokens import TokenType, WORD_COSTS


# ------------------------------------------------------------------ helpers

def types(src):
    """Lex src and return token types, excluding EOF."""
    return [t.type for t in tokenize(src) if t.type != TokenType.EOF]


def pairs(src):
    """Lex src and return (type, value) pairs, excluding EOF."""
    return [(t.type, t.value) for t in tokenize(src) if t.type != TokenType.EOF]


def word_count(src):
    """Sum word costs across all tokens in src."""
    return sum(WORD_COSTS.get(t.type, 0) for t in tokenize(src))


# ------------------------------------------------------------------ keywords

class TestKeywords:
    def test_control_flow(self):
        assert types("if elif else for while") == [
            TokenType.IF, TokenType.ELIF, TokenType.ELSE, TokenType.FOR, TokenType.WHILE,
        ]

    def test_flow_keywords(self):
        assert types("halt break return def call") == [
            TokenType.HALT, TokenType.BREAK, TokenType.RETURN, TokenType.DEF, TokenType.CALL,
        ]

    def test_logical(self):
        assert types("and or not") == [TokenType.AND, TokenType.OR, TokenType.NOT]

    def test_list_ops(self):
        assert types("push pop index length range list") == [
            TokenType.PUSH, TokenType.POP, TokenType.INDEX,
            TokenType.LENGTH, TokenType.RANGE, TokenType.LIST,
        ]

    def test_board_ops(self):
        assert types("move paint get_friction has_agent my_paint opp_paint") == [
            TokenType.MOVE, TokenType.PAINT, TokenType.GET_FRICTION,
            TokenType.HAS_AGENT, TokenType.MY_PAINT, TokenType.OPP_PAINT,
        ]

    def test_constants(self):
        assert types("UP DOWN LEFT RIGHT HERE") == [
            TokenType.UP, TokenType.DOWN, TokenType.LEFT, TokenType.RIGHT, TokenType.HERE,
        ]

    def test_min_max(self):
        assert types("min max") == [TokenType.MIN, TokenType.MAX]

    def test_in_is_keyword(self):
        assert types("in") == [TokenType.IN]

    def test_list_is_keyword(self):
        assert types("list") == [TokenType.LIST]

    def test_keyword_prefix_not_keyword(self):
        # "iff" starts with "if" but is a plain identifier
        assert pairs("iff") == [(TokenType.IDENT, "iff")]

    def test_keyword_suffix_not_keyword(self):
        assert pairs("myif") == [(TokenType.IDENT, "myif")]


# ---------------------------------------------------------------- identifiers

class TestIdentifiers:
    def test_plain(self):
        assert pairs("myvar") == [(TokenType.IDENT, "myvar")]

    def test_with_digits(self):
        assert pairs("x1") == [(TokenType.IDENT, "x1")]

    def test_with_underscore(self):
        assert pairs("my_var") == [(TokenType.IDENT, "my_var")]

    def test_leading_underscore(self):
        assert pairs("_x") == [(TokenType.IDENT, "_x")]

    def test_all_caps_non_constant(self):
        # UPROAR is not a keyword — it's an identifier
        assert pairs("UPROAR") == [(TokenType.IDENT, "UPROAR")]


# ------------------------------------------------------------------ literals

class TestLiterals:
    def test_integer(self):
        assert pairs("42") == [(TokenType.INT_LIT, "42")]

    def test_zero(self):
        assert pairs("0") == [(TokenType.INT_LIT, "0")]

    def test_float_standard(self):
        assert pairs("1.5") == [(TokenType.FLOAT_LIT, "1.5")]

    def test_float_trailing_dot(self):
        # 42. is a valid float literal per spec
        assert pairs("42.") == [(TokenType.FLOAT_LIT, "42.")]

    def test_float_leading_dot(self):
        # .5 is a valid float literal per spec
        assert pairs(".5") == [(TokenType.FLOAT_LIT, ".5")]

    def test_float_whole(self):
        assert pairs("3.0") == [(TokenType.FLOAT_LIT, "3.0")]

    def test_bare_dot_is_error(self):
        with pytest.raises(LexError):
            tokenize(".")


# ----------------------------------------------------------------- operators

class TestOperators:
    def test_arithmetic(self):
        assert types("+ - * / %") == [
            TokenType.PLUS, TokenType.MINUS, TokenType.STAR,
            TokenType.SLASH, TokenType.PERCENT,
        ]

    def test_comparison_single(self):
        assert types("< >") == [TokenType.LT, TokenType.GT]

    def test_comparison_double(self):
        assert types("== != <= >=") == [
            TokenType.EQ, TokenType.NEQ, TokenType.LTE, TokenType.GTE,
        ]

    def test_assign_vs_eq(self):
        # = is ASSIGN, == is EQ — must not confuse them
        assert types("= ==") == [TokenType.ASSIGN, TokenType.EQ]

    def test_lt_vs_lte(self):
        assert types("< <=") == [TokenType.LT, TokenType.LTE]

    def test_gt_vs_gte(self):
        assert types("> >=") == [TokenType.GT, TokenType.GTE]

    def test_neq_not_split(self):
        # != must not become NOT + ASSIGN
        assert types("!=") == [TokenType.NEQ]


# -------------------------------------------------------------------- sigil

class TestSigil:
    def test_sigil_produces_two_tokens(self):
        assert types("$x") == [TokenType.DOLLAR, TokenType.IDENT]

    def test_sigil_value_is_dollar(self):
        assert pairs("$x") == [(TokenType.DOLLAR, "$"), (TokenType.IDENT, "x")]

    def test_sigil_builtin(self):
        assert types("$directions") == [TokenType.DOLLAR, TokenType.IDENT]


# --------------------------------------------------------------- punctuation

class TestPunctuation:
    def test_all(self):
        assert types("( ) { } , ;") == [
            TokenType.LPAREN, TokenType.RPAREN,
            TokenType.LBRACE, TokenType.RBRACE,
            TokenType.COMMA, TokenType.SEMICOLON,
        ]


# ----------------------------------------------------------------- comments

class TestComments:
    def test_full_line_comment(self):
        assert types("// this is a comment") == []

    def test_inline_comment(self):
        assert types("$x // comment") == [TokenType.DOLLAR, TokenType.IDENT]

    def test_comment_does_not_consume_next_line(self):
        assert types("// comment\n$x") == [TokenType.DOLLAR, TokenType.IDENT]

    def test_double_slash_only(self):
        # a single / is the division operator, not a comment
        assert types("/") == [TokenType.SLASH]


# --------------------------------------------------------------- whitespace

class TestWhitespace:
    def test_spaces_ignored(self):
        assert types("$x   =   5") == [
            TokenType.DOLLAR, TokenType.IDENT, TokenType.ASSIGN, TokenType.INT_LIT,
        ]

    def test_newlines_ignored(self):
        assert types("$x\n=\n5") == [
            TokenType.DOLLAR, TokenType.IDENT, TokenType.ASSIGN, TokenType.INT_LIT,
        ]

    def test_tabs_ignored(self):
        assert types("$x\t=\t5") == [
            TokenType.DOLLAR, TokenType.IDENT, TokenType.ASSIGN, TokenType.INT_LIT,
        ]


# ------------------------------------------------------------ line/col tracking

class TestLineCol:
    def test_first_token_at_1_1(self):
        tok = tokenize("if")[0]
        assert tok.line == 1 and tok.col == 1

    def test_col_advances(self):
        toks = [t for t in tokenize("if $x") if t.type != TokenType.EOF]
        assert toks[0].col == 1   # if
        assert toks[1].col == 4   # $

    def test_line_increments_on_newline(self):
        toks = [t for t in tokenize("if\n$x") if t.type != TokenType.EOF]
        assert toks[0].line == 1
        assert toks[1].line == 2

    def test_col_resets_after_newline(self):
        toks = [t for t in tokenize("if\n$x") if t.type != TokenType.EOF]
        assert toks[1].col == 1

    def test_eof_position_tracked(self):
        toks = tokenize("$x")
        eof = toks[-1]
        assert eof.type == TokenType.EOF
        assert eof.line >= 1


# --------------------------------------------------------------- error cases

class TestErrors:
    def test_invalid_character(self):
        with pytest.raises(LexError):
            tokenize("@x")

    def test_exclamation_alone(self):
        # ! is only valid as part of !=
        with pytest.raises(LexError):
            tokenize("!")

    def test_error_reports_position(self):
        with pytest.raises(LexError) as exc_info:
            tokenize("$x @y")
        assert exc_info.value.line == 1
        assert exc_info.value.col == 4


# --------------------------------------------------------------- word counts

class TestWordCount:
    def test_dollar_costs_one(self):
        assert word_count("$x") == 1

    def test_assignment_costs_two(self):
        # $x = 5 → $(1) + =(1) = 2
        assert word_count("$x = 5") == 2

    def test_expression_with_two_vars(self):
        # $y = $x + 1 → $(1) + =(1) + $(1) + +(1) = 4
        assert word_count("$y = $x + 1") == 4

    def test_if_costs_one(self):
        assert word_count("if") == 1

    def test_elif_costs_one(self):
        assert word_count("elif") == 1

    def test_else_costs_one(self):
        assert word_count("else") == 1

    def test_break_costs_one(self):
        assert word_count("break") == 1

    def test_constants_are_free(self):
        assert word_count("UP DOWN LEFT RIGHT HERE") == 0

    def test_identifiers_are_free(self):
        assert word_count("myvar") == 0

    def test_integer_literals_are_free(self):
        assert word_count("42") == 0

    def test_float_literals_are_free(self):
        assert word_count("3.14") == 0

    def test_punctuation_is_free(self):
        assert word_count("( ) { } , ;") == 0

    def test_in_is_free(self):
        assert word_count("in") == 0

    def test_list_is_free(self):
        assert word_count("list") == 0

    def test_board_ops_each_cost_one(self):
        for op in ("move", "paint", "get_friction", "has_agent", "my_paint", "opp_paint"):
            assert word_count(op) == 1, f"expected {op} to cost 1 word"

    def test_full_script_count(self):
        # for $dir in $directions { move($dir) }
        # for(1) $(1 for $dir) $(1 for $directions) move(1) $(1 for $dir in body) = 5 words
        assert word_count("for $dir in $directions { move($dir) }") == 5

    def test_safe_move_function_count(self):
        # def safe_move(d) { $cost = get_friction($d)  if $ops_remaining > $cost { move($d) } }
        # def(1) $(1) =(1) get_friction(1) $(1) if(1) $(1) >(1) $(1) move(1) $(1) = 11 words
        src = "def safe_move(d) { $cost = get_friction($d) if $ops_remaining > $cost { move($d) } }"
        assert word_count(src) == 11
