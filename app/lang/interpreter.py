from __future__ import annotations
import copy
from .nodes import (
    Program, Assign, ExprStmt, If, For, While, Halt, Return, FuncDef,
    BinOp, UnaryOp, VarRef, IntLit, FloatLit, Constant, Call,
    Min, Max, RangeExpr, Push, Pop, Index, Length, ListConstructor,
    Move, Paint, GetFriction, HasAgent, MyPaint, OppPaint,
)
from .tokens import TokenType
from .compiler import Type

# Non-string key for storing function bodies in persisted_funcs.
# Integer 0 can never collide with a user-defined function name (always a str).
_BODIES_KEY = 0

# Built-in list constants, per spec Section 9.
_DIRECTIONS = ["UP", "DOWN", "LEFT", "RIGHT"]
_LOCATIONS  = ["HERE", "UP", "DOWN", "LEFT", "RIGHT"]

_VALID_DIRECTIONS = frozenset(_DIRECTIONS)
_VALID_LOCATIONS  = frozenset(_LOCATIONS)


# --------------------------------------------------------------------------- signals

class HaltSignal(Exception):
    """Raised by halt keyword or a runtime halt condition. Actions taken stand."""


class ResetSignal(Exception):
    """Raised when the entire execution must be undone."""


# --------------------------------------------------------------------------- internal control flow

class _ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


# --------------------------------------------------------------------------- runtime helpers

def _type_name(v) -> str:
    if v is None:
        return "null"
    return type(v).__name__


def _coerce_int(v, ctx: str) -> int:
    """
    Coerce v to int per spec Section 4.3:
      - int → ok
      - float with no fractional component → coerce to int
      - anything else → runtime halt
    """
    if isinstance(v, bool):
        # Python bool is a subclass of int, but booleans should not appear
        # in this language; treat them as ints (True=1, False=0) defensively.
        return int(v)
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        if v == int(v):
            return int(v)
        raise HaltSignal(f"{ctx}: fractional float {v} cannot be used as int")
    raise HaltSignal(f"{ctx}: expected int, got {_type_name(v)}")


def _check_bool(v, ctx: str) -> int:
    """
    Validate that v is exactly int 0 or 1 (spec Section 7.1 / 5.7).
    Applies float-to-int coercion first, then enforces 0/1 constraint.
    """
    iv = _coerce_int(v, ctx)
    if iv not in (0, 1):
        raise HaltSignal(f"{ctx}: condition must be 0 or 1, got {iv}")
    return iv


def _expect_direction(v, ctx: str) -> str:
    if v not in _VALID_DIRECTIONS:
        raise HaltSignal(f"{ctx}: expected direction (UP/DOWN/LEFT/RIGHT), got {v!r}")
    return v


def _expect_location(v, ctx: str) -> str:
    if v not in _VALID_LOCATIONS:
        raise HaltSignal(f"{ctx}: expected location, got {v!r}")
    return v


def _copy_list(v):
    """Deep-copy v if it is a list; return v unchanged otherwise."""
    return copy.deepcopy(v) if isinstance(v, list) else v


# --------------------------------------------------------------------------- public API

def execute(program: Program, ctx, persisted_funcs: dict) -> None:
    """
    Walk the compiled AST and apply its effects to ctx.

    Raises HaltSignal or ResetSignal on runtime faults.
    Updates persisted_funcs with any newly defined functions so that
    subsequent turns' compile() and execute() calls can reference them
    without the player paying word costs again.

    Function bodies are stored under the integer key 0 (never conflicts
    with string function names). Compiler-compatible signatures are stored
    under string keys so check() can validate call sites in future scripts.
    """
    _Interpreter(ctx, persisted_funcs).run(program)


# --------------------------------------------------------------------------- interpreter

