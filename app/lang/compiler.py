from dataclasses import dataclass
from enum import Flag, auto
from .nodes import (
    Program, Assign, ExprStmt, If, For, While, Halt, Return, FuncDef,
    BinOp, UnaryOp, VarRef, IntLit, FloatLit, Constant, Call,
    Min, Max, RangeExpr, Push, Pop, Index, Length, ListConstructor,
    Move, Paint, GetFriction, HasAgent, MyPaint, OppPaint,
)
from .tokens import TokenType


# --------------------------------------------------------------------------- types

class Type(Flag):
    INT   = auto()
    FLOAT = auto()
    DIR   = auto()
    LOC   = auto()
    LIST  = auto()


NUMERIC  = Type.INT | Type.FLOAT
LOCATION = Type.DIR | Type.LOC
ANY      = Type.INT | Type.FLOAT | Type.DIR | Type.LOC | Type.LIST

_COMPARISON_OPS = frozenset({
    TokenType.EQ, TokenType.NEQ,
    TokenType.LT, TokenType.GT, TokenType.LTE, TokenType.GTE,
})

# Known types for built-in read-only variables.
_BUILTIN_TYPES: dict[str, Type] = {
    "directions":    Type.LIST,
    "locations":     Type.LIST,
    "ops_remaining": Type.INT,
    "op_limit":      Type.INT,
}
_BUILTIN_VARS = frozenset(_BUILTIN_TYPES)


def _type_name(t: Type) -> str:
    if not t:
        return "unknown"
    parts = []
    if Type.INT   in t: parts.append("int")
    if Type.FLOAT in t: parts.append("float")
    if Type.DIR   in t: parts.append("direction")
    if Type.LOC   in t: parts.append("location")
    if Type.LIST  in t: parts.append("list")
    return " | ".join(parts)


# ----------------------------------------------------------------------- diagnostics

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


# --------------------------------------------------------------------------- compiler

