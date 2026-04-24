import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from .engine import Engine
from config import Config


def _restore_funcs(engine: Engine, func_bodies: dict) -> None:
    """Rebuild engine.persisted_funcs from {name: source_text} of stored function bodies."""
    from ..lang.lexer import tokenize
    from ..lang.parser import parse
    from ..lang.nodes import FuncDef
    from ..lang.compiler import Type

    _BODIES_KEY = 0
    bodies = engine.persisted_funcs.setdefault(_BODIES_KEY, {})
    for name, body_text in func_bodies.items():
        try:
            tokens = tokenize(body_text)
            program = parse(tokens)
            for stmt in program.stmts:
                if isinstance(stmt, FuncDef):
                    bodies[stmt.name] = stmt
                    engine.persisted_funcs[stmt.name] = (stmt.params, Type(0))
                    break
        except Exception:
            pass


def _extract_func_text(source_lines: list[str], start_line: int) -> str:
    """Extract a function definition from source lines given its 1-based start line.

    Scans from the def keyword line forward, tracking brace depth to find the
    matching closing brace.
    """
    idx = start_line - 1  # convert to 0-based
    if idx < 0 or idx >= len(source_lines):
        return ""
    depth = 0
    end_idx = idx
    for i in range(idx, len(source_lines)):
        for ch in source_lines[i]:
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
        end_idx = i
        if depth <= 0 and i > idx:
            break
    return "\n".join(source_lines[idx:end_idx + 1])