class _Interpreter:
    def __init__(self, ctx, persisted_funcs: dict):
        self._ctx = ctx
        self._persisted = persisted_funcs
        # Bodies dict: {name: FuncDef} — shared across all turns.
        self._bodies: dict = persisted_funcs.setdefault(_BODIES_KEY, {})

    # ------------------------------------------------------------------ entry

    def run(self, program: Program) -> None:
        env: dict = {}
        # Register all top-level FuncDefs before executing so forward calls work.
        for stmt in program.stmts:
            if isinstance(stmt, FuncDef):
                self._register_func(stmt)
        for stmt in program.stmts:
            self._exec(stmt, env)

    # ----------------------------------------------------------- registration

    def _register_func(self, fd: FuncDef) -> None:
        """
        Persist a function definition so it survives across turns.
        Stores the body for the interpreter and a compiler-compatible
        signature for future check() calls — both without word cost to
        scripts that merely call the function.
        """
        self._bodies[fd.name] = fd
        self._persisted[fd.name] = (fd.params, Type(0))

    # ---------------------------------------------------------------- statements

    def _exec(self, stmt, env: dict) -> None:  # noqa: C901
        if isinstance(stmt, Assign):
            val = self._eval(stmt.value, env)
            # Copy on write: each variable holds an independent list copy so
            # that assigning $b = $a does not alias the two.
            env[stmt.name] = _copy_list(val)

        elif isinstance(stmt, ExprStmt):
            self._eval(stmt.expr, env)

        elif isinstance(stmt, If):
            for cond, body in stmt.branches:
                if _check_bool(self._eval(cond, env), "if/elif condition"):
                    for s in body:
                        self._exec(s, env)
                    return
            if stmt.else_body:
                for s in stmt.else_body:
                    self._exec(s, env)

        elif isinstance(stmt, For):
            for val in self._iter(stmt.iterable, env):
                env[stmt.var] = val       # globally scoped; persists after loop
                for s in stmt.body:
                    self._exec(s, env)

        elif isinstance(stmt, While):
            while _check_bool(self._eval(stmt.cond, env), "while condition"):
                for s in stmt.body:
                    self._exec(s, env)

        elif isinstance(stmt, Halt):
            raise HaltSignal("halt")

        elif isinstance(stmt, Return):
            val = 0 if stmt.value is None else self._eval(stmt.value, env)
            raise _ReturnSignal(val)

        elif isinstance(stmt, FuncDef):
            # Re-registration: a redefined function replaces the old one.
            self._register_func(stmt)

    # --------------------------------------------------------------- iteration

    def _iter(self, iterable, env: dict):
        if isinstance(iterable, RangeExpr):
            start = 0 if iterable.start is None else _coerce_int(
                self._eval(iterable.start, env), "range() start"
            )
            stop = _coerce_int(self._eval(iterable.stop, env), "range() stop")
            step = 1 if iterable.step is None else _coerce_int(
                self._eval(iterable.step, env), "range() step"
            )
            if step == 0:
                raise HaltSignal("range() step cannot be zero")
            return range(start, stop, step)
        lst = self._eval(iterable, env)
        if not isinstance(lst, list):
            raise HaltSignal("for loop iterable is not a list")
        return list(lst)    # snapshot so mid-loop mutations do not affect iteration

    # --------------------------------------------------------------- expressions

    def _eval(self, expr, env: dict):  # noqa: C901
        if isinstance(expr, IntLit):
            return expr.value

        if isinstance(expr, FloatLit):
            return expr.value

        if isinstance(expr, Constant):
            if expr.value == "NULL":
                return None
            return expr.value   # "UP" / "DOWN" / "LEFT" / "RIGHT" / "HERE"

        if isinstance(expr, ListConstructor):
            return []

        if isinstance(expr, VarRef):
            return self._read_var(expr.name, env)

        if isinstance(expr, BinOp):
            return self._eval_binop(expr, env)

        if isinstance(expr, UnaryOp):
            v = self._eval(expr.operand, env)
            if expr.op == TokenType.MINUS:
                if not isinstance(v, (int, float)):
                    raise HaltSignal(f"unary minus requires numeric value, got {_type_name(v)}")
                return -v
            if expr.op == TokenType.NOT:
                iv = _check_bool(v, "not operand")
                return 1 - iv
            return 0

        if isinstance(expr, Min):
            l = self._eval(expr.left, env)
            r = self._eval(expr.right, env)
            if not isinstance(l, (int, float)) or not isinstance(r, (int, float)):
                raise HaltSignal("min() requires numeric operands")
            return min(l, r)

        if isinstance(expr, Max):
            l = self._eval(expr.left, env)
            r = self._eval(expr.right, env)
            if not isinstance(l, (int, float)) or not isinstance(r, (int, float)):
                raise HaltSignal("max() requires numeric operands")
            return max(l, r)

        # ---- board operations (ctx raises HaltSignal/ResetSignal as needed) ----

        if isinstance(expr, Move):
            v = self._eval(expr.dir, env)
            self._ctx.board_move(_expect_direction(v, "move()"))
            return 0

        if isinstance(expr, Paint):
            v = self._eval(expr.num, env)
            self._ctx.board_paint(_coerce_int(v, "paint()"))
            return 0

        if isinstance(expr, GetFriction):
            v = self._eval(expr.loc, env)
            return self._ctx.board_get_friction(_expect_location(v, "get_friction()"))

        if isinstance(expr, HasAgent):
            v = self._eval(expr.dir, env)
            return self._ctx.board_has_agent(_expect_direction(v, "has_agent()"))

        if isinstance(expr, MyPaint):
            v = self._eval(expr.loc, env)
            return self._ctx.board_my_paint(_expect_location(v, "my_paint()"))

        if isinstance(expr, OppPaint):
            v = self._eval(expr.loc, env)
            return self._ctx.board_opp_paint(_expect_location(v, "opp_paint()"))

        # ---- list operations — mutate in place; copy-on-write is at Assign ----

        if isinstance(expr, Push):
            lst = self._eval(expr.lst, env)
            if not isinstance(lst, list):
                raise HaltSignal("push() requires a list as first argument")
            val = self._eval(expr.value, env)
            if expr.pos is None:
                lst.append(val)
            else:
                pos = _coerce_int(self._eval(expr.pos, env), "push() pos")
                if pos < 0 or pos > len(lst):
                    raise HaltSignal(f"push() index {pos} out of range for list of length {len(lst)}")
                lst.insert(pos, val)
            return lst

        if isinstance(expr, Pop):
            lst = self._eval(expr.lst, env)
            if not isinstance(lst, list):
                raise HaltSignal("pop() requires a list as first argument")
            if not lst:
                raise HaltSignal("pop() on empty list")
            if expr.pos is None:
                return lst.pop()
            pos = _coerce_int(self._eval(expr.pos, env), "pop() pos")
            if pos < 0 or pos >= len(lst):
                raise HaltSignal(f"pop() index {pos} out of range for list of length {len(lst)}")
            return lst.pop(pos)

        if isinstance(expr, Index):
            lst = self._eval(expr.lst, env)
            if not isinstance(lst, list):
                raise HaltSignal("index() requires a list as first argument")
            if not lst:
                raise HaltSignal("index() on empty list")
            if expr.pos is None:
                return lst[-1]
            pos = _coerce_int(self._eval(expr.pos, env), "index() pos")
            if pos < 0 or pos >= len(lst):
                raise HaltSignal(f"index() index {pos} out of range for list of length {len(lst)}")
            return lst[pos]

        if isinstance(expr, Length):
            lst = self._eval(expr.lst, env)
            if not isinstance(lst, list):
                raise HaltSignal("length() requires a list argument")
            return len(lst)

        if isinstance(expr, Call):
            return self._call(expr, env)

        return 0

    # ------------------------------------------------------------ binary ops

    def _eval_binop(self, expr: BinOp, env: dict):
        op = expr.op

        # Short-circuit boolean operators — operands must be exactly 0 or 1.
        if op == TokenType.AND:
            l = _check_bool(self._eval(expr.left, env), "and left operand")
            if l == 0:
                return 0
            r = _check_bool(self._eval(expr.right, env), "and right operand")
            return r   # already 0 or 1

        if op == TokenType.OR:
            l = _check_bool(self._eval(expr.left, env), "or left operand")
            if l == 1:
                return 1
            r = _check_bool(self._eval(expr.right, env), "or right operand")
            return r   # already 0 or 1

        l = self._eval(expr.left, env)
        r = self._eval(expr.right, env)

        if op in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR,
                  TokenType.SLASH, TokenType.PERCENT):
            if not isinstance(l, (int, float)):
                raise HaltSignal(f"arithmetic requires numeric operands, got {_type_name(l)}")
            if not isinstance(r, (int, float)):
                raise HaltSignal(f"arithmetic requires numeric operands, got {_type_name(r)}")
            if op == TokenType.PLUS:    return l + r
            if op == TokenType.MINUS:   return l - r
            if op == TokenType.STAR:    return l * r
            if op == TokenType.SLASH:
                if r == 0:
                    raise HaltSignal("division by zero")
                return l / r        # always float per spec
            if op == TokenType.PERCENT:
                il = _coerce_int(l, "% left operand")
                ir = _coerce_int(r, "% right operand")
                if ir == 0:
                    raise HaltSignal("modulo by zero")
                return il % ir      # always int per spec

        # Comparison operators — return int 0 or 1.
        if op == TokenType.EQ:  return 1 if l == r else 0
        if op == TokenType.NEQ: return 1 if l != r else 0
        if op in (TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE):
            if not isinstance(l, (int, float)) or not isinstance(r, (int, float)):
                raise HaltSignal("ordered comparison requires numeric operands")
            if op == TokenType.LT:  return 1 if l < r else 0
            if op == TokenType.GT:  return 1 if l > r else 0
            if op == TokenType.LTE: return 1 if l <= r else 0
            if op == TokenType.GTE: return 1 if l >= r else 0

        return 0

    # ---------------------------------------------------------- function calls

    def _call(self, expr: Call, caller_env: dict):
        fd = self._bodies.get(expr.name)
        if fd is None:
            raise HaltSignal(f"call to undefined function '{expr.name}'")

        # Evaluate args in caller scope; deep-copy lists so callee mutations
        # cannot affect the caller's lists (pass-by-value semantics, spec 6.2).
        args = [_copy_list(self._eval(a, caller_env)) for a in expr.args]

        # Function scope is fully isolated from the caller's globals.
        local_env: dict = dict(zip(fd.params, args))
        try:
            for stmt in fd.body:
                self._exec(stmt, local_env)
        except _ReturnSignal as ret:
            return ret.value
        except RecursionError:
            raise HaltSignal("stack depth exceeded")

        return 0    # implicit return 0

    # ---------------------------------------------------------- variable read

    def _read_var(self, name: str, env: dict):
        if name == "directions":
            return list(_DIRECTIONS)    # fresh copy each read
        if name == "locations":
            return list(_LOCATIONS)
        if name == "ops_remaining":
            return self._ctx.ops_remaining
        if name == "op_limit":
            return self._ctx.op_limit
        if name not in env:
            raise HaltSignal(f"uninitialized variable '${name}'")
        # Return reference so push/pop expressions can mutate the stored list.
        # Value isolation between variables is enforced on assignment (Assign).
        return env[name]
