import time
from dataclasses import dataclass
from .board import Board, PaintBlackCell, PaintOverflow
from .agent import Agent, get_friction, MoveOutOfBounds, MoveCollision
from ..lang.tokens import WORD_COSTS
from ..lang.lexer import tokenize, LexError
from ..lang.parser import parse, ParseError
from ..lang.compiler import check, CompileError, CompileWarning
from ..lang.signals import HaltSignal, ResetSignal

_DELTAS: dict[str, tuple[int, int]] = {
    "HERE":  ( 0,  0),
    "UP":    (-1,  0),
    "DOWN":  ( 1,  0),
    "LEFT":  ( 0, -1),
    "RIGHT": ( 0,  1),
}


# ----------------------------------------------------------------------- compile result

@dataclass
class CompileResult:
    program: object               # nodes.Program, or None on error
    word_count: int
    errors: list[CompileError]
    warnings: list[CompileWarning]

    @property
    def ok(self) -> bool:
        return not self.errors


# ----------------------------------------------------------------------- context

class ExecutionContext:
    """
    Passed to the interpreter for a single script execution.
    Provides all board operations as methods, tracks op budget,
    and raises HaltSignal / ResetSignal as appropriate.
    """

    def __init__(
        self,
        player: int,
        op_limit: int,
        board: Board,
        own_agent: Agent,
        opp_agent: Agent,
    ):
        self.player = player
        self.op_limit = op_limit
        self.ops_remaining = op_limit
        self._board = board
        self._own = own_agent
        self._opp = opp_agent
        self._log: list[dict] = []

    # ------------------------------------------------------------ op accounting

    def _deduct(self, cost: int) -> None:
        if cost > self.ops_remaining:
            raise ResetSignal("op budget exceeded")
        self.ops_remaining -= cost

    # ------------------------------------------------------------ location util

    def _resolve(self, loc: str) -> tuple[int, int]:
        dr, dc = _DELTAS[loc]
        return self._own.row + dr, self._own.col + dc

    # ------------------------------------------------------------ board ops

    def board_move(self, direction: str) -> None:
        dr, dc = _DELTAS[direction]
        dest = (self._own.row + dr, self._own.col + dc)
        # agent.move() returns the op cost; raises MoveOutOfBounds or MoveCollision
        try:
            cost = self._own.move(direction, self._board, self._opp)
        except MoveOutOfBounds as e:
            raise HaltSignal(str(e)) from e
        except MoveCollision as e:
            raise ResetSignal(str(e)) from e
        # Deduct after move; if over budget, ResetSignal triggers full rollback
        self._deduct(cost)
        self._log.append({"op": "move", "to": dest})

    def board_paint(self, amount: int) -> None:
        if amount <= 0:
            raise HaltSignal(f"paint({amount}) is not a positive integer")
        at = (self._own.row, self._own.col)
        self._deduct(2 * amount)
        try:
            self._board.paint(self._own.row, self._own.col, self.player, amount)
        except PaintBlackCell as e:
            raise ResetSignal(str(e)) from e
        except PaintOverflow as e:
            raise ResetSignal(str(e)) from e
        self._log.append({"op": "paint", "at": at, "amount": amount})

    def board_get_friction(self, loc: str) -> int | None:
        self._deduct(1)
        r, c = self._resolve(loc)
        if not self._board.in_bounds(r, c):
            self._log.append({"op": "get_friction", "at": (r, c), "result": None})
            return None
        result = get_friction(self._board.cell(r, c), self.player)
        self._log.append({"op": "get_friction", "at": (r, c), "result": result})
        return result

    def board_has_agent(self, direction: str) -> int | None:
        self._deduct(1)
        r, c = self._resolve(direction)
        if not self._board.in_bounds(r, c):
            self._log.append({"op": "has_agent", "at": (r, c), "result": None})
            return None
        result = 1 if (self._opp.row == r and self._opp.col == c) else 0
        self._log.append({"op": "has_agent", "at": (r, c), "result": result})
        return result

    def board_my_paint(self, loc: str) -> int | None:
        self._deduct(1)
        r, c = self._resolve(loc)
        if not self._board.in_bounds(r, c):
            self._log.append({"op": "my_paint", "at": (r, c), "result": None})
            return None
        cell = self._board.cell(r, c)
        result = cell.p1 if self.player == 1 else cell.p2
        self._log.append({"op": "my_paint", "at": (r, c), "result": result})
        return result

    def board_opp_paint(self, loc: str) -> int | None:
        self._deduct(1)
        r, c = self._resolve(loc)
        if not self._board.in_bounds(r, c):
            self._log.append({"op": "opp_paint", "at": (r, c), "result": None})
            return None
        cell = self._board.cell(r, c)
        result = cell.p2 if self.player == 1 else cell.p1
        self._log.append({"op": "opp_paint", "at": (r, c), "result": result})
        return result


# --------------------------------------------------------------------------- engine

