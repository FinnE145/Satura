import pytest
from app.lang.lexer import tokenize
from app.lang.parser import parse
from app.lang.compiler import check, CompileError, CompileWarning, Type


# ------------------------------------------------------------------ helpers

def compile(src, persisted_funcs=None):
    """Lex, parse, and check src. Returns (errors, warnings)."""
    return check(parse(tokenize(src)), persisted_funcs)


def errors(src, persisted_funcs=None):
    errs, _ = compile(src, persisted_funcs)
    return errs


def warnings(src, persisted_funcs=None):
    _, warns = compile(src, persisted_funcs)
    return warns


def error_messages(src, persisted_funcs=None):
    return [e.message for e in errors(src, persisted_funcs)]


def warning_messages(src, persisted_funcs=None):
    return [w.message for w in warnings(src, persisted_funcs)]


def assert_clean(src, persisted_funcs=None):
    errs, warns = compile(src, persisted_funcs)
    assert errs == [], f"unexpected errors: {errs}"
    assert warns == [], f"unexpected warnings: {warns}"


# -------------------------------------------------------- assignment errors

class TestAssignmentErrors:
    def test_assign_to_directions(self):
        msgs = error_messages("$directions = 5")
        assert any("directions" in m for m in msgs)

    def test_assign_to_locations(self):
        msgs = error_messages("$locations = 5")
        assert any("locations" in m for m in msgs)

    def test_assign_to_ops_remaining(self):
        msgs = error_messages("$ops_remaining = 5")
        assert any("ops_remaining" in m for m in msgs)

    def test_assign_to_op_limit(self):
        msgs = error_messages("$op_limit = 5")
        assert any("op_limit" in m for m in msgs)

    def test_assign_to_user_var_is_fine(self):
        assert errors("$x = 5") == []

    def test_builtin_assignment_has_position(self):
        errs = errors("$directions = 5")
        assert errs[0].line == 1
        assert errs[0].col == 1


# ------------------------------------------------------- undefined variables

class TestUndefinedVariables:
    def test_read_never_assigned(self):
        msgs = error_messages("move($x)")
        assert any("$x" in m for m in msgs)

    def test_assigned_before_read_is_fine(self):
        assert errors("$x = UP\nmove($x)") == []

    def test_assigned_in_branch_counts(self):
        # $x is assigned somewhere — compiler only errors if NEVER assigned
        src = "if $ops_remaining > 0 { $x = 1 }\npaint($x)"
        assert errors(src) == []

    def test_builtin_vars_always_in_scope(self):
        # $directions is always accessible (check via length, which takes a list)
        assert_clean("length($directions)")

    def test_undefined_in_condition(self):
        msgs = error_messages("if $y > 0 { halt }")
        assert any("$y" in m for m in msgs)

    def test_undefined_in_function_body(self):
        # $z is not a param and never assigned inside the function
        msgs = error_messages("def f(a) { move($z) }")
        assert any("$z" in m for m in msgs)

    def test_param_is_in_scope(self):
        assert errors("def f(d) { move($d) }") == []

    def test_global_var_not_visible_in_function(self):
        # $x is assigned globally but functions have isolated scope
        src = "$x = 5\ndef f() { move($x) }"
        msgs = error_messages(src)
        assert any("$x" in m for m in msgs)

    def test_undefined_error_has_position(self):
        errs = errors("move($x)")
        assert errs[0].line >= 1


# ---------------------------------------------------------- return errors

class TestReturnErrors:
    def test_return_at_top_level(self):
        msgs = error_messages("return 5")
        assert any("return" in m.lower() for m in msgs)

    def test_return_inside_function_is_fine(self):
        assert errors("def f() { return 5 }") == []

    def test_bare_return_inside_function_is_fine(self):
        assert errors("def f() { return }") == []

    def test_return_in_nested_if_inside_function(self):
        assert errors("def f() { if $ops_remaining > 0 { return 1 } }") == []


# ---------------------------------------------------------- nested def errors

class TestNestedDefErrors:
    def test_nested_def_is_error(self):
        src = "def outer() { def inner() { halt } }"
        msgs = error_messages(src)
        assert any("nested" in m.lower() for m in msgs)

    def test_top_level_def_is_fine(self):
        assert errors("def f() { halt }\ndef g() { halt }") == []


# ------------------------------------------------------- board op errors

