import pytest
from app.lang.lexer import tokenize
from app.lang.parser import parse, ParseError
from app.lang.nodes import (
    Program, Assign, ExprStmt, If, For, While, Halt, Break, Return, FuncDef,
    BinOp, UnaryOp, VarRef, IntLit, FloatLit, Constant, Call,
    Min, Max, RangeExpr, Push, Pop, Index, Length, ListConstructor,
    Move, Paint, GetFriction, HasAgent, MyPaint, OppPaint,
)
from app.lang.tokens import TokenType


# ------------------------------------------------------------------ helpers

def ast(src):
    """Lex and parse src, return the statement list."""
    return parse(tokenize(src)).stmts


def stmt(src):
    """Parse src, assert exactly one statement, return it."""
    stmts = ast(src)
    assert len(stmts) == 1, f"expected 1 statement, got {len(stmts)}"
    return stmts[0]


def expr(src):
    """Parse src as a single expression statement, return the inner expression."""
    node = stmt(src)
    assert isinstance(node, ExprStmt), f"expected ExprStmt, got {type(node).__name__}"
    return node.expr


# ---------------------------------------------------------------- assignments

class TestAssignment:
    def test_int_literal(self):
        node = stmt("$x = 5")
        assert isinstance(node, Assign)
        assert node.name == "x"
        assert isinstance(node.value, IntLit)
        assert node.value.value == 5

    def test_float_literal(self):
        node = stmt("$x = 3.14")
        assert isinstance(node.value, FloatLit)
        assert node.value.value == 3.14

    def test_constant(self):
        node = stmt("$dir = UP")
        assert isinstance(node.value, Constant)
        assert node.value.value == "UP"

    def test_var_ref(self):
        node = stmt("$y = $x")
        assert isinstance(node.value, VarRef)
        assert node.value.name == "x"

    def test_position(self):
        node = stmt("$x = 5")
        assert node.line == 1
        assert node.col == 1

    def test_with_semicolon(self):
        node = stmt("$x = 5;")
        assert isinstance(node, Assign)


# --------------------------------------------------------------- expressions

class TestExpressions:
    def test_binop_add(self):
        node = expr("$x + 1")
        assert isinstance(node, BinOp)
        assert node.op == TokenType.PLUS
        assert isinstance(node.left, VarRef) and node.left.name == "x"
        assert isinstance(node.right, IntLit) and node.right.value == 1

    def test_binop_subtraction(self):
        node = expr("$x - 1")
        assert node.op == TokenType.MINUS

    def test_mul_before_add(self):
        # $a + $b * $c → Add(a, Mul(b, c))
        node = expr("$a + $b * $c")
        assert node.op == TokenType.PLUS
        assert isinstance(node.right, BinOp)
        assert node.right.op == TokenType.STAR

    def test_parens_override_precedence(self):
        # ($a + $b) * $c → Mul(Add(a, b), c)
        node = expr("($a + $b) * $c")
        assert node.op == TokenType.STAR
        assert isinstance(node.left, BinOp)
        assert node.left.op == TokenType.PLUS

    def test_unary_minus(self):
        node = expr("-$x")
        assert isinstance(node, UnaryOp)
        assert node.op == TokenType.MINUS
        assert isinstance(node.operand, VarRef)

    def test_unary_not(self):
        node = expr("not $x")
        assert isinstance(node, UnaryOp)
        assert node.op == TokenType.NOT

    def test_comparison_gt(self):
        node = expr("$x > 3")
        assert isinstance(node, BinOp)
        assert node.op == TokenType.GT

    def test_comparison_eq(self):
        node = expr("$x == $y")
        assert node.op == TokenType.EQ

    def test_logical_and(self):
        node = expr("$x > 0 and $y > 0")
        assert isinstance(node, BinOp)
        assert node.op == TokenType.AND

    def test_logical_or(self):
        node = expr("$x > 0 or $y > 0")
        assert node.op == TokenType.OR

    def test_and_before_or(self):
        # a and b or c and d → Or(And(a,b), And(c,d))
        node = expr("$a and $b or $c and $d")
        assert node.op == TokenType.OR
        assert isinstance(node.left, BinOp) and node.left.op == TokenType.AND
        assert isinstance(node.right, BinOp) and node.right.op == TokenType.AND

    def test_not_before_and(self):
        # not $a and $b → And(Not(a), b)
        node = expr("not $a and $b")
        assert node.op == TokenType.AND
        assert isinstance(node.left, UnaryOp) and node.left.op == TokenType.NOT

    def test_min(self):
        node = expr("min($x, 3)")
        assert isinstance(node, Min)
        assert isinstance(node.left, VarRef)
        assert isinstance(node.right, IntLit)

    def test_max(self):
        node = expr("max($a, $b)")
        assert isinstance(node, Max)
        assert isinstance(node.left, VarRef)
        assert isinstance(node.right, VarRef)

    def test_division_produces_binop(self):
        node = expr("$x / $y")
        assert node.op == TokenType.SLASH

    def test_modulo(self):
        node = expr("$x % 2")
        assert node.op == TokenType.PERCENT

    def test_nested_unary(self):
        node = expr("not not $x")
        assert isinstance(node, UnaryOp) and node.op == TokenType.NOT
        assert isinstance(node.operand, UnaryOp) and node.operand.op == TokenType.NOT

    def test_binop_position(self):
        node = expr("$x + 1")
        assert node.line == 1
        assert node.col == 4   # the + is at col 4


