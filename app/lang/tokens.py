from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Sigil / assignment
    DOLLAR       = auto()
    ASSIGN       = auto()

    # Literals
    INT_LIT      = auto()
    FLOAT_LIT    = auto()

    # Identifier
    IDENT        = auto()

    # Keywords — costly
    IF           = auto()
    ELIF         = auto()
    ELSE         = auto()
    FOR          = auto()
    WHILE        = auto()
    HALT         = auto()
    RETURN       = auto()
    DEF          = auto()
    CALL         = auto()
    AND          = auto()
    OR           = auto()
    NOT          = auto()
    MIN          = auto()
    MAX          = auto()
    RANGE        = auto()
    INDEX        = auto()
    LENGTH       = auto()
    PUSH         = auto()
    POP          = auto()

    # Keywords — free
    IN           = auto()
    LIST         = auto()

    # Board operations — costly
    MOVE         = auto()
    PAINT        = auto()
    GET_FRICTION = auto()
    HAS_AGENT    = auto()
    MY_PAINT     = auto()
    OPP_PAINT    = auto()

    # Direction / location constants — free
    UP           = auto()
    DOWN         = auto()
    LEFT         = auto()
    RIGHT        = auto()
    HERE         = auto()

    # Arithmetic operators — costly
    PLUS         = auto()
    MINUS        = auto()
    STAR         = auto()
    SLASH        = auto()
    PERCENT      = auto()

    # Comparison operators — costly
    EQ           = auto()
    NEQ          = auto()
    LT           = auto()
    GT           = auto()
    LTE          = auto()
    GTE          = auto()

    # Punctuation — free
    LPAREN       = auto()
    RPAREN       = auto()
    LBRACE       = auto()
    RBRACE       = auto()
    COMMA        = auto()
    SEMICOLON    = auto()

    # Control
    EOF          = auto()


@dataclass
class Token:
    type:  TokenType
    value: str
    line:  int
    col:   int


# Maps reserved words to their TokenType.
# The lexer uses this to distinguish keywords/constants from plain identifiers.
KEYWORDS: dict[str, TokenType] = {
    "if":           TokenType.IF,
    "elif":         TokenType.ELIF,
    "else":         TokenType.ELSE,
    "for":          TokenType.FOR,
    "while":        TokenType.WHILE,
    "halt":         TokenType.HALT,
    "return":       TokenType.RETURN,
    "def":          TokenType.DEF,
    "call":         TokenType.CALL,
    "and":          TokenType.AND,
    "or":           TokenType.OR,
    "not":          TokenType.NOT,
    "min":          TokenType.MIN,
    "max":          TokenType.MAX,
    "range":        TokenType.RANGE,
    "index":        TokenType.INDEX,
    "length":       TokenType.LENGTH,
    "push":         TokenType.PUSH,
    "pop":          TokenType.POP,
    "in":           TokenType.IN,
    "list":         TokenType.LIST,
    "move":         TokenType.MOVE,
    "paint":        TokenType.PAINT,
    "get_friction": TokenType.GET_FRICTION,
    "has_agent":    TokenType.HAS_AGENT,
    "my_paint":     TokenType.MY_PAINT,
    "opp_paint":    TokenType.OPP_PAINT,
    "UP":           TokenType.UP,
    "DOWN":         TokenType.DOWN,
    "LEFT":         TokenType.LEFT,
    "RIGHT":        TokenType.RIGHT,
    "HERE":         TokenType.HERE,
}


# Word cost per token type. Any type absent from this table costs 0.
WORD_COSTS: dict[TokenType, int] = {
    TokenType.DOLLAR:       1,
    TokenType.ASSIGN:       1,
    TokenType.IF:           1,
    TokenType.ELIF:         1,
    TokenType.ELSE:         1,
    TokenType.FOR:          1,
    TokenType.WHILE:        1,
    TokenType.HALT:         1,
    TokenType.RETURN:       1,
    TokenType.DEF:          1,
    TokenType.CALL:         1,
    TokenType.AND:          1,
    TokenType.OR:           1,
    TokenType.NOT:          1,
    TokenType.MIN:          1,
    TokenType.MAX:          1,
    TokenType.RANGE:        1,
    TokenType.INDEX:        1,
    TokenType.LENGTH:       1,
    TokenType.PUSH:         1,
    TokenType.POP:          1,
    TokenType.MOVE:         1,
    TokenType.PAINT:        1,
    TokenType.GET_FRICTION: 1,
    TokenType.HAS_AGENT:    1,
    TokenType.MY_PAINT:     1,
    TokenType.OPP_PAINT:    1,
    TokenType.PLUS:         1,
    TokenType.MINUS:        1,
    TokenType.STAR:         1,
    TokenType.SLASH:        1,
    TokenType.PERCENT:      1,
    TokenType.EQ:           1,
    TokenType.NEQ:          1,
    TokenType.LT:           1,
    TokenType.GT:           1,
    TokenType.LTE:          1,
    TokenType.GTE:          1,
}