class TestBoardOpErrors:
    def test_move_here_is_error(self):
        msgs = error_messages("move(HERE)")
        assert any("move" in m for m in msgs)

    def test_move_int_is_error(self):
        msgs = error_messages("move(5)")
        assert any("move" in m for m in msgs)

    def test_move_up_is_fine(self):
        assert errors("move(UP)") == []

    def test_move_var_is_fine(self):
        assert errors("$d = UP\nmove($d)") == []

    def test_has_agent_here_is_error(self):
        msgs = error_messages("has_agent(HERE)")
        assert any("has_agent" in m for m in msgs)

    def test_has_agent_down_is_fine(self):
        assert errors("has_agent(DOWN)") == []

    def test_get_friction_here_is_fine(self):
        assert errors("get_friction(HERE)") == []

    def test_get_friction_up_is_fine(self):
        # directions are also valid locations
        assert errors("get_friction(UP)") == []

    def test_get_friction_int_is_error(self):
        msgs = error_messages("get_friction(5)")
        assert any("get_friction" in m for m in msgs)

    def test_my_paint_here_is_fine(self):
        assert errors("my_paint(HERE)") == []

    def test_opp_paint_here_is_fine(self):
        assert errors("opp_paint(HERE)") == []

    def test_paint_float_warns(self):
        # float is accepted but warns; runtime coercion handles fractional check
        assert errors("paint(1.5)") == []
        assert any("paint" in m for m in warning_messages("paint(1.5)"))

    def test_paint_dir_is_error(self):
        msgs = error_messages("paint(UP)")
        assert any("paint" in m for m in msgs)

    def test_paint_int_is_fine(self):
        assert errors("paint(3)") == []


# -------------------------------------------------------- function call errors

class TestCallErrors:
    def test_call_undefined_function(self):
        msgs = error_messages("call foo()")
        assert any("foo" in m for m in msgs)

    def test_call_defined_function_is_fine(self):
        assert errors("def go(d) { move($d) }\ncall go(UP)") == []

    def test_wrong_arg_count_too_few(self):
        msgs = error_messages("def go(d) { move($d) }\ncall go()")
        assert any("expects" in m and "1" in m for m in msgs)

    def test_wrong_arg_count_too_many(self):
        msgs = error_messages("def go(d) { move($d) }\ncall go(UP, DOWN)")
        assert any("expects" in m for m in msgs)

    def test_forward_reference_is_fine(self):
        # call appears before def in source — forward refs are valid
        src = "call go(UP)\ndef go(d) { move($d) }"
        assert errors(src) == []

    def test_call_persisted_function(self):
        # Function defined in a previous turn
        persisted = {"go": (["d"], Type.INT)}
        assert errors("call go(UP)", persisted) == []

    def test_call_persisted_wrong_args(self):
        persisted = {"go": (["d"], Type.INT)}
        msgs = error_messages("call go(UP, DOWN)", persisted)
        assert any("expects" in m for m in msgs)


# -------------------------------------------------------- type errors

class TestTypeErrors:
    """Guaranteed type mismatches — no overlap between actual and required type."""

    def test_float_in_paint_warns(self):
        assert errors("paint(1.5)") == []
        assert warnings("paint(1.5)") != []

    def test_division_result_in_paint_warns(self):
        # / always produces FLOAT → warns
        assert errors("$x = 6\n$y = 3\npaint($x / $y)") == []
        assert warnings("$x = 6\n$y = 3\npaint($x / $y)") != []

    def test_range_float_stop_warns(self):
        assert errors("for $i in range(1.5) { halt }") == []
        assert warnings("for $i in range(1.5) { halt }") != []

    def test_range_float_start_warns(self):
        assert errors("for $i in range(1.0, 5) { halt }") == []
        assert warnings("for $i in range(1.0, 5) { halt }") != []

    def test_push_float_pos_warns(self):
        assert errors("$lst = list()\n$p = 1.0\npush($lst, 1, $p)") == []
        assert warnings("$lst = list()\n$p = 1.0\npush($lst, 1, $p)") != []

    def test_pop_float_pos_warns(self):
        assert errors("$lst = list()\n$p = 1.5\npop($lst, $p)") == []
        assert warnings("$lst = list()\n$p = 1.5\npop($lst, $p)") != []

    def test_index_float_pos_warns(self):
        assert errors("$lst = list()\n$p = 1.5\nindex($lst, $p)") == []
        assert warnings("$lst = list()\n$p = 1.5\nindex($lst, $p)") != []

    def test_function_returning_float_in_paint_warns(self):
        src = "def get_val() { return 1.5 }\n$x = call get_val()\npaint($x)"
        assert errors(src) == []
        assert warnings(src) != []

    def test_dir_in_paint_is_error(self):
        assert errors("paint(UP)") != []

    def test_loc_in_move_is_error(self):
        # HERE is LOC, move requires DIR
        assert errors("move(HERE)") != []

    def test_int_in_move_is_error(self):
        assert errors("move(5)") != []

    def test_list_in_arithmetic_is_error(self):
        assert errors("$x = list()\n$y = $x + 1") != []

    def test_push_on_non_list_is_error(self):
        assert errors("$x = 5\npush($x, 1)") != []

    def test_pop_on_non_list_is_error(self):
        assert errors("$x = 5\npop($x)") != []

    def test_length_on_non_list_is_error(self):
        assert errors("$x = 5\nlength($x)") != []

    def test_for_over_non_list_is_error(self):
        assert errors("$x = 5\nfor $i in $x { halt }") != []