# ------------------------------------------------------------ control flow

class TestIf:
    def test_simple_if(self):
        node = stmt("if $x > 0 { move(UP) }")
        assert isinstance(node, If)
        assert len(node.branches) == 1
        assert node.else_body is None

    def test_if_elif(self):
        node = stmt("if $x > 0 { move(UP) } elif $x < 0 { move(DOWN) }")
        assert len(node.branches) == 2
        assert node.else_body is None

    def test_if_else(self):
        node = stmt("if $x > 0 { move(UP) } else { halt }")
        assert len(node.branches) == 1
        assert node.else_body is not None
        assert isinstance(node.else_body[0], Halt)

    def test_if_elif_else(self):
        src = "if $x > 0 { move(UP) } elif $x < 0 { move(DOWN) } else { halt }"
        node = stmt(src)
        assert len(node.branches) == 2
        assert node.else_body is not None

    def test_multiple_elif(self):
        src = "if $x == 1 { } elif $x == 2 { } elif $x == 3 { } else { }"
        node = stmt(src)
        assert len(node.branches) == 3

    def test_if_position(self):
        node = stmt("if $x > 0 { halt }")
        assert node.line == 1 and node.col == 1


class TestWhile:
    def test_basic(self):
        node = stmt("while $x > 0 { $x = $x - 1 }")
        assert isinstance(node, While)
        assert isinstance(node.cond, BinOp)
        assert len(node.body) == 1

    def test_empty_body(self):
        node = stmt("while $x > 0 { }")
        assert isinstance(node, While)
        assert node.body == []


class TestHalt:
    def test_halt(self):
        assert isinstance(stmt("halt"), Halt)

    def test_halt_semicolon(self):
        assert isinstance(stmt("halt;"), Halt)

    def test_halt_position(self):
        node = stmt("halt")
        assert node.line == 1 and node.col == 1


class TestBreak:
    def test_break(self):
        assert isinstance(stmt("break"), Break)

    def test_break_semicolon(self):
        assert isinstance(stmt("break;"), Break)

    def test_break_position(self):
        node = stmt("break")
        assert node.line == 1 and node.col == 1

    def test_break_inside_loop(self):
        node = stmt("for $i in range(5) { break }")
        assert isinstance(node, For)
        assert isinstance(node.body[0], Break)


# --------------------------------------------------------------- for loops