class Compiler:
    def __init__(
        self,
        persisted_funcs: dict[str, tuple[list[str], Type]] | None = None,
    ):
        """
        persisted_funcs maps function names defined in previous turns to
        (params, return_type).  Pass this in so the compiler can validate
        cross-turn call sites and argument counts.
        """
        self.errors:   list[CompileError]   = []
        self.warnings: list[CompileWarning] = []

        # name -> (params, return_type) — grows as we register new defs
        self._funcs: dict[str, tuple[list[str], Type]] = {}
        if persisted_funcs:
            self._funcs.update(persisted_funcs)

        # Set during check() — reset per scope
        self._var_types:  dict[str, Type] = {}
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
                self._funcs[s.name] = (s.params, Type(0))

        # Pass 2 — fixed-point to determine each function's return type.
        # Repeats until no function's return type grows; handles mutual calls.
        changed = True
        while changed:
            changed = False
            for fd in func_defs:
                param_types = {p: ANY for p in fd.params}
                body_types  = self._compute_var_types(fd.body, param_types)
                ret_type    = self._func_return_type(fd.body, body_types)
                params, old = self._funcs[fd.name]
                new = old | ret_type
                if new != old:
                    self._funcs[fd.name] = (params, new)
                    changed = True

        # Pass 3 — compute type for every global variable.
        global_types = self._compute_var_types(program.stmts, {})

        # Pass 4 — full semantic walk.
        self._var_types   = global_types
        self._in_function = False
        for s in program.stmts:
            self._check_stmt(s)

        return self.errors, self.warnings

    # --------------------------------------------------------- error / warning

    def _error(self, msg: str, line: int, col: int) -> None:
        self.errors.append(CompileError(msg, line, col))

    def _warn(self, msg: str, line: int, col: int) -> None:
        self.warnings.append(CompileWarning(msg, line, col))

    def _check_type(
        self,
        actual: Type,
        required: Type,
        context: str,
        line: int,
        col: int,
    ) -> None:
        """
        Error   — actual and required have no overlap (guaranteed wrong).
        Warning — actual partially overlaps required (possibly wrong).
        Clean   — actual is fully contained within required (guaranteed right).
        Type(0) or ANY means we have no useful type information; skip silently.
        """
        if not actual or actual == ANY:
            return
        overlap = actual & required
        if not overlap:
            self._error(
                f"{context}: expected {_type_name(required)}, got {_type_name(actual)}",
                line, col,
            )
        elif actual & ~required:
            self._warn(
                f"{context}: expected {_type_name(required)},"
                f" but value might be {_type_name(actual & ~required)}",
                line, col,
            )

    # --------------------------------------------------- type inference

    def _type_of(self, expr, var_types: dict[str, Type]) -> Type:
        """Compute the static type of expr. Pure — no side effects."""
        if isinstance(expr, IntLit):
            return Type.INT
        if isinstance(expr, FloatLit):
            return Type.FLOAT
        if isinstance(expr, Constant):
            return Type.LOC if expr.value == "HERE" else Type.DIR
        if isinstance(expr, ListConstructor):
            return Type.LIST
        if isinstance(expr, VarRef):
            if expr.name in _BUILTIN_TYPES:
                return _BUILTIN_TYPES[expr.name]
            return var_types.get(expr.name, ANY)
        if isinstance(expr, BinOp):
            if expr.op == TokenType.SLASH:
                return Type.FLOAT          # / always produces float
            if expr.op == TokenType.PERCENT:
                return Type.INT            # % always produces int
            if expr.op in _COMPARISON_OPS or expr.op in (TokenType.AND, TokenType.OR):
                return Type.INT
            # PLUS, MINUS, STAR: numeric parts of each operand union
            left  = self._type_of(expr.left,  var_types) & NUMERIC
            right = self._type_of(expr.right, var_types) & NUMERIC
            result = left | right
            return result if result else NUMERIC  # fallback when operands aren't numeric
        if isinstance(expr, UnaryOp):
            if expr.op == TokenType.NOT:
                return Type.INT
            if expr.op == TokenType.MINUS:
                t = self._type_of(expr.operand, var_types) & NUMERIC
                return t if t else NUMERIC
        if isinstance(expr, (Min, Max)):
            left  = self._type_of(expr.left,  var_types) & NUMERIC
            right = self._type_of(expr.right, var_types) & NUMERIC
            result = left | right
            return result if result else NUMERIC
        if isinstance(expr, (GetFriction, MyPaint, OppPaint, HasAgent)):
            return Type.INT
        if isinstance(expr, (Move, Paint)):
            return Type.INT
        if isinstance(expr, Length):
            return Type.INT
        if isinstance(expr, (Push, Pop, Index)):
            return ANY  # element type unknown
        if isinstance(expr, Call):
            _, ret_type = self._funcs.get(expr.name, ([], Type(0)))
            return ret_type if ret_type else ANY
        return ANY

    def _for_var_type(self, iterable, var_types: dict[str, Type]) -> Type:
        """Return the element type produced by iterating over iterable."""
        if isinstance(iterable, RangeExpr):
            return Type.INT
        if isinstance(iterable, VarRef):
            if iterable.name == "directions":
                return Type.DIR
            if iterable.name == "locations":
                return Type.LOC
        return ANY

    def _collect_assigns(
        self,
        stmts: list,
        assigns: dict[str, list],
        for_vars: dict[str, list],
    ) -> None:
        """
        Populate:
          assigns[name]  = [value_expr, ...]  for every $name = ... assignment
          for_vars[name] = [iterable_expr, ...] for every for $name in ... (non-range)
        Range for-loop variables are treated as integer assignments via a sentinel.
        Does NOT descend into FuncDef bodies.
        """
        for s in stmts:
            if isinstance(s, Assign):
                assigns.setdefault(s.name, []).append(s.value)
            elif isinstance(s, For):
                if isinstance(s.iterable, RangeExpr):
                    assigns.setdefault(s.var, []).append(IntLit(0))  # range yields INT
                else:
                    for_vars.setdefault(s.var, []).append(s.iterable)
                self._collect_assigns(s.body, assigns, for_vars)
            elif isinstance(s, If):
                for _, body in s.branches:
                    self._collect_assigns(body, assigns, for_vars)
                if s.else_body:
                    self._collect_assigns(s.else_body, assigns, for_vars)
            elif isinstance(s, While):
                self._collect_assigns(s.body, assigns, for_vars)

    def _compute_var_types(
        self, stmts: list, initial: dict[str, Type]
    ) -> dict[str, Type]:
        """
        Infer the type of every variable assigned in stmts.
        initial pre-seeds names (e.g. function parameters).
        Uses fixed-point iteration so mutually-dependent variables converge.
        """
        assigns:  dict[str, list] = {}
        for_vars: dict[str, list] = {}
        self._collect_assigns(stmts, assigns, for_vars)

        types: dict[str, Type] = dict(initial)
        for name in assigns:
            types.setdefault(name, Type(0))
        for name in for_vars:
            types.setdefault(name, Type(0))

        changed = True
        while changed:
            changed = False
            for name, exprs in assigns.items():
                for e in exprs:
                    new = types[name] | self._type_of(e, types)
                    if new != types[name]:
                        types[name] = new
                        changed = True
            for name, iterables in for_vars.items():
                for iterable in iterables:
                    new = types[name] | self._for_var_type(iterable, types)
                    if new != types[name]:
                        types[name] = new
                        changed = True

        return types

    def _func_return_type(self, body: list, var_types: dict[str, Type]) -> Type:
        """Union of all types that can be returned from body."""
        result = Type(0)
        for s in body:
            if isinstance(s, Return) and s.value is not None:
                result |= self._type_of(s.value, var_types)
            elif isinstance(s, If):
                for _, branch in s.branches:
                    result |= self._func_return_type(branch, var_types)
                if s.else_body:
                    result |= self._func_return_type(s.else_body, var_types)
            elif isinstance(s, (For, While)):
                result |= self._func_return_type(s.body, var_types)
        return result

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
                for arg, label in [
                    (r.start, "start"), (r.stop, "stop"), (r.step, "step")
                ]:
                    if arg is None:
                        continue
                    self._check_expr(arg)
                    self._check_type(
                        self._type_of(arg, self._var_types), Type.INT,
                        f"range() {label} argument", arg.line, arg.col,
                    )
            else:
                self._check_expr(s.iterable)
                self._check_type(
                    self._type_of(s.iterable, self._var_types), Type.LIST,
                    "for loop iterable", s.iterable.line, s.iterable.col,
                )
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
            outer_types   = self._var_types
            outer_in_func = self._in_function

            param_types       = {p: ANY for p in s.params}
            self._var_types   = self._compute_var_types(s.body, param_types)
            self._in_function = True

            for inner in s.body:
                self._check_stmt(inner)

            self._var_types   = outer_types
            self._in_function = outer_in_func

        # Halt — nothing to check

    # --------------------------------------------------- expression checking

    def _check_expr(self, expr) -> None:
        """Walk an expression, reporting type errors and warnings."""

        if isinstance(expr, VarRef):
            if expr.name not in _BUILTIN_TYPES and expr.name not in self._var_types:
                self._error(f"undefined variable '${expr.name}'", expr.line, expr.col)

        elif isinstance(expr, BinOp):
            self._check_expr(expr.left)
            self._check_expr(expr.right)
            if expr.op in (
                TokenType.PLUS, TokenType.MINUS, TokenType.STAR,
                TokenType.SLASH, TokenType.PERCENT,
            ):
                self._check_type(
                    self._type_of(expr.left, self._var_types), NUMERIC,
                    "arithmetic operand", expr.left.line, expr.left.col,
                )
                self._check_type(
                    self._type_of(expr.right, self._var_types), NUMERIC,
                    "arithmetic operand", expr.right.line, expr.right.col,
                )

        elif isinstance(expr, UnaryOp):
            self._check_expr(expr.operand)
            if expr.op == TokenType.MINUS:
                self._check_type(
                    self._type_of(expr.operand, self._var_types), NUMERIC,
                    "unary minus operand", expr.operand.line, expr.operand.col,
                )

        elif isinstance(expr, (Min, Max)):
            name = "min" if isinstance(expr, Min) else "max"
            self._check_expr(expr.left)
            self._check_expr(expr.right)
            self._check_type(
                self._type_of(expr.left, self._var_types), NUMERIC,
                f"{name}() argument", expr.left.line, expr.left.col,
            )
            self._check_type(
                self._type_of(expr.right, self._var_types), NUMERIC,
                f"{name}() argument", expr.right.line, expr.right.col,
            )

        elif isinstance(expr, Move):
            self._check_expr(expr.dir)
            self._check_type(
                self._type_of(expr.dir, self._var_types), Type.DIR,
                "move() argument", expr.dir.line, expr.dir.col,
            )

        elif isinstance(expr, HasAgent):
            self._check_expr(expr.dir)
            self._check_type(
                self._type_of(expr.dir, self._var_types), Type.DIR,
                "has_agent() argument", expr.dir.line, expr.dir.col,
            )

        elif isinstance(expr, Paint):
            self._check_expr(expr.num)
            self._check_type(
                self._type_of(expr.num, self._var_types), Type.INT,
                "paint() argument", expr.num.line, expr.num.col,
            )

        elif isinstance(expr, GetFriction):
            self._check_expr(expr.loc)
            self._check_type(
                self._type_of(expr.loc, self._var_types), LOCATION,
                "get_friction() argument", expr.loc.line, expr.loc.col,
            )

        elif isinstance(expr, MyPaint):
            self._check_expr(expr.loc)
            self._check_type(
                self._type_of(expr.loc, self._var_types), LOCATION,
                "my_paint() argument", expr.loc.line, expr.loc.col,
            )

        elif isinstance(expr, OppPaint):
            self._check_expr(expr.loc)
            self._check_type(
                self._type_of(expr.loc, self._var_types), LOCATION,
                "opp_paint() argument", expr.loc.line, expr.loc.col,
            )

        elif isinstance(expr, Push):
            self._check_expr(expr.lst)
            self._check_expr(expr.value)
            self._check_type(
                self._type_of(expr.lst, self._var_types), Type.LIST,
                "push() list argument", expr.lst.line, expr.lst.col,
            )
            if expr.pos is not None:
                self._check_expr(expr.pos)
                self._check_type(
                    self._type_of(expr.pos, self._var_types), Type.INT,
                    "push() position argument", expr.pos.line, expr.pos.col,
                )

        elif isinstance(expr, Pop):
            self._check_expr(expr.lst)
            self._check_type(
                self._type_of(expr.lst, self._var_types), Type.LIST,
                "pop() list argument", expr.lst.line, expr.lst.col,
            )
            if expr.pos is not None:
                self._check_expr(expr.pos)
                self._check_type(
                    self._type_of(expr.pos, self._var_types), Type.INT,
                    "pop() position argument", expr.pos.line, expr.pos.col,
                )

        elif isinstance(expr, Index):
            self._check_expr(expr.lst)
            self._check_type(
                self._type_of(expr.lst, self._var_types), Type.LIST,
                "index() list argument", expr.lst.line, expr.lst.col,
            )
            if expr.pos is not None:
                self._check_expr(expr.pos)
                self._check_type(
                    self._type_of(expr.pos, self._var_types), Type.INT,
                    "index() position argument", expr.pos.line, expr.pos.col,
                )

        elif isinstance(expr, Length):
            self._check_expr(expr.lst)
            self._check_type(
                self._type_of(expr.lst, self._var_types), Type.LIST,
                "length() argument", expr.lst.line, expr.lst.col,
            )

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
    persisted_funcs: dict[str, tuple[list[str], Type]] | None = None,
) -> tuple[list[CompileError], list[CompileWarning]]:
    """Convenience wrapper: check a parsed program and return (errors, warnings)."""
    return Compiler(persisted_funcs).check(program)