class Engine:
    def __init__(
        self,
        size: int,
        op_limit: int,
        clock_seconds: float,
        word_rate: float = 1.0,
    ):
        self.board = Board(size)
        self.agents: dict[int, Agent] = {
            1: Agent(1, size // 4,     size // 4),
            2: Agent(2, 3 * size // 4, 3 * size // 4),
        }
        self.op_limit = op_limit
        self.persisted_funcs: dict = {}

        self._word_rate = word_rate
        self._word_bank: dict[int, float] = {1: 0.0, 2: 0.0}
        # When not None, words are actively accumulating for that player
        self._word_tick: dict[int, float | None] = {1: None, 2: None}

        self._clock_remaining: dict[int, float] = {1: clock_seconds, 2: clock_seconds}
        # When not None, the clock is running for that player
        self._clock_tick: dict[int, float | None] = {1: None, 2: None}

    # ------------------------------------------------------------------- clock

    def resume_clock(self, player: int) -> None:
        if self._clock_tick[player] is None:
            self._clock_tick[player] = time.monotonic()

    def pause_clock(self, player: int) -> None:
        if self._clock_tick[player] is not None:
            elapsed = time.monotonic() - self._clock_tick[player]
            self._clock_remaining[player] = max(0.0, self._clock_remaining[player] - elapsed)
            self._clock_tick[player] = None

    def clock_remaining(self, player: int) -> float:
        remaining = self._clock_remaining[player]
        if self._clock_tick[player] is not None:
            elapsed = time.monotonic() - self._clock_tick[player]
            remaining = max(0.0, remaining - elapsed)
        return remaining

    def clock_expired(self, player: int) -> bool:
        return self.clock_remaining(player) <= 0.0

    # ---------------------------------------------------------------- word bank

    def resume_word_accumulation(self, player: int) -> None:
        """Begin accumulating words for `player`. Called when their exec phase ends."""
        if self._word_tick[player] is None:
            self._word_tick[player] = time.monotonic()

    def pause_word_accumulation(self, player: int) -> None:
        if self._word_tick[player] is not None:
            elapsed = time.monotonic() - self._word_tick[player]
            self._word_bank[player] += elapsed * self._word_rate
            self._word_tick[player] = None

    def word_bank(self, player: int) -> float:
        bank = self._word_bank[player]
        if self._word_tick[player] is not None:
            bank += (time.monotonic() - self._word_tick[player]) * self._word_rate
        return bank

    def spend_words(self, player: int, word_count: int) -> bool:
        """
        Deduct `word_count` words. Returns False if the bank is insufficient,
        in which case the script must not be deployed.
        """
        current = self.word_bank(player)
        if current < word_count:
            return False
        # Flush accumulated words, then deduct
        self.pause_word_accumulation(player)
        self._word_bank[player] -= word_count
        self.resume_word_accumulation(player)
        return True

    # ---------------------------------------------------------------- compilation

    def compile(self, source: str) -> CompileResult:
        """
        Run the full lex → parse → check pipeline.
        Returns a CompileResult; execution should only proceed if result.ok is True.
        """
        try:
            tokens = tokenize(source)
        except LexError as e:
            err = CompileError(str(e), getattr(e, "line", 0), getattr(e, "col", 0))
            return CompileResult(program=None, word_count=0, errors=[err], warnings=[])

        word_count = sum(WORD_COSTS.get(t.type, 0) for t in tokens)

        try:
            program = parse(tokens)
        except ParseError as e:
            err = CompileError(str(e), getattr(e, "line", 0), getattr(e, "col", 0))
            return CompileResult(program=None, word_count=word_count, errors=[err], warnings=[])

        errors, warnings = check(program, self.persisted_funcs)
        return CompileResult(program=program, word_count=word_count, errors=errors, warnings=warnings)

    # ---------------------------------------------------------------- execution

    def run_execution(self, player: int, program) -> tuple[str, list[dict]]:
        """
        Execute a compiled program for `player`.
        Returns (outcome, log) where outcome is "normal", "halt", or "reset"
        and log is a list of realized board operations (empty on reset).

        Assumes the script has already been compiled (result.ok) and words spent.
        """
        from ..lang.interpreter import execute  # deferred to avoid circular import

        own = self.agents[player]
        opp = self.agents[3 - player]

        board_snap = self.board.snapshot()
        own_snap   = own.snapshot()
        opp_snap   = opp.snapshot()

        ctx = ExecutionContext(player, self.op_limit, self.board, own, opp)

        outcome = "normal"
        try:
            execute(program, ctx, self.persisted_funcs)
        except HaltSignal:
            outcome = "halt"
        except ResetSignal:
            outcome = "reset"
            self.board.restore(board_snap)
            own.restore(own_snap)
            opp.restore(opp_snap)

        return outcome, ctx._log

    # --------------------------------------------------------- win / stalemate

    def check_winner(self) -> int | None:
        """
        Returns 1, 2, or None.
        Default rule: first to dominate >= 60% of total cells.
        """
        p1, p2, _black, total = self.board.territory()
        threshold = total * 0.6
        if p1 >= threshold:
            return 1
        if p2 >= threshold:
            return 2
        return None

    def check_stalemate(self) -> bool:
        """True when neither player can mathematically reach the 60% win threshold."""
        total = self.board.size * self.board.size
        threshold = total * 0.6
        p1_maxed = sum(c.p1 == 5 for row in self.board.grid for c in row)
        p2_maxed = sum(c.p2 == 5 for row in self.board.grid for c in row)
        return (total - p2_maxed) < threshold and (total - p1_maxed) < threshold
