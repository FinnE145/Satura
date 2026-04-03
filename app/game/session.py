import time
from datetime import datetime, timezone
from .engine import Engine
from config import Config


class GameSession:
    def __init__(self, game_id: str, engine: Engine):
        self.game_id = game_id
        self.engine = engine
        self._program: dict[int, object | None] = {1: None, 2: None}
        self.current_player: int = 1
        self.phase: str = "exec2"
        self._anim_deadline: float | None = None
        self.game_over: bool = False
        self.winner: int | str | None = None
        self._exec_log: list[dict] = []
        self._exec_ops: int = 0

    # ------------------------------------------------------------------ public API

    def compile_script(self, player: int, source: str) -> dict:
        """Lint only — no state change, no clock interaction."""
        if player != self.current_player or self.phase != "write":
            return {"ok": False, "errors": ["not your write phase"], "warnings": [], "word_count": 0}
        result = self.engine.compile(source)
        return {
            "ok": result.ok,
            "errors": [str(e) for e in result.errors],
            "warnings": [str(w) for w in result.warnings],
            "word_count": result.word_count,
        }

    def deploy_script(self, player: int, source: str) -> dict:
        """Compile, spend words, store program, run exec1, enter post-exec1 animation."""
        if player != self.current_player or self.phase != "write":
            return {"ok": False, "errors": ["not your write phase"], "warnings": []}

        self.engine.pause_clock(player)

        if self.engine.clock_expired(player):
            self._finish(3 - player)
            return {"ok": False, "errors": ["time expired"], "warnings": []}

        result = self.engine.compile(source)
        if not result.ok:
            self.engine.resume_clock(player)
            return {
                "ok": False,
                "errors": [str(e) for e in result.errors],
                "warnings": [str(w) for w in result.warnings],
            }

        if not self.engine.spend_words(player, result.word_count):
            self.engine.resume_clock(player)
            return {"ok": False, "errors": ["insufficient word bank"], "warnings": []}

        self.engine.pause_word_accumulation(player)
        self._program[player] = result.program
        self._run_exec1()
        return {
            "ok": True,
            "game_over": self.game_over,
            "winner": self.winner,
            "warnings": [str(w) for w in result.warnings],
        }

    def get_state(self) -> dict:
        """Auto-advance animation phases, then return full game state."""
        self._maybe_advance_animation()
        p1, p2, black, total = self.engine.board.territory()
        return {
            "game_id": self.game_id,
            "game_over": self.game_over,
            "winner": self.winner,
            "current_player": self.current_player,
            "phase": self.phase,
            "board": [
                [{"p1": c.p1, "p2": c.p2} for c in row]
                for row in self.engine.board.grid
            ],
            "agents": {
                1: {"row": self.engine.agents[1].row, "col": self.engine.agents[1].col},
                2: {"row": self.engine.agents[2].row, "col": self.engine.agents[2].col},
            },
            "territory": {"p1": p1, "p2": p2, "black": black, "total": total},
            "clock": {
                1: self.engine.clock_remaining(1),
                2: self.engine.clock_remaining(2),
            },
            "word_bank": {
                1: self.engine.word_bank(1),
                2: self.engine.word_bank(2),
            },
            "word_rate": self.engine._word_rate,
            "exec_log": self._exec_log,
            "exec_ops_consumed": self._exec_ops,
            "op_limit": self.engine.op_limit,
        }

    def check_clock_expired(self) -> bool:
        """Call during polling to detect write-phase timeout."""
        if self.phase == "write" and self.engine.clock_expired(self.current_player):
            self._finish(3 - self.current_player)
            return True
        return False

    # ------------------------------------------------------------------ private helpers

    def _run_exec2(self) -> None:
        self.phase = "exec2"
        program = self._program[self.current_player]
        if program is not None:
            _, self._exec_log, self._exec_ops = self.engine.run_execution(self.current_player, program)
        else:
            self._exec_log = []
            self._exec_ops = 0
        self._check_win_stalemate()
        if not self.game_over:
            self.phase = "anim_pre_write"
            self._anim_deadline = time.monotonic() + Config.ANIMATION_DURATION
            self.engine.resume_word_accumulation(self.current_player)

    def _run_exec1(self) -> None:
        self.phase = "exec1"
        _, self._exec_log, self._exec_ops = self.engine.run_execution(self.current_player, self._program[self.current_player])
        self._check_win_stalemate()
        if not self.game_over:
            self.phase = "anim_post_exec1"
            self._anim_deadline = time.monotonic() + Config.ANIMATION_DURATION

    def _maybe_advance_animation(self) -> None:
        if self._anim_deadline is None or time.monotonic() < self._anim_deadline:
            return
        if self.phase == "anim_pre_write":
            self.phase = "write"
            self._anim_deadline = None
            self.engine.resume_clock(self.current_player)
        elif self.phase == "anim_post_exec1":
            self._anim_deadline = None
            self._switch_player()
            self._run_exec2()

    def _check_win_stalemate(self) -> None:
        w = self.engine.check_winner()
        if w is not None:
            self._finish(w)
            return
        if self.engine.check_stalemate():
            self._finish("draw")

    def _finish(self, winner: int | str) -> None:
        self.game_over = True
        self.winner = winner
        self.phase = "finished"
        self._persist_result()

    def _switch_player(self) -> None:
        self.current_player = 3 - self.current_player

    def _persist_result(self) -> None:
        """Update the Game DB row to reflect the finished state."""
        try:
            from .. import db
            from ..models import Game
            game = Game.query.get(self.game_id)
            if game is not None:
                game.status = "finished"
                game.winner = self.winner if isinstance(self.winner, int) else None
                game.finished_at = datetime.now(timezone.utc)
                db.session.commit()
        except Exception:
            pass  # best-effort; in-memory state is authoritative


# ------------------------------------------------------------------ module registry

_sessions: dict[str, "GameSession"] = {}


def create_session(
    game_id: str,
    size: int,
    op_limit: int,
    clock_seconds: float,
    word_rate: float = 1.0,
) -> GameSession:
    """Create a new session and immediately run P1's first exec2 (no script → halt)."""
    engine = Engine(size, op_limit, clock_seconds, word_rate)
    session = GameSession(game_id, engine)
    _sessions[game_id] = session
    session._run_exec2()
    return session


def get_session(game_id: str) -> GameSession | None:
    return _sessions.get(game_id)
