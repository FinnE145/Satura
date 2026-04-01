import time
import pytest
from unittest.mock import patch

from app.game.board import Board, Cell
from app.game.agent import Agent
from app.game.engine import (
    Engine,
    ExecutionContext,
    CompileResult,
    HaltSignal,
    ResetSignal,
)
from app.lang.compiler import CompileError, CompileWarning


# ================================================================== CompileResult

class TestCompileResult:
    def test_ok_no_errors(self):
        r = CompileResult(program=object(), word_count=5, errors=[], warnings=[])
        assert r.ok is True

    def test_ok_with_errors(self):
        err = CompileError("oops", 1, 0)
        r = CompileResult(program=None, word_count=0, errors=[err], warnings=[])
        assert r.ok is False

    def test_ok_with_warnings_only(self):
        w = CompileWarning("hmm", 1, 0)
        r = CompileResult(program=object(), word_count=1, errors=[], warnings=[w])
        assert r.ok is True


# ================================================================== ExecutionContext helpers

def _make_ctx(player=1, op_limit=100, board=None, own_pos=(2, 2), opp_pos=(4, 4)):
    if board is None:
        board = Board(6)
    own = Agent(player, *own_pos)
    opp = Agent(3 - player, *opp_pos)
    return ExecutionContext(player, op_limit, board, own, opp), board, own, opp


# ================================================================== ExecutionContext._deduct

class TestDeduct:
    def test_deducts_cost(self):
        ctx, *_ = _make_ctx(op_limit=10)
        ctx._deduct(3)
        assert ctx.ops_remaining == 7

    def test_deduct_exact_budget(self):
        ctx, *_ = _make_ctx(op_limit=5)
        ctx._deduct(5)
        assert ctx.ops_remaining == 0

    def test_deduct_over_budget_raises_reset(self):
        ctx, *_ = _make_ctx(op_limit=3)
        with pytest.raises(ResetSignal):
            ctx._deduct(4)


# ================================================================== ExecutionContext.board_move

class TestBoardMove:
    def test_move_updates_agent(self):
        ctx, _, own, _ = _make_ctx()
        ctx.board_move("RIGHT")
        assert (own.row, own.col) == (2, 3)

    def test_move_deducts_ops(self):
        ctx, *_ = _make_ctx(op_limit=50)
        ctx.board_move("RIGHT")
        assert ctx.ops_remaining == 49  # blank cell costs 1

    def test_move_out_of_bounds_raises_halt(self):
        ctx, _, own, _ = _make_ctx(own_pos=(0, 0))
        with pytest.raises(HaltSignal):
            ctx.board_move("UP")

    def test_move_out_of_bounds_no_position_change(self):
        ctx, _, own, _ = _make_ctx(own_pos=(0, 0))
        with pytest.raises(HaltSignal):
            ctx.board_move("UP")
        assert (own.row, own.col) == (0, 0)

    def test_move_collision_raises_reset(self):
        ctx, _, own, opp = _make_ctx(own_pos=(2, 2), opp_pos=(2, 3))
        with pytest.raises(ResetSignal):
            ctx.board_move("RIGHT")

    def test_move_over_budget_raises_reset(self):
        ctx, board, own, opp = _make_ctx(op_limit=1, own_pos=(2, 2), opp_pos=(4, 4))
        # Black cell costs 20; budget is 1
        board.grid[2][3].p1 = 5
        board.grid[2][3].p2 = 5
        with pytest.raises(ResetSignal):
            ctx.board_move("RIGHT")


# ================================================================== ExecutionContext.board_paint

class TestBoardPaint:
    def test_paint_applies(self):
        ctx, board, own, _ = _make_ctx()
        ctx.board_paint(2)
        assert board.cell(2, 2).p1 == 2

    def test_paint_deducts_ops(self):
        ctx, *_ = _make_ctx(op_limit=100)
        ctx.board_paint(3)
        assert ctx.ops_remaining == 94  # 2 * 3 = 6

    def test_paint_zero_raises_halt(self):
        ctx, *_ = _make_ctx()
        with pytest.raises(HaltSignal):
            ctx.board_paint(0)

    def test_paint_negative_raises_halt(self):
        ctx, *_ = _make_ctx()
        with pytest.raises(HaltSignal):
            ctx.board_paint(-1)

    def test_paint_black_cell_raises_reset(self):
        ctx, board, own, _ = _make_ctx(own_pos=(2, 2))
        board.grid[2][2].p1 = 5
        board.grid[2][2].p2 = 5
        with pytest.raises(ResetSignal):
            ctx.board_paint(1)

    def test_paint_overflow_raises_reset(self):
        ctx, board, own, _ = _make_ctx(own_pos=(2, 2))
        board.grid[2][2].p1 = 5
        with pytest.raises(ResetSignal):
            ctx.board_paint(1)

    def test_paint_over_budget_raises_reset(self):
        ctx, *_ = _make_ctx(op_limit=3)
        with pytest.raises(ResetSignal):
            ctx.board_paint(2)  # costs 4

    def test_paint_p2_player(self):
        ctx, board, own, _ = _make_ctx(player=2)
        ctx.board_paint(1)
        assert board.cell(2, 2).p2 == 1


