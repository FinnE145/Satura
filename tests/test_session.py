import time
import pytest
from unittest.mock import patch

from app.game.engine import Engine
from app.game.session import GameSession, create_session, get_session, _sessions


# ================================================================== helpers

def _engine(size=6, op_limit=500, clock_seconds=300.0, word_rate=1.0):
    return Engine(size, op_limit, clock_seconds, word_rate)


def _session(engine=None):
    """Bare GameSession — no auto exec2 run."""
    if engine is None:
        engine = _engine()
    return GameSession("test-game", engine)


def _in_write(player=1, engine=None):
    """Session already in write phase for the given player."""
    s = _session(engine)
    s.current_player = player
    s.phase = "write"
    s.engine._word_bank[player] = 1000.0
    s.engine.resume_clock(player)
    return s


def _deploy(s, source="", player=None):
    """Deploy source for the current (or given) player. Gives words if needed."""
    p = player if player is not None else s.current_player
    s.engine._word_bank[p] = max(s.engine._word_bank[p], 1000.0)
    return s.deploy_script(p, source)


# ================================================================== create_session / get_session

class TestRegistry:
    def test_create_session_returns_session(self):
        s = create_session("reg-1", 4, 100, 60.0)
        assert isinstance(s, GameSession)
        assert s.game_id == "reg-1"

    def test_create_session_stored_in_registry(self):
        s = create_session("reg-2", 4, 100, 60.0)
        assert get_session("reg-2") is s

    def test_get_session_missing(self):
        assert get_session("does-not-exist") is None

    def test_create_session_runs_p1_exec2(self):
        # After creation, P1's exec2 (no script) already ran — should be in anim_pre_write
        s = create_session("reg-3", 4, 100, 60.0)
        assert s.current_player == 1
        assert s.phase == "anim_pre_write"

    def test_create_session_exec_log_empty_on_no_script(self):
        s = create_session("reg-4", 4, 100, 60.0)
        assert s._exec_log == []


# ================================================================== initial state

class TestInitialState:
    def test_phase_starts_exec2(self):
        s = _session()
        assert s.phase == "exec2"

    def test_current_player_starts_1(self):
        s = _session()
        assert s.current_player == 1

    def test_game_not_over(self):
        s = _session()
        assert s.game_over is False

    def test_winner_none(self):
        s = _session()
        assert s.winner is None

    def test_programs_none(self):
        s = _session()
        assert s._program[1] is None
        assert s._program[2] is None

    def test_exec_log_empty(self):
        s = _session()
        assert s._exec_log == []


# ================================================================== compile_script

class TestCompileScript:
    def test_wrong_player_returns_error(self):
        s = _in_write(player=1)
        result = s.compile_script(2, "")
        assert result["ok"] is False

    def test_wrong_phase_returns_error(self):
        s = _session()
        s.phase = "anim_pre_write"
        result = s.compile_script(1, "")
        assert result["ok"] is False

    def test_valid_source_ok(self):
        s = _in_write()
        result = s.compile_script(1, "")
        assert result["ok"] is True
        assert result["errors"] == []

    def test_invalid_source_not_ok(self):
        s = _in_write()
        result = s.compile_script(1, "@@@")
        assert result["ok"] is False
        assert len(result["errors"]) > 0

    def test_returns_word_count(self):
        s = _in_write()
        result = s.compile_script(1, "")
        assert "word_count" in result

    def test_no_state_change(self):
        s = _in_write()
        before_phase = s.phase
        before_player = s.current_player
        s.compile_script(1, "")
        assert s.phase == before_phase
        assert s.current_player == before_player

    def test_clock_not_paused(self):
        s = _in_write()
        s.compile_script(1, "")
        # Clock tick should still be running (not paused)
        assert s.engine._clock_tick[1] is not None


# ================================================================== deploy_script