@dataclass
class PendingLobby:
    game_id: str
    settings: dict
    player1_id: int
    player1_username: str
    join_alias: str = ''
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
        self._write_started_at: float | None = None
        self._opening_pre_write_pending: bool = True
        self._player_ids: dict[int, int | None] = {1: None, 2: None}
        self._draw_offer_player: int | None = None
        self._draw_cooldown: dict[int, float] = {}

        # Persistence tracking
        self._phase_counter: int = 0
        self._prev_phase_id: int | None = None
        self._turn_counter: int = 0
        self._current_script_id: int | None = None

    _SENSING_OPS = {"get_friction", "has_agent", "my_paint", "opp_paint"}

    def set_players(self, p1_id: int, p2_id: int | None) -> None:
        self._player_ids[1] = p1_id
        self._player_ids[2] = p2_id

    # ------------------------------------------------------------------ public API

    def compile_script(self, player: int, source: str, user_id: int | None = None) -> dict:
        """Lint only — no state change, no clock interaction."""
        if user_id != self._player_ids.get(player):
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
        if user_id != self._player_ids.get(player):
            return {"ok": False, "errors": ["forbidden"], "warnings": []}
        if player != self.current_player or self.phase != "write":
            return {"ok": False, "errors": ["not your write phase"], "warnings": []}

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

        # Persist script before execution
        account_id = self._player_ids.get(player)
        script_id = self._persist_script(source, result.word_count, player, account_id)
        self._current_script_id = script_id

        # Snapshot function names before execution to detect new definitions
        funcs_before = set(self.engine.persisted_funcs.get(0, {}).keys())

        self._program[player] = result.program
        self._run_exec1()

        # Persist any newly defined functions
        self._persist_functions(source, script_id, player, account_id, funcs_before)

        return {
            "ok": True,
            "game_over": self.game_over,
            "winner": self.winner,
            "warnings": [str(w) for w in result.warnings],
        }

    def get_state(self, for_player: int | None = None) -> dict:
        """Auto-advance animation phases, then return game state.

        If for_player is 1 or 2, sensitive fields are filtered so each client
        only receives its own private data:
        - exec_log: sensing ops are stripped when the requesting player is not
          the one who executed (they don't need them and shouldn't see them).
        - word_bank: only the requesting player's own level is included.
        """
        self._maybe_advance_animation()
        self.check_clock_expired()
        p1, p2, black, total = self.engine.board.territory()

        if for_player is not None and for_player != self._last_exec_player:
            exec_log = [e for e in self._exec_log if e.get("op") not in self._SENSING_OPS]
        else:
            exec_log = self._exec_log

        if for_player is not None:
            word_bank = {for_player: self.engine.word_bank(for_player)}
        else:
            word_bank = {
                1: self.engine.word_bank(1),
                2: self.engine.word_bank(2),
            }

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
            "word_bank": word_bank,
            "word_rate": self.engine._word_rate,
            "exec_log": exec_log,
            "exec_ops_consumed": self._exec_ops,
            "last_exec_player": self._last_exec_player,
            "animation_step_duration": Config.ANIMATION_STEP_DURATION,
            "phase_timer": self._phase_timer_payload(),
            "op_limit": self.engine.op_limit,
            "draw_offer": self._draw_offer_state(),
        }

    def offer_draw(self, player: int, user_id: int | None = None) -> dict:
        """Player offers a draw; rejected if a cooldown is still active."""
        if user_id != self._player_ids.get(player):
            return {"ok": False, "error": "forbidden"}
        if self.game_over:
            return {"ok": False, "error": "game already over"}
        if player not in (1, 2):
            return {"ok": False, "error": "invalid player"}
        if self._draw_offer_player is not None:
            return {"ok": False, "error": "draw already offered"}
        if self._draw_cooldown.get(player, 0) > time.monotonic():
            return {"ok": False, "error": "cooldown active"}
        self._draw_offer_player = player
        return {"ok": True}

    def cancel_draw(self, player: int, user_id: int | None = None) -> dict:
        """Offering player withdraws their own pending draw offer."""
        if user_id != self._player_ids.get(player):
            return {"ok": False, "error": "forbidden"}
        if self._draw_offer_player != player:
            return {"ok": False, "error": "no draw offer from this player"}
        self._draw_offer_player = None
        return {"ok": True}

    def accept_draw(self, player: int, user_id: int | None = None) -> dict:
        """Non-offering player accepts; ends the game as a draw."""
        if user_id != self._player_ids.get(player):
            return {"ok": False, "error": "forbidden"}
        if self.game_over:
            return {"ok": False, "error": "game already over"}
        if self._draw_offer_player is None:
            return {"ok": False, "error": "no draw offer"}
        if self._draw_offer_player == player:
            return {"ok": False, "error": "cannot accept your own offer"}
        self._finish("draw", reason="draw_offer")
        return {"ok": True}

    def reject_draw(self, player: int, user_id: int | None = None) -> dict:
        """Non-offering player rejects; offering player gets a 30-second cooldown."""
        if user_id != self._player_ids.get(player):
            return {"ok": False, "error": "forbidden"}
        if self._draw_offer_player is None:
            return {"ok": False, "error": "no draw offer"}
        if self._draw_offer_player == player:
            return {"ok": False, "error": "cannot reject your own offer"}
        self._draw_cooldown[self._draw_offer_player] = time.monotonic() + 30.0
        self._draw_offer_player = None
        return {"ok": True}

    def resign(self, player: int, user_id: int | None = None) -> dict:
        """Forfeit the game on behalf of player; the opponent wins."""
        if user_id != self._player_ids.get(player):
            return {"ok": False, "error": "forbidden"}
        if self.game_over:
            return {"ok": False, "error": "game already over"}
        if player not in (1, 2):
            return {"ok": False, "error": "invalid player"}
        self._finish(3 - player, reason="resign")
        return {"ok": True}

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

    def _draw_offer_state(self) -> dict:
        now = time.monotonic()
        return {
            "offered_by": self._draw_offer_player,
            "cooldown": {
                1: max(0.0, self._draw_cooldown[1] - now) if self._draw_cooldown.get(1, 0) > now else None,
                2: max(0.0, self._draw_cooldown[2] - now) if self._draw_cooldown.get(2, 0) > now else None,
            },
        }

    # ------------------------------------------------------------------ persistence

    def _snapshot_board_json(self) -> str:
        return json.dumps(self.engine.board.snapshot())

    def _snapshot_agents_json(self) -> str:
        agents = self.engine.agents
        return json.dumps({
            "1": {"row": agents[1].row, "col": agents[1].col},
            "2": {"row": agents[2].row, "col": agents[2].col},
        })

    def _snapshot_word_banks_json(self) -> str:
        return json.dumps({
            "1": self.engine.word_bank(1),
            "2": self.engine.word_bank(2),
        })

    def _snapshot_clock_json(self) -> str:
        return json.dumps({
            "1": self.engine.clock_remaining(1),
            "2": self.engine.clock_remaining(2),
        })

    def _persist_phase(
        self,
        exec_type: str,
        player_slot: int,
        outcome: str | None = None,
        exec_log: list[dict] | None = None,
        ops_consumed: int = 0,
        script_id: int | None = None,
    ) -> None:
        """Insert an ExecutionPhase row capturing the current board/agent/clock/word state."""
        try:
            from .. import db
            from ..models import ExecutionPhase

            phase = ExecutionPhase(
                game_id=self.game_id,
                phase_number=self._phase_counter,
                player_slot=player_slot,
                exec_type=exec_type,
                script_id=script_id,
                outcome=outcome,
                exec_log_json=json.dumps(exec_log) if exec_log is not None else None,
                ops_consumed=ops_consumed,
                board_state_json=self._snapshot_board_json(),
                agents_json=self._snapshot_agents_json(),
                word_banks_json=self._snapshot_word_banks_json(),
                clock_remaining_json=self._snapshot_clock_json(),
                prev_phase_id=self._prev_phase_id,
            )
            db.session.add(phase)
            db.session.flush()
            self._prev_phase_id = phase.id
            self._phase_counter += 1
            db.session.commit()
        except Exception:
            pass  # best-effort; in-memory state is authoritative

    def _persist_initial_phase(self) -> None:
        """Insert phase 0 representing the initial board state before any player action."""
        self._persist_phase(
            exec_type="initial",
            player_slot=self.current_player,
        )

    def _persist_script(
        self,
        source: str,
        word_count: int,
        player_slot: int,
        account_id: int | None,
    ) -> int | None:
        """Insert a Script row and return its ID."""
        try:
            from .. import db
            from ..models import Script

            write_duration = None
            if self._write_started_at is not None:
                write_duration = time.monotonic() - self._write_started_at

            script = Script(
                game_id=self.game_id,
                account_id=account_id,
                player_slot=player_slot,
                source_text=source,
                word_count=word_count,
                write_duration_seconds=write_duration,
                turn_number=self._turn_counter,
            )
            db.session.add(script)
            db.session.flush()
            self._turn_counter += 1
            script_id = script.id
            db.session.commit()
            return script_id
        except Exception:
            return None

    def _persist_functions(
        self,
        source: str,
        script_id: int | None,
        player_slot: int,
        account_id: int | None,
        funcs_before: set[str],
    ) -> None:
        """Insert DefinedFunction rows for any newly defined/redefined functions."""
        if script_id is None:
            return
        try:
            from .. import db
            from ..models import DefinedFunction

            bodies = self.engine.persisted_funcs.get(0, {})
            new_names = set(bodies.keys()) - funcs_before
            if not new_names:
                return

            source_lines = source.splitlines()
            for name in new_names:
                func_def = bodies[name]
                func_text = _extract_func_text(source_lines, func_def.line)
                db.session.add(DefinedFunction(
                    game_id=self.game_id,
                    account_id=account_id,
                    script_id=script_id,
                    func_name=name,
                    func_body_text=func_text,
                ))
            db.session.commit()
        except Exception:
            pass

    # ------------------------------------------------------------------ private helpers

    def _run_exec2(self) -> None:
        self.phase = "exec2"
        self._last_exec_player = self.current_player
        program = self._program[self.current_player]
        if program is not None:
            outcome, self._exec_log, self._exec_ops = self.engine.run_execution(self.current_player, program)
        else:
            outcome = None
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
        if outcome is not None:
            self._persist_phase(
                exec_type="exec2",
                player_slot=self.current_player,
                outcome=outcome,
                exec_log=self._exec_log,
                ops_consumed=self._exec_ops,
                script_id=self._current_script_id,
            )

    def _run_exec1(self) -> None:
        self.phase = "exec1"
        self._last_exec_player = self.current_player
        outcome, self._exec_log, self._exec_ops = self.engine.run_execution(self.current_player, self._program[self.current_player])
        self._check_win_stalemate()
        if not self.game_over:
            self.phase = "anim_post_exec1"
            self._anim_deadline = time.monotonic() + self._animation_wait_seconds(self._exec_log)
        self._write_started_at = None
        self._persist_phase(
            exec_type="exec1",
            player_slot=self.current_player,
            outcome=outcome,
            exec_log=self._exec_log,
            ops_consumed=self._exec_ops,
            script_id=self._current_script_id,
        )

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
                game.is_draw = self.winner == "draw"
                game.end_reason = self.end_reason
                game.finished_at = datetime.now(timezone.utc)
                db.session.commit()
        except Exception:
            pass  # best-effort; in-memory state is authoritative