# ================================================================== ExecutionContext.board_get_friction

class TestBoardGetFriction:
    def test_blank_cell(self):
        ctx, *_ = _make_ctx()
        assert ctx.board_get_friction("HERE") == 1

    def test_deducts_one_op(self):
        ctx, *_ = _make_ctx(op_limit=10)
        ctx.board_get_friction("HERE")
        assert ctx.ops_remaining == 9

    def test_out_of_bounds_returns_null(self):
        ctx, _, own, _ = _make_ctx(own_pos=(0, 0))
        assert ctx.board_get_friction("UP") is None

    def test_painted_cell(self):
        ctx, board, own, _ = _make_ctx(own_pos=(2, 2))
        board.grid[2][3].p2 = 3  # opponent paint for player 1
        assert ctx.board_get_friction("RIGHT") == 6

    def test_black_cell(self):
        ctx, board, own, _ = _make_ctx(own_pos=(2, 2))
        board.grid[2][3].p1 = 5
        board.grid[2][3].p2 = 5
        assert ctx.board_get_friction("RIGHT") == 20


# ================================================================== ExecutionContext.board_has_agent

class TestBoardHasAgent:
    def test_opponent_present(self):
        ctx, *_ = _make_ctx(own_pos=(2, 2), opp_pos=(2, 3))
        assert ctx.board_has_agent("RIGHT") == 1

    def test_opponent_absent(self):
        ctx, *_ = _make_ctx(own_pos=(2, 2), opp_pos=(4, 4))
        assert ctx.board_has_agent("RIGHT") == 0

    def test_deducts_one_op(self):
        ctx, *_ = _make_ctx(op_limit=10)
        ctx.board_has_agent("HERE")
        assert ctx.ops_remaining == 9


# ================================================================== ExecutionContext.board_my_paint / board_opp_paint

class TestBoardPaintQueries:
    def test_my_paint_p1(self):
        ctx, board, own, _ = _make_ctx(player=1, own_pos=(2, 2))
        board.grid[2][3].p1 = 4
        assert ctx.board_my_paint("RIGHT") == 4

    def test_my_paint_p2(self):
        ctx, board, own, _ = _make_ctx(player=2, own_pos=(2, 2))
        board.grid[2][3].p2 = 3
        assert ctx.board_my_paint("RIGHT") == 3

    def test_opp_paint_p1_perspective(self):
        ctx, board, own, _ = _make_ctx(player=1, own_pos=(2, 2))
        board.grid[2][3].p2 = 2
        assert ctx.board_opp_paint("RIGHT") == 2

    def test_opp_paint_p2_perspective(self):
        ctx, board, own, _ = _make_ctx(player=2, own_pos=(2, 2))
        board.grid[2][3].p1 = 5
        assert ctx.board_opp_paint("RIGHT") == 5

    def test_my_paint_out_of_bounds_returns_null(self):
        ctx, *_ = _make_ctx(own_pos=(0, 0))
        assert ctx.board_my_paint("UP") is None

    def test_opp_paint_out_of_bounds_returns_null(self):
        ctx, *_ = _make_ctx(own_pos=(0, 0))
        assert ctx.board_opp_paint("UP") is None

    def test_my_paint_deducts_op(self):
        ctx, *_ = _make_ctx(op_limit=10)
        ctx.board_my_paint("HERE")
        assert ctx.ops_remaining == 9

    def test_opp_paint_deducts_op(self):
        ctx, *_ = _make_ctx(op_limit=10)
        ctx.board_opp_paint("HERE")
        assert ctx.ops_remaining == 9


# ================================================================== Engine init