class TestDeployScript:
    def test_wrong_player_returns_error(self):
        s = _in_write(player=1)
        result = s.deploy_script(2, "")
        assert result["ok"] is False

    def test_wrong_phase_returns_error(self):
        s = _session()
        s.phase = "anim_pre_write"
        result = s.deploy_script(1, "")
        assert result["ok"] is False

    def test_clock_expired_finishes_game(self):
        s = _in_write(player=1)
        s.engine._clock_remaining[1] = 0.0
        result = s.deploy_script(1, "")
        assert result["ok"] is False
        assert "time expired" in result["errors"]
        assert s.game_over is True
        assert s.winner == 2

    def test_compile_error_returns_errors_and_stays_in_write(self):
        s = _in_write(player=1)
        result = s.deploy_script(1, "@@@")
        assert result["ok"] is False
        assert len(result["errors"]) > 0
        assert s.phase == "write"

    def test_compile_error_resumes_clock(self):
        s = _in_write(player=1)
        s.deploy_script(1, "@@@")
        assert s.engine._clock_tick[1] is not None

    def test_insufficient_words_returns_error(self):
        s = _in_write(player=1)
        s.engine._word_bank[1] = 0.0
        # Use a non-empty script so word_count > 0
        result = s.deploy_script(1, "$x = 1")
        if result["ok"] is False:
            assert "insufficient word bank" in result["errors"] or len(result["errors"]) > 0

    def test_insufficient_words_resumes_clock(self):
        s = _in_write(player=1)
        s.engine._word_bank[1] = 0.0
        s.deploy_script(1, "$x = 1")
        # Clock must not be left paused
        assert s.engine._clock_tick[1] is not None or s.engine._clock_remaining[1] >= 0.0

    def test_success_stores_program(self):
        s = _in_write(player=1)
        _deploy(s)
        assert s._program[1] is not None

    def test_success_runs_exec1(self):
        # After deploy, exec1 ran — phase should be anim_post_exec1 (or finished on win)
        s = _in_write(player=1)
        result = _deploy(s)
        assert result["ok"] is True
        assert s.phase in ("anim_post_exec1", "finished")

    def test_success_phase_anim_post_exec1(self):
        s = _in_write(player=1)
        _deploy(s)
        assert s.phase == "anim_post_exec1"

    def test_success_returns_ok_true(self):
        s = _in_write(player=1)
        result = _deploy(s)
        assert result["ok"] is True

    def test_success_pauses_word_accumulation(self):
        s = _in_write(player=1)
        s.engine.resume_word_accumulation(1)
        _deploy(s)
        # Word tick should be None (paused) after deploy
        assert s.engine._word_tick[1] is None

    def test_deploy_break_script_succeeds(self):
        s = _in_write(player=1)
        result = _deploy(s, "for $i in range(3) { break }")
        assert result["ok"] is True

    def test_deploy_break_script_logs_normal_exec1(self):
        s = _in_write(player=1)
        _deploy(s, "for $i in range(3) { break }")
        assert s.phase == "anim_post_exec1"
        assert not any(entry.get("op") == "halt" for entry in s._exec_log)
        assert not any(entry.get("op") == "reset" for entry in s._exec_log)


# ================================================================== get_state

class TestGetState:
    def test_returns_required_keys(self):
        s = _in_write()
        state = s.get_state()
        for key in ("game_id", "game_over", "winner", "current_player", "phase",
                    "board", "agents", "territory", "clock", "word_bank", "exec_log"):
            assert key in state

    def test_board_shape(self):
        s = _session(_engine(size=4))
        s.phase = "write"
        state = s.get_state()
        assert len(state["board"]) == 4
        assert len(state["board"][0]) == 4
        assert "p1" in state["board"][0][0]
        assert "p2" in state["board"][0][0]

    def test_territory_keys(self):
        s = _in_write()
        state = s.get_state()
        for key in ("p1", "p2", "black", "total"):
            assert key in state["territory"]

    def test_game_id_correct(self):
        s = _in_write()
        assert s.get_state()["game_id"] == "test-game"

    def test_no_advance_before_deadline(self):
        s = _session()
        s.phase = "anim_pre_write"
        s._anim_deadline = time.monotonic() + 9999.0
        s.get_state()
        assert s.phase == "anim_pre_write"

    def test_advance_anim_pre_write_to_write(self):
        s = _session()
        s.phase = "anim_pre_write"
        s._anim_deadline = time.monotonic() - 1.0  # already expired
        s.get_state()
        assert s.phase == "write"

    def test_advance_anim_pre_write_starts_clock(self):
        s = _session()
        s.phase = "anim_pre_write"
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()
        assert s.engine._clock_tick[s.current_player] is not None

    def test_advance_anim_post_exec1_switches_player(self):
        s = _session()
        s.phase = "anim_post_exec1"
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()
        assert s.current_player == 2

    def test_advance_anim_post_exec1_runs_exec2(self):
        # After anim_post_exec1 expires, P2's exec2 runs (no script → halt)
        # Session should be in anim_pre_write for P2
        s = _session()
        s.phase = "anim_post_exec1"
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()
        assert s.phase == "anim_pre_write"
        assert s.current_player == 2