class TestForLoop:
    def test_for_list(self):
        node = stmt("for $dir in $directions { move($dir) }")
        assert isinstance(node, For)
        assert node.var == "dir"
        assert isinstance(node.iterable, VarRef)
        assert node.iterable.name == "directions"

    def test_for_range_stop_only(self):
        node = stmt("for $i in range(5) { paint(1) }")
        r = node.iterable
        assert isinstance(r, RangeExpr)
        assert r.start is None
        assert isinstance(r.stop, IntLit) and r.stop.value == 5
        assert r.step is None

    def test_for_range_start_stop(self):
        node = stmt("for $i in range(0, 10) { paint(1) }")
        r = node.iterable
        assert isinstance(r.start, IntLit) and r.start.value == 0
        assert isinstance(r.stop, IntLit) and r.stop.value == 10
        assert r.step is None

    def test_for_range_start_stop_step(self):
        node = stmt("for $i in range(0, 10, 2) { paint(1) }")
        r = node.iterable
        assert isinstance(r.step, IntLit) and r.step.value == 2

    def test_for_loop_variable_name(self):
        node = stmt("for $item in $mylist { halt }")
        assert node.var == "item"

    def test_anonymous_range_stop_only(self):
        node = stmt("for range(5) { paint(1) }")
        assert isinstance(node, For)
        assert node.var is None
        r = node.iterable
        assert isinstance(r, RangeExpr)
        assert r.start is None
        assert isinstance(r.stop, IntLit) and r.stop.value == 5
        assert r.step is None

    def test_anonymous_range_start_stop(self):
        node = stmt("for range(0, 10) { paint(1) }")
        assert node.var is None
        r = node.iterable
        assert isinstance(r.start, IntLit) and r.start.value == 0
        assert isinstance(r.stop, IntLit) and r.stop.value == 10
        assert r.step is None

    def test_anonymous_range_start_stop_step(self):
        node = stmt("for range(0, 10, 2) { paint(1) }")
        assert node.var is None
        assert isinstance(node.iterable.step, IntLit) and node.iterable.step.value == 2

    def test_named_loop_var_unaffected_by_anonymous_form(self):
        # Regression: $var in ... form still sets var correctly
        node = stmt("for $i in range(5) { }")
        assert node.var == "i"


# ---------------------------------------------------------------- functions

class TestFuncDef:
    def test_no_params(self):
        node = stmt("def foo() { halt }")
        assert isinstance(node, FuncDef)
        assert node.name == "foo"
        assert node.params == []

    def test_one_param(self):
        node = stmt("def go(d) { move($d) }")
        assert node.params == ["d"]

    def test_multiple_params(self):
        node = stmt("def calc(a, b, c) { }")
        assert node.params == ["a", "b", "c"]

    def test_funcdef_position(self):
        node = stmt("def foo() { }")
        assert node.line == 1 and node.col == 1


class TestReturn:
    def test_return_with_value(self):
        node = stmt("def f() { return $x }")
        ret = node.body[0]
        assert isinstance(ret, Return)
        assert isinstance(ret.value, VarRef)

    def test_return_bare(self):
        node = stmt("def f() { return }")
        assert node.body[0].value is None

    def test_return_with_expression(self):
        node = stmt("def f() { return $x + 1 }")
        ret = node.body[0]
        assert isinstance(ret.value, BinOp)


class TestCall:
    def test_no_args(self):
        node = expr("call foo()")
        assert isinstance(node, Call)
        assert node.name == "foo"
        assert node.args == []

    def test_constant_arg(self):
        node = expr("call go(UP)")
        assert isinstance(node.args[0], Constant)
        assert node.args[0].value == "UP"

    def test_var_arg(self):
        node = expr("call go($dir)")
        assert isinstance(node.args[0], VarRef)

    def test_multiple_args(self):
        node = expr("call calc($a, $b, 3)")
        assert len(node.args) == 3

    def test_call_as_assignment_value(self):
        node = stmt("$result = call compute($x)")
        assert isinstance(node, Assign)
        assert isinstance(node.value, Call)

    def test_call_as_subexpression(self):
        node = expr("call get_val() + 1")
        assert isinstance(node, BinOp)
        assert isinstance(node.left, Call)


# ---------------------------------------------------------------- list ops

