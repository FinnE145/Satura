from dataclasses import dataclass
from .nodes import (
    Program, Assign, ExprStmt, If, For, While, Halt, Return, FuncDef,
    BinOp, UnaryOp, VarRef, IntLit, FloatLit, Constant, Call,
    Min, Max, RangeExpr, Push, Pop, Index, Length, ListConstructor,
    Move, Paint, GetFriction, HasAgent, MyPaint, OppPaint,
)
from .tokens import TokenType


@dataclass
class CompileError:
    message: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"Line {self.line}, col {self.col}: {self.message}"


@dataclass
class CompileWarning:
    message: str
    line: int
    col: int

    def __str__(self) -> str:
        return f"Line {self.line}, col {self.col}: warning: {self.message}"


# Built-in variables are always readable but never assignable.
_BUILTIN_VARS = frozenset({"directions", "locations", "ops_remaining", "op_limit"})


class Compiler:
    def __init__(
        self,
        persisted_funcs: dict[str, tuple[list[str], bool]] | None = None,
    ):
        """
        persisted_funcs maps function names defined in previous turns to
        (params, return_could_be_float).  Pass this in so the compiler can
        validate cross-turn call sites and argument counts.
        """
        self.errors:   list[CompileError]   = []
        self.warnings: list[CompileWarning] = []

        # name -> (params, return_cbf) — grows as we register new defs
        self._funcs: dict[str, tuple[list[str], bool]] = {}
        if persisted_funcs:
            self._funcs.update(persisted_funcs)

        # Set during check() — reset per scope
        self._scope_vars: set[str]        = set()
        self._var_cbf:    dict[str, bool] = {}
        self._in_function: bool           = False

    # ------------------------------------------------------------------ public

    def check(
        self, program: Program
    ) -> tuple[list[CompileError], list[CompileWarning]]:
        """Run all compile-time checks. Returns (errors, warnings)."""

        # Pass 1 — register every top-level FuncDef so forward calls resolve.
        func_defs: list[FuncDef] = []
        for s in program.stmts:
            if isinstance(s, FuncDef):
                func_defs.append(s)
                self._funcs[s.name] = (s.params, False)  # return_cbf filled below

        # Pass 2 — fixed-point to determine each function's return could_be_float.
        # Repeats until no new function flips to True; handles mutual calls.
        changed = True
        while changed:
            changed = False
            for fd in func_defs:
                param_cbf = {p: False for p in fd.params}
                body_cbf  = self._compute_var_cbf(fd.body, param_cbf)
                ret_cbf   = self._func_return_cbf(fd.body, body_cbf)
                params, old = self._funcs[fd.name]
                if ret_cbf and not old:
                    self._funcs[fd.name] = (params, True)
                    changed = True

        # Pass 3 — compute could_be_float for every global variable.
        global_cbf = self._compute_var_cbf(program.stmts, {})

        # Pass 4 — full semantic walk.
        self._scope_vars  = self._collect_assigned_names(program.stmts)
        self._var_cbf     = global_cbf
        self._in_function = False
        for s in program.stmts:
            self._check_stmt(s)

        return self.errors, self.warnings

    # --------------------------------------------------------- error / warning

    def _error(self, msg: str, line: int, col: int) -> None:
        self.errors.append(CompileError(msg, line, col))

    def _warn(self, msg: str, line: int, col: int) -> None:
        self.warnings.append(CompileWarning(msg, line, col))

    # --------------------------------------------------- scope / cbf analysis

    def _collect_assigned_names(self, stmts: list) -> set[str]:
        """
        Return every variable name ever assigned in stmts, including inside
        if/for/while blocks.  Does NOT descend into FuncDef bodies.
        """
        names: set[str] = set()
        for s in stmts:
            if isinstance(s, Assign):
                names.add(s.name)
            elif isinstance(s, For):
                names.add(s.var)
                names |= self._collect_assigned_names(s.body)
            elif isinstance(s, If):
                for _, body in s.branches:
                    names |= self._collect_assigned_names(body)
                if s.else_body:
                    names |= self._collect_assigned_names(s.else_body)
            elif isinstance(s, While):
                names |= self._collect_assigned_names(s.body)
        return names

    def _collect_assignments(
        self, stmts: list, result: dict[str, list]
    ) -> None:
        """
        Populate result[name] = [value_expr, ...] for every assignment in stmts.
        For range() loop variables, inserts a sentinel IntLit so they type as int.
        Does NOT descend into FuncDef bodies.
        """
        for s in stmts:
            if isinstance(s, Assign):
                result.setdefault(s.name, []).append(s.value)
            elif isinstance(s, For):
                if isinstance(s.iterable, RangeExpr):
                    result.setdefault(s.var, []).append(IntLit(0))  # range yields ints
                self._collect_assignments(s.body, result)
            elif isinstance(s, If):
                for _, body in s.branches:
                    self._collect_assignments(body, result)
                if s.else_body:
                    self._collect_assignments(s.else_body, result)
            elif isinstance(s, While):
                self._collect_assignments(s.body, result)

    def _compute_var_cbf(
        self, stmts: list, initial: dict[str, bool]
    ) -> dict[str, bool]:
        """
        Compute could_be_float for every variable assigned in stmts.
        initial pre-seeds names (e.g. function parameters).
        Uses fixed-point iteration so mutually-dependent variables converge.
        """
        assignments: dict[str, list] = {}
        self._collect_assignments(stmts, assignments)

        cbf: dict[str, bool] = dict(initial)
        for name in assignments:
            cbf.setdefault(name, False)

        changed = True
        while changed:
            changed = False
            for name, exprs in assignments.items():
                if not cbf[name]:
                    for e in exprs:
                        if self._cbf(e, cbf):
                            cbf[name] = True
                            changed = True
                            break

        return cbf

    def _func_return_cbf(self, body: list, var_cbf: dict[str, bool]) -> bool:
        """True if any return statement in body (recursively) could yield a float."""
        for s in body:
            if isinstance(s, Return) and s.value is not None:
                if self._cbf(s.value, var_cbf):
                    return True
            elif isinstance(s, If):
                for _, branch in s.branches:
                    if self._func_return_cbf(branch, var_cbf):
                        return True
                if s.else_body and self._func_return_cbf(s.else_body, var_cbf):
                    return True
            elif isinstance(s, (For, While)):
                if self._func_return_cbf(s.body, var_cbf):
                    return True
        return False

    def _cbf(self, expr, var_cbf: dict[str, bool]) -> bool:
        """
        Compute could_be_float for expr.  Pure — no side effects.
        """
        if isinstance(expr, FloatLit):
            return True
        if isinstance(expr, (IntLit, Constant, ListConstructor)):
            return False
        if isinstance(expr, VarRef):
            return var_cbf.get(expr.name, False)
        if isinstance(expr, BinOp):
            if expr.op == TokenType.SLASH:
                return True  # division always produces a float
            if expr.op in (TokenType.PLUS, TokenType.MINUS, TokenType.STAR):
                return self._cbf(expr.left, var_cbf) or self._cbf(expr.right, var_cbf)
            # %, comparisons, and, or — all produce integer/bool
            return False
        if isinstance(expr, UnaryOp):
            return self._cbf(expr.operand, var_cbf) if expr.op == TokenType.MINUS else False
        if isinstance(expr, (Min, Max)):
            return self._cbf(expr.left, var_cbf) or self._cbf(expr.right, var_cbf)
        if isinstance(expr, GetFriction):
            return False  # returns int (0, 1, 2, 4, 6, 8, 10, or 20)
        if isinstance(expr, Call):
            _, ret_cbf = self._funcs.get(expr.name, ([], False))
            return ret_cbf
        return False  # board ops returning bool/int, Length, Push, Pop, Index

    # --------------------------------------------------- statement checking

    def _check_stmt(self, s) -> None:
        if isinstance(s, Assign):
            if s.name in _BUILTIN_VARS:
                self._error(
                    f"assignment to read-only built-in variable '${s.name}'",
                    s.line, s.col,
                )
            self._check_expr(s.value)

        elif isinstance(s, ExprStmt):
            self._check_expr(s.expr)

        elif isinstance(s, If):
            for cond, body in s.branches:
                self._check_expr(cond)
                for inner in body:
                    self._check_stmt(inner)
            if s.else_body:
                for inner in s.else_body:
                    self._check_stmt(inner)

        elif isinstance(s, For):
            if isinstance(s.iterable, RangeExpr):
                r = s.iterable
                for arg, label in [(r.start, "start"), (r.stop, "stop"), (r.step, "step")]:
                    if arg is None:
                        continue
                    self._check_expr(arg)
                    if self._cbf(arg, self._var_cbf):
                        self._warn(
                            f"range() {label} argument might be a float"
                            " — range requires integers",
                            arg.line, arg.col,
                        )
            else:
                self._check_expr(s.iterable)
            for inner in s.body:
                self._check_stmt(inner)

        elif isinstance(s, While):
            self._check_expr(s.cond)
            for inner in s.body:
                self._check_stmt(inner)

        elif isinstance(s, Return):
            if not self._in_function:
                self._error("'return' used outside a function body", s.line, s.col)
            elif s.value is not None:
                self._check_expr(s.value)

        elif isinstance(s, FuncDef):
            if self._in_function:
                self._error(
                    "function definitions cannot be nested inside another function",
                    s.line, s.col,
                )
                return
            # Enter isolated function scope — save and restore surrounding state
            outer_scope   = self._scope_vars
            outer_cbf     = self._var_cbf
            outer_in_func = self._in_function

            param_cbf         = {p: False for p in s.params}
            self._scope_vars  = set(s.params) | self._collect_assigned_names(s.body)
            self._var_cbf     = self._compute_var_cbf(s.body, param_cbf)
            self._in_function = True

            for inner in s.body:
                self._check_stmt(inner)

            self._scope_vars  = outer_scope
            self._var_cbf     = outer_cbf
            self._in_function = outer_in_func

        # Halt — nothing to check

    # --------------------------------------------------- expression checking

    def _check_expr(self, expr) -> None:
        """Walk an expression, reporting errors and warnings."""

        if isinstance(expr, VarRef):
            if expr.name not in _BUILTIN_VARS and expr.name not in self._scope_vars:
                self._error(f"undefined variable '${expr.name}'", expr.line, expr.col)

        elif isinstance(expr, (BinOp, Min, Max)):
            self._check_expr(expr.left)
            self._check_expr(expr.right)

        elif isinstance(expr, UnaryOp):
            self._check_expr(expr.operand)

        elif isinstance(expr, Move):
            self._check_expr(expr.dir)
            # Only catches a direct literal HERE — passing HERE via a variable
            # ($x = HERE; move($x)) requires value-range tracking and is left
            # as a runtime halt, not a compile error.
            if isinstance(expr.dir, Constant) and expr.dir.value == "HERE":
                self._error(
                    "move() requires a direction (UP/DOWN/LEFT/RIGHT), not HERE",
                    expr.dir.line, expr.dir.col,
                )

        elif isinstance(expr, HasAgent):
            self._check_expr(expr.dir)
            # Same limitation as move() above.
            if isinstance(expr.dir, Constant) and expr.dir.value == "HERE":
                self._error(
                    "has_agent() requires a direction (UP/DOWN/LEFT/RIGHT), not HERE",
                    expr.dir.line, expr.dir.col,
                )

        elif isinstance(expr, Paint):
            self._check_expr(expr.num)
            if self._cbf(expr.num, self._var_cbf):
                self._warn(
                    "paint() argument might be a float"
                    " — paint requires a positive integer",
                    expr.num.line, expr.num.col,
                )

        elif isinstance(expr, (GetFriction, MyPaint, OppPaint)):
            self._check_expr(expr.loc)

        elif isinstance(expr, Push):
            self._check_expr(expr.lst)
            self._check_expr(expr.value)
            if expr.pos is not None:
                self._check_expr(expr.pos)
                if self._cbf(expr.pos, self._var_cbf):
                    self._warn(
                        "push() position argument might be a float"
                        " — position requires an integer",
                        expr.pos.line, expr.pos.col,
                    )

        elif isinstance(expr, Pop):
            self._check_expr(expr.lst)
            if expr.pos is not None:
                self._check_expr(expr.pos)
                if self._cbf(expr.pos, self._var_cbf):
                    self._warn(
                        "pop() position argument might be a float"
                        " — position requires an integer",
                        expr.pos.line, expr.pos.col,
                    )

        elif isinstance(expr, Index):
            self._check_expr(expr.lst)
            if expr.pos is not None:
                self._check_expr(expr.pos)
                if self._cbf(expr.pos, self._var_cbf):
                    self._warn(
                        "index() position argument might be a float"
                        " — position requires an integer",
                        expr.pos.line, expr.pos.col,
                    )

        elif isinstance(expr, Length):
            self._check_expr(expr.lst)

        elif isinstance(expr, Call):
            if expr.name not in self._funcs:
                self._error(
                    f"call to undefined function '{expr.name}'",
                    expr.line, expr.col,
                )
                return
            params, _ = self._funcs[expr.name]
            if len(expr.args) != len(params):
                self._error(
                    f"'{expr.name}' expects {len(params)} argument(s),"
                    f" got {len(expr.args)}",
                    expr.line, expr.col,
                )
            for arg in expr.args:
                self._check_expr(arg)

        # IntLit, FloatLit, Constant, ListConstructor — nothing to check


def check(
    program: Program,
    persisted_funcs: dict[str, tuple[list[str], bool]] | None = None,
) -> tuple[list[CompileError], list[CompileWarning]]:
    """Convenience wrapper: check a parsed program and return (errors, warnings)."""
    return Compiler(persisted_funcs).check(program)