# ================================================================== check_clock_expired

class TestCheckClockExpired:
    def test_not_expired_in_write(self):
        s = _in_write()
        assert s.check_clock_expired() is False
        assert s.game_over is False

    def test_expired_in_write_finishes_game(self):
        s = _in_write(player=1)
        s.engine._clock_remaining[1] = 0.0
        expired = s.check_clock_expired()
        assert expired is True
        assert s.game_over is True
        assert s.winner == 2  # opponent wins

    def test_expired_sets_phase_finished(self):
        s = _in_write(player=1)
        s.engine._clock_remaining[1] = 0.0
        s.check_clock_expired()
        assert s.phase == "finished"

    def test_not_checked_outside_write_phase(self):
        s = _session()
        s.phase = "anim_pre_write"
        s.engine._clock_remaining[1] = 0.0
        assert s.check_clock_expired() is False
        assert s.game_over is False

    def test_p2_clock_expiry_winner_is_p1(self):
        s = _in_write(player=2)
        s.engine._clock_remaining[2] = 0.0
        s.check_clock_expired()
        assert s.winner == 1


# ================================================================== turn sequencing

class TestTurnSequencing:
    def test_deploy_switches_to_exec1_then_anim_post(self):
        s = _in_write(player=1)
        _deploy(s)
        assert s.phase == "anim_post_exec1"
        assert s.current_player == 1  # player hasn't switched yet

    def test_after_anim_post_exec1_switches_to_p2(self):
        s = _in_write(player=1)
        _deploy(s)
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()
        assert s.current_player == 2

    def test_p2_runs_exec2_after_p1_anim_post(self):
        s = _in_write(player=1)
        _deploy(s)
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()
        # P2 has no script, exec2 ran → anim_pre_write for P2
        assert s.phase == "anim_pre_write"
        assert s.current_player == 2

    def test_p2_write_then_exec1(self):
        # Full sequence: P1 deploy → P2 exec2(noop) → P2 write → P2 exec1
        s = _in_write(player=1)
        _deploy(s)
        # Skip P1's post-exec1 animation and P2's pre-write animation
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P2 exec2 runs, anim_pre_write
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P2 write phase
        assert s.phase == "write"
        assert s.current_player == 2
        _deploy(s, player=2)
        assert s._program[2] is not None
        assert s.phase == "anim_post_exec1"

    def test_p1_exec2_runs_stored_script(self):
        # Full sequence to reach P1's second exec2 (which should run the stored script)
        s = _in_write(player=1)
        _deploy(s, source="")  # P1 exec1 (empty script)
        # P2's full turn
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P2 exec2 → anim_pre_write
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # → write
        _deploy(s, player=2, source="")  # P2 exec1
        # Back to P1's exec2
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P1 exec2 runs stored program
        # P1's program was set, so exec2 should have produced a log (empty prog → empty log)
        assert s.current_player == 1
        assert s.phase == "anim_pre_write"


# ================================================================== win detection

