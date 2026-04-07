import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from .engine import Engine
from config import Config


@dataclass
class PendingLobby:
    game_id: str
    settings: dict
    player1_id: int
    player1_username: str
    player2_id: int | None = None
    player2_username: str | None = None
    player1_ready: bool = False
    player2_ready: bool = False

    def lobby_status(self) -> dict:
        return {
            "player1_username": self.player1_username,
            "player2_joined": self.player2_id is not None,
            "player2_username": self.player2_username,
            "player1_ready": self.player1_ready,
            "player2_ready": self.player2_ready,
            "both_ready": self.player1_ready and self.player2_ready and self.player2_id is not None,
            "started": False,
            "settings": self.settings,
        }


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
        self.end_reason: str | None = None
        self._exec_log: list[dict] = []
        self._exec_ops: int = 0
        self._last_exec_player: int | None = None
        self._auto_player: int | None = None
        self._auto_first_script: str | None = None
        self._auto_repeat_script: str | None = None
        self._auto_write_delay: float = 0.0
        self._auto_write_ready_at: float | None = None
        self._auto_deploy_count: int = 0
        self._write_started_at: float | None = None
        self._opening_pre_write_pending: bool = True
        self._multiplayer: bool = False
        self._player_ids: dict[int, int | None] = {1: None, 2: None}

    _SENSING_OPS = {"get_friction", "has_agent", "my_paint", "opp_paint"}

    def set_multiplayer_players(self, p1_id: int, p2_id: int) -> None:
        self._multiplayer = True
        self._player_ids[1] = p1_id
        self._player_ids[2] = p2_id

    def configure_auto_writer(
        self,
        player: int,
        first_script: str,
        repeat_script: str,
        write_delay_seconds: float,
    ) -> None:
        self._auto_player = player
        self._auto_first_script = first_script
        self._auto_repeat_script = repeat_script
        self._auto_write_delay = max(0.0, write_delay_seconds)

    # ------------------------------------------------------------------ public API

    def compile_script(self, player: int, source: str, user_id: int | None = None) -> dict:
        """Lint only — no state change, no clock interaction."""
        if self._multiplayer and user_id != self._player_ids.get(player):
            return {"ok": False, "errors": ["forbidden"], "warnings": [], "word_count": 0}
        if player != self.current_player or self.phase != "write":
            return {"ok": False, "errors": ["not your write phase"], "warnings": [], "word_count": 0}
        if self.engine.clock_expired(player):
            self._finish(3 - player, reason="timeout")
            return {"ok": False, "errors": ["time expired"], "warnings": [], "word_count": 0}
        result = self.engine.compile(source)
        return {
            "ok": result.ok,
            "errors": [str(e) for e in result.errors],
            "warnings": [str(w) for w in result.warnings],
            "word_count": result.word_count,
        }

    def deploy_script(self, player: int, source: str, user_id: int | None = None) -> dict:
        """Compile, spend words, store program, run exec1, enter post-exec1 animation."""
        if self._multiplayer and user_id != self._player_ids.get(player):
            return {"ok": False, "errors": ["forbidden"], "warnings": []}
        if player != self.current_player or self.phase != "write":
            return {"ok": False, "errors": ["not your write phase"], "warnings": []}

        self._auto_write_ready_at = None
        self.engine.pause_clock(player)
        self.engine.pause_word_accumulation(player)

        if self.engine.clock_expired(player):
            self._finish(3 - player, reason="timeout")
            return {"ok": False, "errors": ["time expired"], "warnings": []}

        result = self.engine.compile(source)
        if not result.ok:
            self.engine.resume_clock(player)
            self.engine.resume_word_accumulation(player)
            return {
                "ok": False,
                "errors": [str(e) for e in result.errors],
                "warnings": [str(w) for w in result.warnings],
            }

        if not self.engine.spend_words(player, result.word_count):
            self.engine.resume_clock(player)
            self.engine.resume_word_accumulation(player)
            return {"ok": False, "errors": ["insufficient word bank"], "warnings": []}

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
        self.check_clock_expired()
        self._maybe_auto_deploy()
        self.check_clock_expired()
        p1, p2, black, total = self.engine.board.territory()
        return {
            "game_id": self.game_id,
            "game_over": self.game_over,
            "winner": self.winner,
            "end_reason": self.end_reason,
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
            "last_exec_player": self._last_exec_player,
            "animation_step_duration": Config.ANIMATION_STEP_DURATION,
            "phase_timer": self._phase_timer_payload(),
            "op_limit": self.engine.op_limit,
        }

    def check_clock_expired(self) -> bool:
        """Call during polling to detect write-phase timeout."""
        if self.phase == "write" and self.engine.clock_expired(self.current_player):
            self._finish(3 - self.current_player, reason="timeout")
            return True
        return False

    def skip_opening_pre_write(self) -> None:
        """Force the one-time opening pre-write wait to end on the next state tick."""
        self._opening_pre_write_pending = False
        if self.phase in ("anim_pre_write", "opening_pre_write"):
            self._anim_deadline = time.monotonic() - 1.0

    # ------------------------------------------------------------------ private helpers

    def _run_exec2(self) -> None:
        self.phase = "exec2"
        self._last_exec_player = self.current_player
        program = self._program[self.current_player]
        if program is not None:
            _, self._exec_log, self._exec_ops = self.engine.run_execution(self.current_player, program)
        else:
            self._exec_log = []
            self._exec_ops = 0
        self._check_win_stalemate()
        if not self.game_over:
            wait_seconds = self._animation_wait_seconds(self._exec_log)
            if self._opening_pre_write_pending:
                self.phase = "opening_pre_write"
                self._anim_deadline = time.monotonic() + wait_seconds + Config.INITIAL_PRE_WRITE_SECONDS
                self._opening_pre_write_pending = False
            else:
                self.phase = "anim_pre_write"
                self._anim_deadline = time.monotonic() + wait_seconds
        self._write_started_at = None

    def _run_exec1(self) -> None:
        self.phase = "exec1"
        self._last_exec_player = self.current_player
        _, self._exec_log, self._exec_ops = self.engine.run_execution(self.current_player, self._program[self.current_player])
        self._check_win_stalemate()
        if not self.game_over:
            self.phase = "anim_post_exec1"
            self._anim_deadline = time.monotonic() + self._animation_wait_seconds(self._exec_log)
        self._write_started_at = None

    def _animation_wait_seconds(self, exec_log: list[dict]) -> float:
        non_sensing_steps = sum(1 for entry in exec_log if entry.get("op") not in self._SENSING_OPS)
        return non_sensing_steps * Config.ANIMATION_STEP_DURATION + 2.0

    def _maybe_advance_animation(self) -> None:
        if self._anim_deadline is None or time.monotonic() < self._anim_deadline:
            return
        if self.phase == "anim_pre_write":
            self._enter_write_phase()
        elif self.phase == "opening_pre_write":
            self._enter_write_phase()
        elif self.phase == "anim_post_exec1":
            self._anim_deadline = None
            self._switch_player()
            self._run_exec2()

    def _enter_write_phase(self) -> None:
        self.phase = "write"
        self._anim_deadline = None
        self._write_started_at = time.monotonic()
        self.engine.resume_clock(self.current_player)
        self.engine.resume_word_accumulation(self.current_player)
        if self.current_player == self._auto_player:
            self._auto_write_ready_at = time.monotonic() + self._auto_write_delay

    def _phase_timer_payload(self) -> dict | None:
        now = time.monotonic()
        if self.phase in ("anim_pre_write", "anim_post_exec1", "opening_pre_write") and self._anim_deadline is not None:
            return {
                "mode": "countdown",
                "seconds": max(0.0, self._anim_deadline - now),
            }
        if self.phase == "write":
            started_at = self._write_started_at if self._write_started_at is not None else now
            return {
                "mode": "countup",
                "seconds": max(0.0, now - started_at),
            }
        return None

    def _maybe_auto_deploy(self) -> None:
        if self.game_over:
            return
        if self._auto_player is None or self.current_player != self._auto_player:
            return
        if self.phase != "write":
            return
        if self._auto_first_script is None or self._auto_repeat_script is None:
            return

        now = time.monotonic()
        if self._auto_write_ready_at is None:
            self._auto_write_ready_at = now + self._auto_write_delay
            return
        if now < self._auto_write_ready_at:
            return

        source = self._auto_first_script if self._auto_deploy_count == 0 else self._auto_repeat_script
        result = self.deploy_script(self._auto_player, source)
        if result.get("ok"):
            self._auto_deploy_count += 1
        elif "insufficient word bank" in result.get("errors", []):
            self._auto_write_ready_at = time.monotonic() + 1.0

    def _check_win_stalemate(self) -> None:
        w = self.engine.check_winner()
        if w is not None:
            self._finish(w, reason="territory")
            return
        if self.engine.check_stalemate():
            self._finish("draw", reason="stalemate")

    def _finish(self, winner: int | str, reason: str | None = None) -> None:
        for player in (1, 2):
            self.engine.pause_clock(player)
            self.engine.pause_word_accumulation(player)
        self.game_over = True
        self.winner = winner
        self.end_reason = reason
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
_pending_lobbies: dict[str, PendingLobby] = {}


def create_lobby(game_id: str, settings: dict, player1_id: int, username: str) -> PendingLobby:
    lobby = PendingLobby(
        game_id=game_id,
        settings=settings,
        player1_id=player1_id,
        player1_username=username,
    )
    _pending_lobbies[game_id] = lobby
    return lobby


def get_lobby(game_id: str) -> PendingLobby | None:
    return _pending_lobbies.get(game_id)


def remove_lobby(game_id: str) -> None:
    _pending_lobbies.pop(game_id, None)


def create_session(
    game_id: str,
    size: int,
    op_limit: int,
    clock_seconds: float,
    word_rate: float = 1.0,
    starting_player: int = 1,
) -> GameSession:
    """Create a new session and immediately run first exec2 for the starting player."""
    engine = Engine(size, op_limit, clock_seconds, word_rate)
    session = GameSession(game_id, engine)
    session.current_player = 2 if starting_player == 2 else 1
    _sessions[game_id] = session
    session._run_exec2()
    return session


def get_session(game_id: str) -> GameSession | None:
    return _sessions.get(game_id)