class TestListOps:
    def test_list_constructor(self):
        assert isinstance(expr("list()"), ListConstructor)

    def test_push_no_pos(self):
        node = expr("push($lst, $x)")
        assert isinstance(node, Push)
        assert node.pos is None

    def test_push_with_pos(self):
        node = expr("push($lst, $x, 0)")
        assert isinstance(node.pos, IntLit)

    def test_pop_no_pos(self):
        node = expr("pop($lst)")
        assert isinstance(node, Pop)
        assert node.pos is None

    def test_pop_with_pos(self):
        node = expr("pop($lst, 0)")
        assert isinstance(node.pos, IntLit)

    def test_index_no_pos(self):
        node = expr("index($lst)")
        assert isinstance(node, Index)
        assert node.pos is None

    def test_index_with_pos(self):
        node = expr("index($lst, $i)")
        assert isinstance(node.pos, VarRef)

    def test_length(self):
        node = expr("length($lst)")
        assert isinstance(node, Length)
        assert isinstance(node.lst, VarRef)


# -------------------------------------------------------------- board ops

class TestBoardOps:
    def test_move_constant(self):
        node = expr("move(UP)")
        assert isinstance(node, Move)
        assert isinstance(node.dir, Constant) and node.dir.value == "UP"

    def test_move_var(self):
        node = expr("move($dir)")
        assert isinstance(node, Move)
        assert isinstance(node.dir, VarRef)

    def test_paint_literal(self):
        node = expr("paint(3)")
        assert isinstance(node, Paint)
        assert isinstance(node.num, IntLit) and node.num.value == 3

    def test_get_friction_here(self):
        node = expr("get_friction(HERE)")
        assert isinstance(node, GetFriction)
        assert isinstance(node.loc, Constant) and node.loc.value == "HERE"

    def test_has_agent(self):
        node = expr("has_agent(UP)")
        assert isinstance(node, HasAgent)
        assert isinstance(node.dir, Constant)

    def test_my_paint(self):
        node = expr("my_paint(HERE)")
        assert isinstance(node, MyPaint)

    def test_opp_paint(self):
        node = expr("opp_paint(HERE)")
        assert isinstance(node, OppPaint)

    def test_board_op_position(self):
        node = expr("move(UP)")
        assert node.line == 1 and node.col == 1


# -------------------------------------------------------------- parse errors

class TestParseErrors:
    def test_range_outside_for(self):
        with pytest.raises(ParseError) as exc:
            parse(tokenize("$x = range(5)"))
        msg = str(exc.value).lower()
        assert "range" in msg and "for" in msg

    def test_range_in_expression(self):
        with pytest.raises(ParseError):
            parse(tokenize("if range(5) > 0 { halt }"))

    def test_missing_closing_brace(self):
        with pytest.raises(ParseError):
            parse(tokenize("if $x > 0 { move(UP)"))

    def test_missing_rparen(self):
        with pytest.raises(ParseError):
            parse(tokenize("move(UP"))

    def test_unexpected_closing_brace(self):
        with pytest.raises(ParseError):
            parse(tokenize("}"))

    def test_missing_dollar_in_for(self):
        with pytest.raises(ParseError):
            parse(tokenize("for x in $directions { }"))

    def test_error_has_position(self):
        with pytest.raises(ParseError) as exc:
            parse(tokenize("move(UP"))
        assert exc.value.line >= 1


# --------------------------------------------------------- multi-statement

class TestMultiStatement:
    def test_multiple_statements(self):
        stmts = ast("$x = 5\n$y = $x + 1\nmove(UP)")
        assert len(stmts) == 3
        assert isinstance(stmts[0], Assign)
        assert isinstance(stmts[1], Assign)
        assert isinstance(stmts[2], ExprStmt)

    def test_semicolons_as_separators(self):
        stmts = ast("move(UP); paint(1); move(DOWN)")
        assert len(stmts) == 3

    def test_bare_semicolons_skipped(self):
        stmts = ast(";;;$x = 5;;;")
        assert len(stmts) == 1

    def test_full_script(self):
        src = """
        def go(d) {
            if not has_agent($d) { move($d) }
        }
        for $dir in $directions {
            call go($dir)
        }
        """
        stmts = ast(src)
        assert len(stmts) == 2
        assert isinstance(stmts[0], FuncDef)
        assert isinstance(stmts[1], For)