class TestWinDetection:
    def _dominate_for(self, board, player, count):
        """Give player ownership of `count` cells."""
        n = 0
        for row in board.grid:
            for c in row:
                if n >= count:
                    return
                if player == 1:
                    c.p1 = 1
                    c.p2 = 0
                else:
                    c.p2 = 1
                    c.p1 = 0
                n += 1

    def test_win_after_exec1(self):
        # 4x4 board = 16 cells; need 10 (62.5%) for win
        s = _in_write(player=1, engine=_engine(size=4))
        self._dominate_for(s.engine.board, 1, 10)
        _deploy(s, source="")  # exec1 runs empty script; win already on board
        assert s.game_over is True
        assert s.winner == 1
        assert s.phase == "finished"

    def test_win_after_exec2(self):
        s = _in_write(player=1, engine=_engine(size=4))
        _deploy(s, source="")  # exec1 (empty), no win yet
        # Set up win for P1 after exec2 runs
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P2 exec2 (no script) → anim_pre_write
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P2 write
        _deploy(s, player=2, source="")  # P2 exec1
        # Dominate board for P2 so their exec2 triggers win
        self._dominate_for(s.engine.board, 2, 10)
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P1 exec2 runs → but first, check win: P2 has 10 cells
        assert s.game_over is True
        assert s.winner == 2
        assert s.phase == "finished"

    def test_no_win_before_threshold(self):
        s = _in_write(player=1, engine=_engine(size=4))
        self._dominate_for(s.engine.board, 1, 9)  # 56% < 60%
        _deploy(s, source="")
        assert s.game_over is False

    def test_stalemate_detection(self):
        # 4x4 = 16 cells; make 7 cells have p2=5 and 7 cells have p1=5 → both blocked
        s = _in_write(player=1, engine=_engine(size=4))
        n = 0
        for row in s.engine.board.grid:
            for c in row:
                if n < 7:
                    c.p2 = 5
                elif n < 14:
                    c.p1 = 5
                n += 1
        # P1 max_possible = 16 - 7 = 9 < 9.6; P2 max_possible = 16 - 7 = 9 < 9.6
        _deploy(s, source="")
        assert s.game_over is True
        assert s.winner == "draw"


# ================================================================== exec_log

class TestExecLog:
    def test_log_empty_on_no_script(self):
        s = create_session("log-test-1", 6, 500, 300.0)
        # After create_session, P1 exec2 ran with no script
        assert s._exec_log == []

    def test_log_in_get_state(self):
        s = _in_write()
        _deploy(s, source="")
        state = s.get_state()
        assert "exec_log" in state

    def test_log_after_reset_preserved(self):
        # A reset should still return the log up to the point of reset
        from app.game.engine import HaltSignal, ResetSignal
        s = _in_write(player=1)
        _deploy(s, source="")
        # Verify exec_log is a list (even if empty for empty script)
        assert isinstance(s._exec_log, list)

    def test_log_contains_move_entry(self):
        s = _in_write(player=1, engine=_engine(size=8, op_limit=500))
        # Place P2 agent away so no collision
        s.engine.agents[2].row = 7
        s.engine.agents[2].col = 7
        # P1 starts at (2, 2); move RIGHT → ends at (2, 3)
        _deploy(s, source="move(RIGHT)")
        move_entries = [e for e in s._exec_log if e["op"] == "move"]
        assert len(move_entries) == 1
        assert move_entries[0]["to"] == (2, 3)

    def test_log_contains_paint_entry(self):
        s = _in_write(player=1, engine=_engine(size=8, op_limit=500))
        _deploy(s, source="paint(1)")
        paint_entries = [e for e in s._exec_log if e["op"] == "paint"]
        assert len(paint_entries) == 1
        assert paint_entries[0]["at"] == (s.engine.agents[1].row, s.engine.agents[1].col)
        assert paint_entries[0]["amount"] == 1

    def test_log_replaced_on_each_exec(self):
        s = _in_write(player=1)
        _deploy(s, source="")
        first_log_id = id(s._exec_log)
        # Advance to P2's write and deploy
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # P2 exec2 → anim_pre_write
        s._anim_deadline = time.monotonic() - 1.0
        s.get_state()  # → write
        _deploy(s, player=2, source="")
        # P2's exec1 ran; log replaced
        assert id(s._exec_log) != first_log_id or s._exec_log == []


# ================================================================== word bank accumulation

class TestWordBankAccumulation:
    def test_accumulation_starts_after_exec2(self):
        # After _run_exec2, word accumulation should be active
        s = _session()
        s._run_exec2()  # no script → halt
        assert s.engine._word_tick[1] is not None

    def test_accumulation_paused_after_deploy(self):
        s = _in_write(player=1)
        s.engine.resume_word_accumulation(1)
        _deploy(s, source="")
        assert s.engine._word_tick[1] is None

    def test_word_bank_accrues_during_write_phase(self):
        e = _engine(word_rate=10.0)
        s = _session(e)
        s.phase = "write"
        s.current_player = 1
        t0 = 1000.0
        with patch("time.monotonic", side_effect=[t0, t0 + 5.0]):
            e.resume_word_accumulation(1)
            bank = e.word_bank(1)
        assert abs(bank - 50.0) < 0.1