# ------------------------------------------------------- type warnings

class TestTypeWarnings:
    """Partial type overlaps — possibly wrong but not guaranteed."""

    def test_int_or_float_var_in_paint_warns(self):
        # $y is INT|FLOAT — warns because float component could cause runtime halt
        msgs = warning_messages("$x = 1.0\n$y = $x + 1\npaint($y)")
        assert any("paint" in m for m in msgs)

    def test_int_only_in_paint_is_clean(self):
        assert warnings("$x = 2\n$y = $x + 1\npaint($y)") == []

    def test_modulo_always_int(self):
        assert warnings("$x = 5.0\npaint($x % 2)") == []

    def test_comparison_always_int(self):
        assert warnings("$x = 1.5\npaint($x > 0)") == []

    def test_get_friction_nullable_warns_in_paint(self):
        # get_friction returns NULL for out-of-bounds, so passing it to paint() warns
        msgs = warning_messages("paint(get_friction(HERE))")
        assert any("paint" in m for m in msgs)

    def test_min_int_or_float_warns(self):
        # min(float, int) → INT|FLOAT — warns because float component could cause runtime halt
        msgs = warning_messages("paint(min(1.5, 2))")
        assert any("paint" in m for m in msgs)

    def test_max_int_only_is_clean(self):
        assert warnings("paint(max(1, 2))") == []

    def test_range_int_arg_is_clean(self):
        assert warnings("for $i in range(5) { halt }") == []

    def test_function_return_int_is_clean(self):
        src = "def get_val() { return 5 }\n$x = call get_val()\npaint($x)"
        assert warnings(src) == []

    def test_float_taint_does_not_cross_function_boundary(self):
        # $g is FLOAT, but f() has isolated scope — $x inside is INT only
        src = "$g = 1.5\ndef f() { $x = 1\npaint($x) }"
        assert warnings(src) == []

    def test_dir_or_loc_var_in_move_warns(self):
        # $d could be UP (DIR) or HERE (LOC) — overlaps DIR but LOC part is wrong
        src = "$d = UP\nif $ops_remaining > 0 { $d = HERE }\nmove($d)"
        msgs = warning_messages(src)
        assert any("move" in m for m in msgs)

    def test_pure_dir_var_in_move_is_clean(self):
        assert warnings("$d = UP\nmove($d)") == []


# -------------------------------------------------------- clean scripts

class TestCleanScripts:
    def test_simple_move(self):
        assert_clean("move(UP)")

    def test_conditional_move(self):
        assert_clean("if $ops_remaining > 0 { move(UP) }")

    def test_loop_over_directions(self):
        assert_clean("for $dir in $directions { move($dir) }")

    def test_loop_over_locations(self):
        assert_clean("for $loc in $locations { get_friction($loc) }")

    def test_function_def_and_call(self):
        assert_clean("def go(d) { move($d) }\ncall go(UP)")

    def test_full_script(self):
        src = """
        def safe_move(d) {
            $cost = get_friction($d)
            if $ops_remaining > $cost { move($d) }
        }
        for $dir in $directions {
            call safe_move($dir)
        }
        """
        assert_clean(src)
