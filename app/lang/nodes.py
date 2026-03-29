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

@dataclass
class ExprStmt:
    expr: Expr

@dataclass
class If:
    branches:  list[tuple[Expr, list[Stmt]]]  # (condition, body) for if + each elif
    else_body: list[Stmt] | None

@dataclass
class For:
    var:      str
    iterable: Expr        # RangeExpr or any list-valued expression
    body:     list[Stmt]

@dataclass
class While:
    cond: Expr
    body: list[Stmt]

@dataclass
class Halt:
    pass

@dataclass
class Return:
    value: Expr | None    # None means bare `return`, which returns 0

@dataclass
class FuncDef:
    name:   str
    params: list[str]
    body:   list[Stmt]


# ----------------------------------------------------------------- expressions

@dataclass
class BinOp:
    op:    TokenType
    left:  Expr
    right: Expr

@dataclass
class UnaryOp:
    op:      TokenType
    operand: Expr

@dataclass
class VarRef:
    name: str

@dataclass
class IntLit:
    value: int

@dataclass
class FloatLit:
    value: float

@dataclass
class Constant:
    """Direction or location constant: UP, DOWN, LEFT, RIGHT, HERE."""
    value: str

@dataclass
class Call:
    """User-defined function call via the `call` keyword."""
    name: str
    args: list[Expr]

@dataclass
class Min:
    left:  Expr
    right: Expr

@dataclass
class Max:
    left:  Expr
    right: Expr

@dataclass
class RangeExpr:
    start: Expr | None
    stop:  Expr
    step:  Expr | None

@dataclass
class Push:
    lst:   Expr
    value: Expr
    pos:   Expr | None

@dataclass
class Pop:
    lst: Expr
    pos: Expr | None

@dataclass
class Index:
    lst: Expr
    pos: Expr | None

@dataclass
class Length:
    lst: Expr

@dataclass
class ListConstructor:
    pass


# ------------------------------------------------------------ board operations

@dataclass
class Move:
    dir: Expr

@dataclass
class Paint:
    num: Expr

@dataclass
class GetFriction:
    loc: Expr

@dataclass
class HasAgent:
    dir: Expr

@dataclass
class MyPaint:
    loc: Expr

@dataclass
class OppPaint:
    loc: Expr
