"""
Tests for app/lang/interpreter.py.

Strategy:
  - Compile each snippet with the full lex→parse→check pipeline.
  - Execute against a mock or stub context.
  - Route computed values through paint() calls on the mock to observe them,
    since the interpreter returns None and has no other output channel.
  - Use a plain _Ctx stub when board-op side effects aren't being observed.
"""
import pytest
from unittest.mock import MagicMock, call as mcall

from app.lang.lexer import tokenize
from app.lang.parser import parse
from app.lang.compiler import check
from app.lang.interpreter import execute, HaltSignal, ResetSignal


# ------------------------------------------------------------------ helpers

def _compile(source, funcs=None):
    """Full pipeline → Program; asserts no compile errors."""
    if funcs is None:
        funcs = {}
    tokens = tokenize(source)
    program = parse(tokens)
    errors, _ = check(program, funcs)
    assert not errors, [e.message for e in errors]
    return program


class _Ctx:
    """Stub context for tests that don't need to inspect board calls."""
    def __init__(self, op_limit=1000, ops_remaining=None):
        self.op_limit = op_limit
        self.ops_remaining = op_limit if ops_remaining is None else ops_remaining
    def board_move(self, d): pass
    def board_paint(self, n): pass
    def board_get_friction(self, loc): return 1
    def board_has_agent(self, d): return 0
    def board_my_paint(self, loc): return 0
    def board_opp_paint(self, loc): return 0


def _mock_ctx(op_limit=1000, **attrs):
    ctx = MagicMock()
    ctx.op_limit = op_limit
    ctx.ops_remaining = op_limit
    for k, v in attrs.items():
        setattr(ctx, k, v)
    return ctx


def _run(source, ctx=None, funcs=None):
    """Compile + execute; return ctx."""
    if funcs is None:
        funcs = {}
    if ctx is None:
        ctx = _Ctx()
    execute(_compile(source, funcs), ctx, funcs)
    return ctx


def _raises_halt(source, ctx=None, funcs=None):
    """Assert execution raises HaltSignal."""
    if ctx is None:
        ctx = _Ctx()
    if funcs is None:
        funcs = {}
    with pytest.raises(HaltSignal):
        execute(_compile(source, funcs), ctx, funcs)


# ================================================================== literals / constants

