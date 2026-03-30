from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from .tokens import TokenType

# Type aliases — used in annotations below for readability.
# Python cannot enforce these at runtime.
Expr = Any
Stmt = Any


@dataclass
class Program:
    stmts: list[Stmt]


# ------------------------------------------------------------------ statements

@dataclass
class Assign:
    name:  str
    value: Expr
    line:  int = 0
    col:   int = 0

@dataclass
class ExprStmt:
    expr: Expr
    line: int = 0
    col:  int = 0

@dataclass
class If:
    branches:  list[tuple[Expr, list[Stmt]]]  # (condition, body) for if + each elif
    else_body: list[Stmt] | None
    line:      int = 0
    col:       int = 0

@dataclass
class For:
    var:      str
    iterable: Expr        # RangeExpr or any list-valued expression
    body:     list[Stmt]
    line:     int = 0
    col:      int = 0

@dataclass
class While:
    cond: Expr
    body: list[Stmt]
    line: int = 0
    col:  int = 0

@dataclass
class Halt:
    line: int = 0
    col:  int = 0

@dataclass
class Return:
    value: Expr | None    # None means bare `return`, which returns 0
    line:  int = 0
    col:   int = 0

@dataclass
class FuncDef:
    name:   str
    params: list[str]
    body:   list[Stmt]
    line:   int = 0
    col:    int = 0


# ----------------------------------------------------------------- expressions

@dataclass
class BinOp:
    op:    TokenType
    left:  Expr
    right: Expr
    line:  int = 0
    col:   int = 0

@dataclass
class UnaryOp:
    op:      TokenType
    operand: Expr
    line:    int = 0
    col:     int = 0

@dataclass
class VarRef:
    name: str
    line: int = 0
    col:  int = 0

@dataclass
class IntLit:
    value: int
    line:  int = 0
    col:   int = 0

@dataclass
class FloatLit:
    value: float
    line:  int = 0
    col:   int = 0

@dataclass
class Constant:
    """Direction or location constant: UP, DOWN, LEFT, RIGHT, HERE."""
    value: str
    line:  int = 0
    col:   int = 0

@dataclass
class Call:
    """User-defined function call via the `call` keyword."""
    name: str
    args: list[Expr]
    line: int = 0
    col:  int = 0

@dataclass
class Min:
    left:  Expr
    right: Expr
    line:  int = 0
    col:   int = 0

@dataclass
class Max:
    left:  Expr
    right: Expr
    line:  int = 0
    col:   int = 0

@dataclass
class RangeExpr:
    start: Expr | None
    stop:  Expr
    step:  Expr | None
    line:  int = 0
    col:   int = 0

@dataclass
class Push:
    lst:   Expr
    value: Expr
    pos:   Expr | None
    line:  int = 0
    col:   int = 0

@dataclass
class Pop:
    lst:  Expr
    pos:  Expr | None
    line: int = 0
    col:  int = 0

@dataclass
class Index:
    lst:  Expr
    pos:  Expr | None
    line: int = 0
    col:  int = 0

@dataclass
class Length:
    lst:  Expr
    line: int = 0
    col:  int = 0

@dataclass
class ListConstructor:
    line: int = 0
    col:  int = 0


# ------------------------------------------------------------ board operations

@dataclass
class Move:
    dir:  Expr
    line: int = 0
    col:  int = 0

@dataclass
class Paint:
    num:  Expr
    line: int = 0
    col:  int = 0

@dataclass
class GetFriction:
    loc:  Expr
    line: int = 0
    col:  int = 0

@dataclass
class HasAgent:
    dir:  Expr
    line: int = 0
    col:  int = 0

@dataclass
class MyPaint:
    loc:  Expr
    line: int = 0
    col:  int = 0

@dataclass
class OppPaint:
    loc:  Expr
    line: int = 0
    col:  int = 0