class TestEngineInit:
    def test_board_size(self):
        e = Engine(size=8, op_limit=100, clock_seconds=60.0)
        assert e.board.size == 8

    def test_agent_positions(self):
        e = Engine(size=8, op_limit=100, clock_seconds=60.0)
        assert e.agents[1].row == 2 and e.agents[1].col == 2   # 8//4 = 2
        assert e.agents[2].row == 6 and e.agents[2].col == 6   # 3*8//4 = 6

    def test_op_limit(self):
        e = Engine(size=8, op_limit=200, clock_seconds=60.0)
        assert e.op_limit == 200

    def test_word_bank_starts_zero(self):
        e = Engine(size=8, op_limit=100, clock_seconds=60.0)
        assert e.word_bank(1) == 0.0
        assert e.word_bank(2) == 0.0


# ================================================================== Engine clock

class TestEngineClock:
    def test_clock_not_running_initially(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        assert e._clock_tick[1] is None

    def test_resume_sets_tick(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e.resume_clock(1)
        assert e._clock_tick[1] is not None

    def test_pause_clears_tick(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e.resume_clock(1)
        e.pause_clock(1)
        assert e._clock_tick[1] is None

    def test_clock_remaining_decreases_while_running(self):
        e = Engine(size=4, op_limit=50, clock_seconds=10.0)
        t0 = 1000.0
        with patch("time.monotonic", side_effect=[t0, t0 + 2.0]):
            e.resume_clock(1)
            remaining = e.clock_remaining(1)
        assert abs(remaining - 8.0) < 0.01

    def test_pause_deducts_elapsed(self):
        e = Engine(size=4, op_limit=50, clock_seconds=10.0)
        with patch("time.monotonic", side_effect=[1000.0, 1003.0]):
            e.resume_clock(1)
            e.pause_clock(1)
        assert abs(e._clock_remaining[1] - 7.0) < 0.01

    def test_clock_does_not_go_below_zero(self):
        e = Engine(size=4, op_limit=50, clock_seconds=1.0)
        with patch("time.monotonic", side_effect=[1000.0, 1100.0]):
            e.resume_clock(1)
            e.pause_clock(1)
        assert e._clock_remaining[1] == 0.0

    def test_clock_expired_true(self):
        e = Engine(size=4, op_limit=50, clock_seconds=0.0)
        assert e.clock_expired(1) is True

    def test_clock_expired_false(self):
        e = Engine(size=4, op_limit=50, clock_seconds=60.0)
        assert e.clock_expired(1) is False

    def test_resume_idempotent(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e.resume_clock(1)
        tick = e._clock_tick[1]
        e.resume_clock(1)  # second call should not change the tick
        assert e._clock_tick[1] == tick

    def test_pause_idempotent(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e.pause_clock(1)  # already paused — should not crash
        assert e._clock_remaining[1] == 30.0


# ================================================================== Engine word bank

class TestEngineWordBank:
    def test_bank_starts_at_zero(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        assert e.word_bank(1) == 0.0

    def test_accumulates_while_running(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0, word_rate=2.0)
        t0 = 500.0
        with patch("time.monotonic", side_effect=[t0, t0 + 3.0]):
            e.resume_word_accumulation(1)
            bank = e.word_bank(1)
        assert abs(bank - 6.0) < 0.01

    def test_pause_flushes_to_bank(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0, word_rate=1.0)
        with patch("time.monotonic", side_effect=[500.0, 505.0]):
            e.resume_word_accumulation(1)
            e.pause_word_accumulation(1)
        assert abs(e._word_bank[1] - 5.0) < 0.01

    def test_spend_words_success(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e._word_bank[1] = 10.0
        assert e.spend_words(1, 4) is True
        assert abs(e.word_bank(1) - 6.0) < 0.01

    def test_spend_words_insufficient(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e._word_bank[1] = 2.0
        assert e.spend_words(1, 5) is False
        assert abs(e._word_bank[1] - 2.0) < 0.01  # unchanged

    def test_spend_words_exact(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e._word_bank[1] = 5.0
        assert e.spend_words(1, 5) is True
        assert abs(e.word_bank(1) - 0.0) < 0.01

    def test_resume_idempotent(self):
        e = Engine(size=4, op_limit=50, clock_seconds=30.0)
        e.resume_word_accumulation(1)
        tick = e._word_tick[1]
        e.resume_word_accumulation(1)
        assert e._word_tick[1] == tick


# ================================================================== Engine.compile

class TestEngineCompile:
    def setup_method(self):
        self.e = Engine(size=6, op_limit=100, clock_seconds=60.0)

    def test_valid_script_ok(self):
        result = self.e.compile("$x = 1")
        assert result.ok is True
        assert result.program is not None

    def test_valid_script_word_count(self):
        result = self.e.compile("$x = 1")
        assert result.word_count > 0

    def test_lex_error_not_ok(self):
        result = self.e.compile("@@@")
        assert result.ok is False
        assert result.program is None

    def test_parse_error_not_ok(self):
        result = self.e.compile("if")
        assert result.ok is False

    def test_empty_script_ok(self):
        result = self.e.compile("")
        assert result.ok is True


# ================================================================== Engine.run_execution

class TestRunExecution:
    def setup_method(self):
        self.e = Engine(size=6, op_limit=200, clock_seconds=60.0)

    def _compiled(self):
        """Return a trivially valid compiled program."""
        result = self.e.compile("")
        assert result.ok
        return result.program

    def test_normal_outcome(self):
        outcome, _ = self.e.run_execution(1, self._compiled())
        assert outcome == "normal"

    def test_halt_outcome_via_engine_signal(self):
        with patch("app.lang.interpreter.execute", side_effect=HaltSignal("test halt")):
            outcome, _ = self.e.run_execution(1, self._compiled())
        assert outcome == "halt"

    def test_reset_outcome_via_engine_signal(self):
        with patch("app.lang.interpreter.execute", side_effect=ResetSignal("test reset")):
            outcome, _ = self.e.run_execution(1, self._compiled())
        assert outcome == "reset"

    def test_reset_rolls_back_board(self):
        e = self.e
        e.board.grid[1][1].p1 = 3

        def mutate_then_reset(program, ctx, funcs):
            e.board.grid[1][1].p1 = 0
            raise ResetSignal("test")

        with patch("app.lang.interpreter.execute", side_effect=mutate_then_reset):
            outcome, _ = e.run_execution(1, self._compiled())

        assert outcome == "reset"
        assert e.board.cell(1, 1).p1 == 3  # restored

    def test_reset_rolls_back_own_agent(self):
        e = self.e
        original_pos = e.agents[1].snapshot()

        def move_then_reset(program, ctx, funcs):
            e.agents[1].row = 0
            e.agents[1].col = 0
            raise ResetSignal("test")

        with patch("app.lang.interpreter.execute", side_effect=move_then_reset):
            outcome, _ = e.run_execution(1, self._compiled())

        assert outcome == "reset"
        assert e.agents[1].snapshot() == original_pos

    def test_halt_does_not_rollback_board(self):
        e = self.e

        def mutate_then_halt(program, ctx, funcs):
            e.board.grid[1][1].p1 = 4
            raise HaltSignal("test")

        with patch("app.lang.interpreter.execute", side_effect=mutate_then_halt):
            outcome, _ = e.run_execution(1, self._compiled())

        assert outcome == "halt"
        assert e.board.cell(1, 1).p1 == 4  # NOT rolled back


# ================================================================== Engine.check_winner

class TestCheckWinner:
    def test_no_winner_initially(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        assert e.check_winner() is None

    def test_p1_wins(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        # Dominate 60 out of 100 cells for player 1
        count = 0
        for r in range(10):
            for c in range(10):
                if count < 60:
                    e.board.grid[r][c].p1 = 1
                    count += 1
        assert e.check_winner() == 1

    def test_p2_wins(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        count = 0
        for r in range(10):
            for c in range(10):
                if count < 60:
                    e.board.grid[r][c].p2 = 1
                    count += 1
        assert e.check_winner() == 2

    def test_threshold_exactly_60_percent(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        # 60 / 100 = exactly 0.6 → should win
        count = 0
        for r in range(10):
            for c in range(10):
                if count < 60:
                    e.board.grid[r][c].p1 = 1
                    count += 1
        assert e.check_winner() == 1

    def test_just_below_threshold(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        count = 0
        for r in range(10):
            for c in range(10):
                if count < 59:
                    e.board.grid[r][c].p1 = 1
                    count += 1
        assert e.check_winner() is None


# ================================================================== Engine.check_stalemate

class TestCheckStalemate:
    def test_no_stalemate_empty_board(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        assert e.check_stalemate() is False

    def test_stalemate_too_many_black_cells(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        # Make 41 cells black → only 59 playable < 60% of 100
        count = 0
        for r in range(10):
            for c in range(10):
                if count < 41:
                    e.board.grid[r][c].p1 = 5
                    e.board.grid[r][c].p2 = 5
                    count += 1
        assert e.check_stalemate() is True

    def test_no_stalemate_exactly_at_boundary(self):
        e = Engine(size=10, op_limit=100, clock_seconds=60.0)
        # 40 black cells → 60 playable = exactly 60% → stalemate condition is false
        count = 0
        for r in range(10):
            for c in range(10):
                if count < 40:
                    e.board.grid[r][c].p1 = 5
                    e.board.grid[r][c].p2 = 5
                    count += 1
        assert e.check_stalemate() is False