# ------------------------------------------------------------------ module registry

_sessions: dict[str, "GameSession"] = {}
_pending_lobbies: dict[str, PendingLobby] = {}
_alias_index: dict[str, str] = {}  # join_alias (uppercase) -> game_id


def _restore_session_from_db(game_id: str) -> "GameSession | None":
    """Rebuild a GameSession from the most recent persisted ExecutionPhase for an active game."""
    try:
        from .. import db
        from ..models import Game, ExecutionPhase, Script, DefinedFunction

        game = Game.query.get(game_id)
        if game is None or game.status != 'active':
            return None

        last_phase = (
            ExecutionPhase.query
            .filter_by(game_id=game_id)
            .order_by(ExecutionPhase.phase_number.desc())
            .first()
        )
        if last_phase is None:
            return None

        size = game.board_size or Config.BOARD_SIZE
        op_limit = game.op_limit or Config.OP_LIMIT
        clock_seconds = game.clock_seconds or Config.CLOCK_SECONDS
        word_rate = game.word_rate if game.word_rate is not None else Config.WORD_RATE

        engine = Engine(size, op_limit, clock_seconds, word_rate)

        # Restore board
        engine.board.restore(json.loads(last_phase.board_state_json))

        # Restore agent positions
        agents_raw = json.loads(last_phase.agents_json)
        engine.agents[1].row = agents_raw['1']['row']
        engine.agents[1].col = agents_raw['1']['col']
        engine.agents[2].row = agents_raw['2']['row']
        engine.agents[2].col = agents_raw['2']['col']

        # Restore word banks and clocks (both paused at snapshot values)
        if last_phase.word_banks_json:
            wb = json.loads(last_phase.word_banks_json)
            engine._word_bank[1] = float(wb.get('1') or 0.0)
            engine._word_bank[2] = float(wb.get('2') or 0.0)

        if last_phase.clock_remaining_json:
            clk = json.loads(last_phase.clock_remaining_json)
            p1_clk = clk.get('1') or clk.get(1)
            p2_clk = clk.get('2') or clk.get(2)
            if p1_clk is not None:
                engine._clock_remaining[1] = float(p1_clk)
            if p2_clk is not None:
                engine._clock_remaining[2] = float(p2_clk)

        # Restore persisted function definitions
        all_funcs = (
            DefinedFunction.query
            .filter_by(game_id=game_id)
            .order_by(DefinedFunction.id)
            .all()
        )
        func_bodies = {}
        for f in all_funcs:
            func_bodies[f.func_name] = f.func_body_text
        _restore_funcs(engine, func_bodies)

        session = GameSession(game_id, engine)
        session._opening_pre_write_pending = False
        session._phase_counter = last_phase.phase_number + 1
        session._prev_phase_id = last_phase.id
        session._turn_counter = Script.query.filter_by(game_id=game_id).count()
        session.set_players(game.player1_id, game.player2_id)

        exec_type = last_phase.exec_type
        player_slot = last_phase.player_slot

        if exec_type in ('exec2', 'initial'):
            current_player = player_slot if exec_type == 'exec2' else (game.starting_player or 1)
            session.current_player = current_player
        else:
            # exec1 for player_slot just ran but exec2 for the other player never persisted.
            # Re-run exec2 for the other player to bring board state up to date.
            other = 3 - player_slot
            session.current_player = other
            last_script = (
                Script.query
                .filter_by(game_id=game_id, player_slot=other)
                .order_by(Script.turn_number.desc())
                .first()
            )
            if last_script:
                try:
                    result = engine.compile(last_script.source_text)
                    if result.ok:
                        session._program[other] = result.program
                except Exception:
                    pass
            session._run_exec2()
            # Skip the animation — go straight to write phase
            session._anim_deadline = None

        if not session.game_over:
            session.phase = 'write'
            session._write_started_at = time.monotonic()
            engine.resume_clock(session.current_player)
            engine.resume_word_accumulation(session.current_player)

        _sessions[game_id] = session
        return session
    except Exception:
        return None


def create_lobby(game_id: str, settings: dict, player1_id: int, username: str, join_alias: str = '') -> PendingLobby:
    lobby = PendingLobby(
        game_id=game_id,
        settings=settings,
        player1_id=player1_id,
        player1_username=username,
        join_alias=join_alias,
    )
    _pending_lobbies[game_id] = lobby
    if join_alias:
        _alias_index[join_alias.upper()] = game_id
    return lobby


def alias_in_use(alias: str) -> bool:
    return alias.upper() in _alias_index


def get_lobby_by_alias(alias: str) -> PendingLobby | None:
    game_id = _alias_index.get(alias.upper())
    if game_id is None:
        return None
    return _pending_lobbies.get(game_id)


def get_lobby(game_id: str) -> PendingLobby | None:
    return _pending_lobbies.get(game_id)


def remove_lobby(game_id: str) -> None:
    lobby = _pending_lobbies.pop(game_id, None)
    if lobby and lobby.join_alias:
        _alias_index.pop(lobby.join_alias.upper(), None)


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
    session._persist_initial_phase()
    session._run_exec2()
    return session


def get_session(game_id: str) -> GameSession | None:
    session = _sessions.get(game_id)
    if session is not None:
        return session
    return _restore_session_from_db(game_id)