class TestLiterals:
    def test_int_literal(self):
        ctx = _mock_ctx()
        _run("paint(5)", ctx)
        ctx.board_paint.assert_called_once_with(5)

    def test_float_literal_in_arithmetic(self):
        # Floats are valid in arithmetic; comparison result is int → paint ok
        ctx = _mock_ctx()
        _run("$x = 6.0 == 6\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_direction_constant(self):
        ctx = _mock_ctx()
        _run("move(UP)", ctx)
        ctx.board_move.assert_called_once_with("UP")

    def test_location_constant(self):
        ctx = _mock_ctx()
        ctx.board_get_friction.return_value = 3
        _run("$f = get_friction(HERE)\npaint($f)", ctx)
        ctx.board_get_friction.assert_called_once_with("HERE")


# ================================================================== variables

class TestVariables:
    def test_assignment_and_read(self):
        ctx = _mock_ctx()
        _run("$x = 7\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(7)

    def test_reassignment(self):
        ctx = _mock_ctx()
        _run("$x = 3\n$x = 9\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(9)

    def test_uninitialized_raises_halt(self):
        # Compiler allows $x because it's assigned in a branch; at runtime the
        # branch is never taken so $x remains uninitialized → HaltSignal.
        ctx = _Ctx()
        with pytest.raises(HaltSignal):
            _run("if 0 { $x = 5 }\npaint($x)", ctx)

    def test_variable_persists_after_loop(self):
        # For loop leaves loop variable in scope
        ctx = _mock_ctx()
        _run("for $i in range(1, 4) {}\npaint($i)", ctx)
        ctx.board_paint.assert_called_once_with(3)


# ================================================================== built-in variables

class TestBuiltins:
    def test_ops_remaining(self):
        ctx = _mock_ctx(op_limit=200)
        ctx.ops_remaining = 150
        _run("paint($ops_remaining)", ctx)
        ctx.board_paint.assert_called_once_with(150)

    def test_op_limit(self):
        ctx = _mock_ctx(op_limit=500)
        _run("paint($op_limit)", ctx)
        ctx.board_paint.assert_called_once_with(500)

    def test_directions_is_list(self):
        ctx = _mock_ctx()
        _run("$d = $directions\npaint(length($d))", ctx)
        ctx.board_paint.assert_called_once_with(4)

    def test_locations_is_list(self):
        ctx = _mock_ctx()
        _run("$l = $locations\npaint(length($l))", ctx)
        ctx.board_paint.assert_called_once_with(5)

    def test_directions_fresh_copy_each_read(self):
        # Mutating $directions should not affect future reads
        ctx = _mock_ctx()
        _run("$d = $directions\npush($d, 1)\npaint(length($directions))", ctx)
        ctx.board_paint.assert_called_once_with(4)


# ================================================================== arithmetic

class TestArithmetic:
    def test_addition(self):
        ctx = _mock_ctx()
        _run("$x = 3 + 4\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(7)

    def test_subtraction(self):
        ctx = _mock_ctx()
        _run("$x = 10 - 3\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(7)

    def test_multiplication(self):
        ctx = _mock_ctx()
        _run("$x = 3 * 4\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(12)

    def test_division_produces_float(self):
        # 6 / 2 = 3.0 (float); equality comparison with int 3 → 1 (they are equal)
        ctx = _mock_ctx()
        _run("$x = 6 / 2 == 3\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_division_by_zero_raises_halt(self):
        # $z is a variable so the compiler can't catch the zero divisor statically.
        # HaltSignal fires during the division, before any paint call.
        ctx = _Ctx()
        with pytest.raises(HaltSignal):
            _run("$z = 0\n$y = 1 / $z", ctx)

    def test_modulo(self):
        ctx = _mock_ctx()
        _run("$x = 10 % 3\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_modulo_by_zero_raises_halt(self):
        _raises_halt("$x = 5 % 0\npaint($x)")

    def test_unary_minus(self):
        ctx = _mock_ctx()
        _run("$x = -3 + 10\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(7)

    def test_unary_minus_on_non_numeric_raises_halt(self):
        # Build AST directly: -"UP" cannot be typed-checked away at compile time
        # when the value comes from a list element at runtime.
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, Assign, ExprStmt, UnaryOp, Index, VarRef, ListConstructor, IntLit
        from app.lang.tokens import TokenType
        # $d = $directions; -index($d) → unary minus on a direction string → halt
        prog = Program(stmts=[
            Assign(name="d", value=VarRef(name="directions", line=1, col=1), line=1, col=1),
            ExprStmt(expr=UnaryOp(op=TokenType.MINUS, operand=Index(lst=VarRef(name="d", line=2, col=1), pos=None, line=2, col=1), line=2, col=1)),
        ])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_fractional_float_in_paint_raises_halt(self):
        # Build AST directly: paint(3.5) → coerce fails (fractional float)
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Paint, FloatLit
        prog = Program(stmts=[ExprStmt(expr=Paint(num=FloatLit(value=3.5, line=1, col=1), line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})


# ================================================================== comparisons

class TestComparisons:
    def test_eq_true(self):
        ctx = _mock_ctx()
        _run("$x = 3 == 3\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_eq_false(self):
        ctx = _mock_ctx()
        _run("$x = 3 == 4\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(0)

    def test_neq(self):
        ctx = _mock_ctx()
        _run("$x = 3 != 4\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_lt_true(self):
        ctx = _mock_ctx()
        _run("$x = 2 < 5\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_lt_false(self):
        ctx = _mock_ctx()
        _run("$x = 5 < 2\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(0)

    def test_gt(self):
        ctx = _mock_ctx()
        _run("$x = 5 > 2\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_lte_equal(self):
        ctx = _mock_ctx()
        _run("$x = 3 <= 3\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_gte(self):
        ctx = _mock_ctx()
        _run("$x = 5 >= 3\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_ordered_comparison_type_error(self):
        _raises_halt("$x = UP < 1\npaint($x)")

    def test_eq_on_directions(self):
        # == is not restricted to numeric types
        ctx = _mock_ctx()
        _run("$x = UP == UP\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)


# ================================================================== boolean ops

class TestBooleanOps:
    def test_and_true(self):
        ctx = _mock_ctx()
        _run("$x = 1 and 1\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_and_false_left(self):
        ctx = _mock_ctx()
        _run("$x = 0 and 1\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(0)

    def test_and_short_circuits(self):
        # Right side is never evaluated when left is 0
        ctx = _mock_ctx()
        ctx.board_get_friction.return_value = 1
        # If short-circuit works, get_friction is NOT called
        _run("$x = 0 and get_friction(HERE)\npaint($x)", ctx)
        ctx.board_get_friction.assert_not_called()

    def test_or_true_left(self):
        ctx = _mock_ctx()
        _run("$x = 1 or 0\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_or_short_circuits(self):
        ctx = _mock_ctx()
        _run("$x = 1 or get_friction(HERE)\npaint($x)", ctx)
        ctx.board_get_friction.assert_not_called()

    def test_or_false(self):
        ctx = _mock_ctx()
        _run("$x = 0 or 0\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(0)

    def test_not_true_to_false(self):
        ctx = _mock_ctx()
        _run("$x = not 1\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(0)

    def test_not_false_to_true(self):
        ctx = _mock_ctx()
        _run("$x = not 0\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_and_non_bool_raises_halt(self):
        _raises_halt("$x = 2 and 1\npaint($x)")

    def test_or_non_bool_raises_halt(self):
        _raises_halt("$x = 0 or 2\npaint($x)")

    def test_not_non_bool_raises_halt(self):
        _raises_halt("$x = not 2\npaint($x)")


# ================================================================== min / max

class TestMinMax:
    def test_min(self):
        ctx = _mock_ctx()
        _run("$x = min(3, 7)\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(3)

    def test_max(self):
        ctx = _mock_ctx()
        _run("$x = max(3, 7)\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(7)

    def test_min_equal(self):
        ctx = _mock_ctx()
        _run("$x = min(4, 4)\npaint($x)", ctx)
        ctx.board_paint.assert_called_once_with(4)

    def test_min_non_numeric_raises_halt(self):
        # Compiler catches static type errors; trigger at runtime via direct AST
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Min, Constant, IntLit
        prog = Program(stmts=[ExprStmt(expr=Min(left=Constant(value="UP", line=1, col=1), right=IntLit(value=3, line=1, col=1), line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_max_non_numeric_raises_halt(self):
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Max, Constant, IntLit
        prog = Program(stmts=[ExprStmt(expr=Max(left=IntLit(value=3, line=1, col=1), right=Constant(value="DOWN", line=1, col=1), line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})


# ================================================================== if / elif / else

class TestIf:
    def test_if_taken(self):
        ctx = _mock_ctx()
        _run("if 1 { paint(1) }", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_if_not_taken(self):
        ctx = _mock_ctx()
        _run("if 0 { paint(1) }", ctx)
        ctx.board_paint.assert_not_called()

    def test_else_taken(self):
        ctx = _mock_ctx()
        _run("if 0 { paint(1) } else { paint(2) }", ctx)
        ctx.board_paint.assert_called_once_with(2)

    def test_elif_taken(self):
        ctx = _mock_ctx()
        _run("if 0 { paint(1) } elif 1 { paint(2) } else { paint(3) }", ctx)
        ctx.board_paint.assert_called_once_with(2)

    def test_only_first_true_branch_runs(self):
        ctx = _mock_ctx()
        _run("if 1 { paint(1) } elif 1 { paint(2) }", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_condition_non_bool_raises_halt(self):
        _raises_halt("if 2 { paint(1) }")


# ================================================================== for loops

class TestForLoop:
    def test_range_basic(self):
        ctx = _mock_ctx()
        _run("for $i in range(3) { paint($i) }", ctx)
        assert ctx.board_paint.call_count == 3
        ctx.board_paint.assert_any_call(0)
        ctx.board_paint.assert_any_call(1)
        ctx.board_paint.assert_any_call(2)

    def test_range_with_start(self):
        ctx = _mock_ctx()
        _run("for $i in range(2, 5) { paint($i) }", ctx)
        assert ctx.board_paint.call_count == 3

    def test_range_with_step(self):
        ctx = _mock_ctx()
        _run("for $i in range(0, 6, 2) { paint($i) }", ctx)
        assert ctx.board_paint.call_count == 3
        ctx.board_paint.assert_any_call(0)
        ctx.board_paint.assert_any_call(2)
        ctx.board_paint.assert_any_call(4)

    def test_range_zero_step_raises_halt(self):
        _raises_halt("for $i in range(0, 5, 0) { paint($i) }")

    def test_for_over_list(self):
        ctx = _mock_ctx()
        _run("$lst = list()\npush($lst, 3)\npush($lst, 7)\nfor $v in $lst { paint($v) }", ctx)
        assert ctx.board_paint.call_count == 2
        ctx.board_paint.assert_any_call(3)
        ctx.board_paint.assert_any_call(7)

    def test_for_non_list_raises_halt(self):
        # Build AST directly: for $x in <int> → not a list at runtime
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, For, ExprStmt, Paint, VarRef, IntLit
        prog = Program(stmts=[
            For(var="x", iterable=IntLit(value=5, line=1, col=1),
                body=[ExprStmt(expr=Paint(num=VarRef(name="x", line=1, col=1), line=1, col=1))],
                line=1, col=1),
        ])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_for_list_snapshot_mid_mutation(self):
        # Mutating the list mid-loop should not affect the current iteration
        ctx = _mock_ctx()
        _run("$lst = list()\npush($lst, 1)\npush($lst, 2)\nfor $v in $lst { push($lst, 9) }", ctx)
        # Loop should run exactly 2 times (snapshot taken at loop start)
        # Just verify no infinite loop / halt; the list grows but iteration count was fixed


# ================================================================== while loops

class TestWhile:
    def test_while_runs_body(self):
        ctx = _mock_ctx()
        _run("$x = 0\nwhile $x < 3 { paint($x)\n$x = $x + 1 }", ctx)
        assert ctx.board_paint.call_count == 3

    def test_while_not_entered_when_false(self):
        ctx = _mock_ctx()
        _run("while 0 { paint(1) }", ctx)
        ctx.board_paint.assert_not_called()

    def test_while_condition_non_bool_raises_halt(self):
        _raises_halt("while 2 { paint(1) }")


# ================================================================== halt

class TestHalt:
    def test_halt_raises_halt_signal(self):
        with pytest.raises(HaltSignal):
            _run("halt")

    def test_halt_stops_further_statements(self):
        ctx = _mock_ctx()
        with pytest.raises(HaltSignal):
            _run("halt\npaint(1)", ctx)
        ctx.board_paint.assert_not_called()

    def test_halt_after_side_effect_preserves_effect(self):
        # paint before halt still ran (HaltSignal = commit what ran)
        ctx = _mock_ctx()
        with pytest.raises(HaltSignal):
            _run("paint(3)\nhalt", ctx)
        ctx.board_paint.assert_called_once_with(3)


# ================================================================== functions

class TestFunctions:
    def test_call_returns_value(self):
        ctx = _mock_ctx()
        _run("def f() { return 42 }\npaint(call f())", ctx)
        ctx.board_paint.assert_called_once_with(42)

    def test_implicit_return_null(self):
        # A function that runs off the end returns NULL; comparing with NULL is valid.
        ctx = _mock_ctx()
        _run("def f() {}\n$r = call f()\nif $r == NULL { paint(1) }", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_bare_return(self):
        ctx = _mock_ctx()
        _run("def f() { return }\npaint(call f())", ctx)
        ctx.board_paint.assert_called_once_with(0)

    def test_params_passed_correctly(self):
        ctx = _mock_ctx()
        _run("def f(a, b) { return $a + $b }\npaint(call f(3, 4))", ctx)
        ctx.board_paint.assert_called_once_with(7)

    def test_local_scope_isolated(self):
        # Function assigns $y locally; global $y is only "assigned" in a dead branch
        # so the compiler allows paint($y) but at runtime $y is uninitialized → halt
        ctx = _Ctx()
        src = (
            "def f() { $y = 42 }\n"
            "if 0 { $y = 0 }\n"     # lets compiler see $y as assigned in global scope
            "call f()\n"
            "paint($y)"
        )
        with pytest.raises(HaltSignal):
            _run(src, ctx)

    def test_list_passed_by_value(self):
        # Mutations inside function must not affect caller's copy
        ctx = _mock_ctx()
        _run(
            "def f(lst) { push($lst, 99) }\n"
            "$l = list()\npush($l, 1)\n"
            "call f($l)\n"
            "paint(length($l))",
            ctx,
        )
        ctx.board_paint.assert_called_once_with(1)  # still length 1

    def test_undefined_function_raises_halt(self):
        # Can't compile a call to an undefined function → compile error
        # But if funcs dict is updated mid-game, an undefined call at runtime halts
        # We test this by injecting a Call node directly via a persisted_funcs miss.
        # Simplest: define f then clear bodies so runtime can't find it.
        from app.lang.interpreter import execute as _exec, HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Call
        # Build minimal AST for: call unknown()
        prog = Program(stmts=[ExprStmt(expr=Call(name="unknown", args=[]))])
        with pytest.raises(_HS):
            _exec(prog, _Ctx(), {})

    def test_recursion_raises_halt(self):
        # Deeply recursive calls should hit stack depth limit → HaltSignal
        ctx = _Ctx()
        with pytest.raises(HaltSignal):
            _run("def f() { return call f() }\ncall f()", ctx)

    def test_function_persists_across_executions(self):
        funcs = {}
        ctx = _Ctx()
        # First execution: define f
        _run("def f() { return 7 }", ctx, funcs)
        # Second execution: call f (which is now in funcs)
        ctx2 = _mock_ctx()
        execute(_compile("paint(call f())", funcs), ctx2, funcs)
        ctx2.board_paint.assert_called_once_with(7)

    def test_function_redefinition_replaces(self):
        funcs = {}
        ctx = _Ctx()
        _run("def f() { return 1 }", ctx, funcs)
        _run("def f() { return 2 }", ctx, funcs)
        ctx2 = _mock_ctx()
        execute(_compile("paint(call f())", funcs), ctx2, funcs)
        ctx2.board_paint.assert_called_once_with(2)

    def test_forward_call_within_same_script(self):
        # FuncDefs are registered before execution so forward calls work
        ctx = _mock_ctx()
        _run("paint(call f())\ndef f() { return 5 }", ctx)
        ctx.board_paint.assert_called_once_with(5)


# ================================================================== lists

class TestLists:
    def test_empty_list(self):
        ctx = _mock_ctx()
        _run("$l = list()\npaint(length($l))", ctx)
        ctx.board_paint.assert_called_once_with(0)

    def test_push_append(self):
        ctx = _mock_ctx()
        _run("$l = list()\npush($l, 5)\npaint(length($l))", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_push_at_index(self):
        # push(list, value, pos) — insert value 99 at position 0
        ctx = _mock_ctx()
        _run("$l = list()\npush($l, 1)\npush($l, 2)\npush($l, 99, 0)\npaint(index($l, 0))", ctx)
        ctx.board_paint.assert_called_once_with(99)

    def test_push_index_out_of_range_raises_halt(self):
        _raises_halt("$l = list()\npush($l, 5, 99)")

    def test_push_non_list_raises_halt(self):
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Push, IntLit
        prog = Program(stmts=[ExprStmt(expr=Push(lst=IntLit(value=5, line=1, col=1), value=IntLit(value=1, line=1, col=1), pos=None, line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_pop_last(self):
        ctx = _mock_ctx()
        _run("$l = list()\npush($l, 3)\npush($l, 7)\npaint(pop($l))", ctx)
        ctx.board_paint.assert_called_once_with(7)

    def test_pop_at_index(self):
        ctx = _mock_ctx()
        _run("$l = list()\npush($l, 3)\npush($l, 7)\npaint(pop($l, 0))", ctx)
        ctx.board_paint.assert_called_once_with(3)

    def test_pop_empty_raises_halt(self):
        _raises_halt("$l = list()\npop($l)")

    def test_pop_out_of_range_raises_halt(self):
        _raises_halt("$l = list()\npush($l, 1)\npop($l, 5)")

    def test_pop_non_list_raises_halt(self):
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Pop, IntLit
        prog = Program(stmts=[ExprStmt(expr=Pop(lst=IntLit(value=5, line=1, col=1), pos=None, line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_index_last(self):
        ctx = _mock_ctx()
        _run("$l = list()\npush($l, 4)\npush($l, 9)\npaint(index($l))", ctx)
        ctx.board_paint.assert_called_once_with(9)

    def test_index_at_position(self):
        ctx = _mock_ctx()
        _run("$l = list()\npush($l, 4)\npush($l, 9)\npaint(index($l, 0))", ctx)
        ctx.board_paint.assert_called_once_with(4)

    def test_index_empty_raises_halt(self):
        _raises_halt("$l = list()\nindex($l)")

    def test_index_out_of_range_raises_halt(self):
        _raises_halt("$l = list()\npush($l, 1)\nindex($l, 5)")

    def test_index_non_list_raises_halt(self):
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Index, IntLit
        prog = Program(stmts=[ExprStmt(expr=Index(lst=IntLit(value=5, line=1, col=1), pos=None, line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_length(self):
        ctx = _mock_ctx()
        _run("$l = list()\npush($l, 1)\npush($l, 2)\npush($l, 3)\npaint(length($l))", ctx)
        ctx.board_paint.assert_called_once_with(3)

    def test_length_non_list_raises_halt(self):
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Length, IntLit
        prog = Program(stmts=[ExprStmt(expr=Length(lst=IntLit(value=5, line=1, col=1), line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_copy_on_assign(self):
        # $b = $a should produce an independent copy of the list
        ctx = _mock_ctx()
        _run(
            "$a = list()\npush($a, 1)\n"
            "$b = $a\n"
            "push($b, 2)\n"
            "paint(length($a))",
            ctx,
        )
        ctx.board_paint.assert_called_once_with(1)  # $a still has 1 element


# ================================================================== board ops via ctx

class TestBoardOps:
    def test_move_calls_ctx(self):
        ctx = _mock_ctx()
        _run("move(UP)", ctx)
        ctx.board_move.assert_called_once_with("UP")

    def test_move_invalid_direction_raises_halt(self):
        # "HERE" is a location but not a valid direction → _expect_direction halts
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, Move, Constant
        prog = Program(stmts=[ExprStmt(expr=Move(dir=Constant(value="HERE", line=1, col=1), line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_paint_calls_ctx(self):
        ctx = _mock_ctx()
        _run("paint(3)", ctx)
        ctx.board_paint.assert_called_once_with(3)

    def test_get_friction_returns_ctx_value(self):
        ctx = _mock_ctx()
        ctx.board_get_friction.return_value = 5
        _run("$f = get_friction(UP)\npaint($f)", ctx)
        ctx.board_paint.assert_called_once_with(5)

    def test_get_friction_invalid_loc_raises_halt(self):
        # "NOWHERE" is not a valid location → _expect_location halts
        from app.lang.interpreter import HaltSignal as _HS
        from app.lang.nodes import Program, ExprStmt, GetFriction, Constant
        prog = Program(stmts=[ExprStmt(expr=GetFriction(loc=Constant(value="NOWHERE", line=1, col=1), line=1, col=1))])
        with pytest.raises(_HS):
            execute(prog, _Ctx(), {})

    def test_has_agent_returns_ctx_value(self):
        ctx = _mock_ctx()
        ctx.board_has_agent.return_value = 1
        _run("$h = has_agent(RIGHT)\npaint($h)", ctx)
        ctx.board_paint.assert_called_once_with(1)

    def test_my_paint_returns_ctx_value(self):
        ctx = _mock_ctx()
        ctx.board_my_paint.return_value = 3
        _run("$p = my_paint(HERE)\npaint($p)", ctx)
        ctx.board_paint.assert_called_once_with(3)

    def test_opp_paint_returns_ctx_value(self):
        ctx = _mock_ctx()
        ctx.board_opp_paint.return_value = 2
        _run("$p = opp_paint(LEFT)\npaint($p)", ctx)
        ctx.board_paint.assert_called_once_with(2)

    def test_ctx_reset_signal_propagates(self):
        from app.lang.interpreter import ResetSignal as _RS
        ctx = _mock_ctx()
        ctx.board_move.side_effect = _RS("collision")
        with pytest.raises(_RS):
            _run("move(UP)", ctx)

    def test_ctx_halt_signal_propagates(self):
        ctx = _mock_ctx()
        ctx.board_move.side_effect = HaltSignal("out of bounds")
        with pytest.raises(HaltSignal):
            _run("move(UP)", ctx)
