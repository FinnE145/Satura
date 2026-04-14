# [AI Summary] Flask route handlers for all HTTP endpoints: game creation,
# script submission, state polling, and real-time compiler feedback.
# Imports: app/game/session.py, app/game/engine.py, app/lang/compiler.py,
#          app/lang/interpreter.py. Imported by: app/__init__.py.

import uuid
import re
import random
import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from urllib.parse import urlsplit
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from . import db
from .models import Game, Account, AccountSettings, Script, ExecutionPhase, DefinedFunction
from .game.session import create_session, get_session, create_lobby, get_lobby, get_lobby_by_alias, alias_in_use, remove_lobby
from config import Config

bp = Blueprint('main', __name__)

_LOG_DIR = Path(__file__).parent.parent

_ALIAS_CHARS = 'BCDFGHJKLMNPQRSTVWXZ'  # consonants only, no I or O


def _gen_join_alias() -> str:
    """Generate a unique 6-letter consonant-only join alias."""
    while True:
        code = ''.join(random.choices(_ALIAS_CHARS, k=6))
        if not alias_in_use(code):
            return code


def _populate_game_settings(game: Game, parsed: dict, created_by: int | None = None) -> None:
    """Copy parsed session config onto a Game DB row."""
    game.preset = parsed.get('preset')
    game.board_size = parsed.get('size')
    game.op_limit = parsed.get('op_limit')
    game.clock_seconds = parsed.get('clock_seconds')
    game.word_rate = parsed.get('word_rate')
    game.starting_player = parsed.get('starting_player')
    game.accommodations_enabled = parsed.get('accommodations_enabled', False)
    game.p1_clock_seconds = parsed.get('p1_clock_seconds')
    game.p2_clock_seconds = parsed.get('p2_clock_seconds')
    game.p1_starting_words = parsed.get('p1_starting_words')
    game.p2_starting_words = parsed.get('p2_starting_words')
    if created_by is not None:
        game.created_by = created_by
_PALETTES = ('solstice', 'fieldstone', 'levant', 'folio')
_PALETTE_CONFIG = {
    'solstice': {'warm': '#D2640E', 'cool': '#A82068'},
    'fieldstone': {'warm': '#AC3E26', 'cool': '#2C4874'},
    'levant': {'warm': '#C48C1C', 'cool': '#661E6E'},
    'folio': {'warm': '#D4A800', 'cool': '#303482'},
}

# UI accents are decoupled from canonical game palette values so app chrome can
# keep readable contrast without changing board rendering or SVG palette assets.
_UI_ACCENT_CONFIG = {
    'solstice': {
        'warm': '#D2640E',
        'warm_bright': '#F07828',
        'cool': '#C93E8F',
        'cool_bright': '#D85EA8',
    },
    'fieldstone': {
        # Keep warm close to shared UI warm, with a slight lift for this darker palette.
        'warm': '#BE4F2B',
        'warm_bright': '#D76A45',
        'cool': '#4F76A8',
        'cool_bright': '#6E93C1',
    },
    'levant': {
        'warm': '#D2640E',
        'warm_bright': '#F07828',
        'cool': '#8A3FA2',
        'cool_bright': '#A965BF',
    },
    'folio': {
        'warm': '#D2640E',
        'warm_bright': '#F07828',
        'cool': '#4F5CC0',
        'cool_bright': '#7380D7',
    },
}


def _hex_to_rgb(hex_color):
    value = hex_color.strip().lstrip('#')
    if len(value) != 6:
        return (0, 0, 0)
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _rgba(hex_color, alpha):
    r, g, b = _hex_to_rgb(hex_color)
    return f'rgba({r}, {g}, {b}, {alpha})'


def _active_palette_for_user():
    palette_name = Config.DEFAULT_PALETTE
    if current_user.is_authenticated:
        user_settings = _get_or_create_settings(current_user)
        if user_settings.palette in _PALETTES:
            palette_name = user_settings.palette

    base = _PALETTE_CONFIG.get(palette_name, _PALETTE_CONFIG['solstice'])
    ui_accents = _UI_ACCENT_CONFIG.get(
        palette_name,
        _UI_ACCENT_CONFIG['solstice'],
    )
    warm = base['warm']
    cool = base['cool']
    ui_warm = ui_accents['warm']
    ui_warm_bright = ui_accents['warm_bright']
    ui_cool = ui_accents['cool']
    ui_cool_bright = ui_accents['cool_bright']
    return {
        'name': palette_name,
        'warm': warm,
        'cool': cool,
        'warm_tint': _rgba(warm, '0.10'),
        'warm_dim': _rgba(warm, '0.65'),
        'cool_tint': _rgba(cool, '0.10'),
        'cool_dim': _rgba(cool, '0.65'),
        'ui_warm': ui_warm,
        'ui_warm_tint': _rgba(ui_warm, '0.10'),
        'ui_warm_dim': _rgba(ui_warm, '0.65'),
        'ui_warm_bright': ui_warm_bright,
        'ui_warm_bright_tint': _rgba(ui_warm_bright, '0.10'),
        'ui_warm_bright_dim': _rgba(ui_warm_bright, '0.65'),
        'ui_cool': ui_cool,
        'ui_cool_tint': _rgba(ui_cool, '0.10'),
        'ui_cool_dim': _rgba(ui_cool, '0.65'),
        'ui_cool_bright': ui_cool_bright,
        'ui_cool_bright_tint': _rgba(ui_cool_bright, '0.10'),
        'ui_cool_bright_dim': _rgba(ui_cool_bright, '0.65'),
        'mark_file': f'satura_logo_mark_{palette_name}.svg',
    }


@bp.app_context_processor
def inject_theme_context():
    palette = _active_palette_for_user()
    return {
        'active_palette': palette,
    }


def _log_contact(log_file, name, email, message):
    entry = (
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n"
        f"Name:    {name}\n"
        f"Email:   {email}\n"
        f"Message:\n"
        f"{message}\n"
    )
    with open(_LOG_DIR / log_file, 'a') as f:
        f.write(entry + "\n\n")



def _valid_email(email):
    if not email:
        return False
    return bool(re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email))


def _get_or_create_settings(account):
    if account.settings is not None:
        return account.settings

    settings = AccountSettings(
        account=account,
        default_time_control=Config.DEFAULT_TIME_CONTROL,
        custom_minutes=Config.DEFAULT_CUSTOM_MINUTES,
        default_player=Config.DEFAULT_PLAYER_CHOICE,
        default_board_size=Config.BOARD_SIZE,
        palette=Config.DEFAULT_PALETTE,
    )
    db.session.add(settings)
    db.session.commit()
    return settings


def _closest_board_size(value):
    stops = tuple(Config.BOARD_SIZE_STOPS)
    if value in stops:
        return value
    return min(stops, key=lambda stop: abs(stop - value))


def _coerce_int(value, *, field, minimum=None, maximum=None, allowed=None):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field} must be an integer')

    if allowed is not None and parsed not in allowed:
        allowed_text = ', '.join(str(item) for item in sorted(allowed))
        raise ValueError(f'{field} must be one of: {allowed_text}')
    if minimum is not None and parsed < minimum:
        raise ValueError(f'{field} must be at least {minimum}')
    if maximum is not None and parsed > maximum:
        raise ValueError(f'{field} must be at most {maximum}')
    return parsed


def _coerce_float(value, *, field, minimum=None, maximum=None):
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        raise ValueError(f'{field} must be a number')

    if minimum is not None and parsed < minimum:
        raise ValueError(f'{field} must be at least {minimum}')
    if maximum is not None and parsed > maximum:
        raise ValueError(f'{field} must be at most {maximum}')
    return parsed


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return bool(value)


def _parse_session_config(payload):
    presets = Config.TIME_CONTROL_PRESETS
    preset = str(payload.get('preset', '5'))
    if preset != 'custom' and preset not in presets:
        raise ValueError('preset must be one of 60, 30, 15, 5, custom')

    base = dict(presets.get(preset, presets['5']))
    if preset == 'custom':
        base['clock_seconds'] = _coerce_float(
            payload.get('clock_seconds'),
            field='clock_seconds',
            minimum=10.0,
            maximum=21600.0,
        )
        base['board_size'] = _coerce_int(
            payload.get('board_size'),
            field='board_size',
            allowed=set(Config.BOARD_SIZE_STOPS),
        )
        base['op_limit'] = _coerce_int(
            payload.get('op_limit'),
            field='op_limit',
            minimum=1,
            maximum=200,
        )
        base['word_rate'] = _coerce_float(
            payload.get('word_rate'),
            field='word_rate',
            minimum=0.1,
            maximum=10.0,
        )
        base['starting_words'] = _coerce_float(
            payload.get('starting_words'),
            field='starting_words',
            minimum=0.0,
            maximum=500.0,
        )

    accommodations_enabled = _coerce_bool(payload.get('accommodations_enabled', False))
    if accommodations_enabled:
        p1_clock_seconds = _coerce_float(
            payload.get('p1_clock_seconds', base['clock_seconds']),
            field='p1_clock_seconds',
            minimum=10.0,
            maximum=21600.0,
        )
        p2_clock_seconds = _coerce_float(
            payload.get('p2_clock_seconds', base['clock_seconds']),
            field='p2_clock_seconds',
            minimum=10.0,
            maximum=21600.0,
        )
        p1_starting_words = _coerce_float(
            payload.get('p1_starting_words', base['starting_words']),
            field='p1_starting_words',
            minimum=0.0,
            maximum=500.0,
        )
        p2_starting_words = _coerce_float(
            payload.get('p2_starting_words', base['starting_words']),
            field='p2_starting_words',
            minimum=0.0,
            maximum=500.0,
        )
        starting_player_raw = payload.get('starting_player', 1)
        if isinstance(starting_player_raw, str) and starting_player_raw.strip().lower() == 'random':
            starting_player = random.choice((1, 2))
        else:
            starting_player = _coerce_int(
                starting_player_raw,
                field='starting_player',
                allowed={1, 2},
            )
    else:
        p1_clock_seconds = base['clock_seconds']
        p2_clock_seconds = base['clock_seconds']
        p1_starting_words = base['starting_words']
        p2_starting_words = base['starting_words']
        starting_player = 1

    return {
        'preset': preset,
        'size': base['board_size'],
        'op_limit': base['op_limit'],
        'clock_seconds': base['clock_seconds'],
        'word_rate': base['word_rate'],
        'starting_player': starting_player,
        'p1_clock_seconds': p1_clock_seconds,
        'p2_clock_seconds': p2_clock_seconds,
        'p1_starting_words': p1_starting_words,
        'p2_starting_words': p2_starting_words,
        'accommodations_enabled': accommodations_enabled,
    }


def _player_slot_for_game(account_id, game):
    if game.player1_id == account_id:
        return 1
    if game.player2_id == account_id:
        return 2
    return None


def _make_recent_games(account):
    all_games = (
        Game.query
        .filter(or_(Game.player1_id == account.id, Game.player2_id == account.id))
        .order_by(Game.finished_at.desc(), Game.created_at.desc())
        .all()
    )
    finished = [game for game in all_games if game.status == 'finished']

    wins = 0
    losses = 0
    for game in finished:
        user_slot = _player_slot_for_game(account.id, game)
        if user_slot is None or game.winner is None:
            continue
        if game.winner == user_slot:
            wins += 1
        elif game.winner in (1, 2):
            losses += 1

    rows = _build_my_game_rows(account)[:4]

    return {
        'wins': wins,
        'losses': losses,
        'games_played': len(finished),
        'recent_games': rows,
    }


def _unique_deleted_username(account_id):
    base = Config.DELETED_USERNAME
    existing = Account.query.filter(Account.username == base, Account.id != account_id).first()
    if existing is None:
        return base

    suffix = 1
    while True:
        candidate = f'{base}#{account_id}-{suffix}'
        clash = Account.query.filter(Account.username == candidate, Account.id != account_id).first()
        if clash is None:
            return candidate
        suffix += 1


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        next_url = request.form.get('next', '')
        account = Account.query.filter_by(username=username).first()
        if account and account.check_password(password):
            login_user(account)
            parsed = urlsplit(next_url)
            if next_url and not parsed.scheme and not parsed.netloc:
                return redirect(next_url)
            return redirect(url_for('main.index'))
        flash('Invalid username or password.')
    else:
        next_url = request.args.get('next', '')

    return render_template('login.html', next=next_url)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/')
def index():
    total_games = Game.query.count()
    return render_template('index.html', total_games=total_games)


@bp.route('/new-game')
def new_game_legacy():
    return redirect(url_for('main.game_new'))


@bp.route('/game/new')
def game_new():
    preset_order = ('60', '30', '15', '5')
    preset_icons = {
        '60': 'hourglass_top',
        '30': 'timer',
        '15': 'speed',
        '5': 'rocket',
        'custom': 'alarm_smart_wake',
    }
    preset_param = request.args.get('preset', '5')
    if preset_param not in ('60', '30', '15', '5', 'custom'):
        preset_param = '5'
    return render_template(
        'game_new.html',
        presets=Config.TIME_CONTROL_PRESETS,
        preset_order=preset_order,
        preset_icons=preset_icons,
        board_size_stops=Config.BOARD_SIZE_STOPS,
        default_preset=preset_param,
        username=current_user.username if current_user.is_authenticated else '',
    )


@bp.route('/game/<game_id>')
def game_page(game_id):
    session = get_session(game_id)
    if session is None:
        return render_template('stub.html', page_title='Game not found'), 404
    player_num = None
    if current_user.is_authenticated:
        if session._player_ids.get(1) == current_user.id:
            player_num = 1
        elif session._player_ids.get(2) == current_user.id:
            player_num = 2
    return render_template('game.html', game_id=game_id, player_num=player_num)


def _fmt_duration(seconds):
    """Format a number of seconds as 'Xm Ys' or 'Ys'."""
    if seconds is None:
        return '—'
    m = int(seconds // 60)
    s = int(seconds % 60)
    if m > 0:
        return f'{m}m {s:02d}s'
    return f'{s}s'


def _build_my_game_rows(account):
    """Build my-games timeline row data for an account, newest-first."""
    games = (
        Game.query
        .filter(
            (Game.player1_id == account.id) | (Game.player2_id == account.id)
        )
        .order_by(Game.created_at.desc())
        .all()
    )

    game_data = []
    for g in games:
        is_p1 = (g.player1_id == account.id)
        my_slot = 1 if is_p1 else 2
        opp_slot = 2 if is_p1 else 1

        opp = g.player2 if is_p1 else g.player1
        opp_username = opp.username if opp else None

        if g.is_draw:
            result = 'stalemate' if g.end_reason == 'stalemate' else 'draw'
        elif g.winner == my_slot:
            result = 'win'
        elif g.winner == opp_slot:
            result = 'loss'
        else:
            result = None

        last_phase = g.phases.order_by(ExecutionPhase.phase_number.desc()).first()
        turn_count = g.scripts.count()

        total_time_s = None
        if g.finished_at and g.created_at:
            total_time_s = (g.finished_at - g.created_at).total_seconds()

        # Parse clock remaining from last phase
        p1_clock_s = None
        p2_clock_s = None
        if last_phase and last_phase.clock_remaining_json:
            try:
                clk = json.loads(last_phase.clock_remaining_json)
                p1_clock_s = clk.get('1') or clk.get(1)
                p2_clock_s = clk.get('2') or clk.get(2)
            except (ValueError, TypeError):
                pass

        # Detect non-default settings
        preset_key = g.preset
        preset_defaults = Config.TIME_CONTROL_PRESETS.get(preset_key) if preset_key else None
        custom_settings = {}
        has_custom = False

        if preset_defaults and g.word_rate is not None:
            if abs(g.word_rate - preset_defaults['word_rate']) > 0.001:
                custom_settings['Word rate'] = g.word_rate
                has_custom = True

        if g.accommodations_enabled:
            has_custom = True
            if g.p1_clock_seconds is not None and g.clock_seconds is not None:
                if abs(g.p1_clock_seconds - g.clock_seconds) > 0.001:
                    custom_settings['P1 clock'] = _fmt_duration(g.p1_clock_seconds)
            if g.p2_clock_seconds is not None and g.clock_seconds is not None:
                if abs(g.p2_clock_seconds - g.clock_seconds) > 0.001:
                    custom_settings['P2 clock'] = _fmt_duration(g.p2_clock_seconds)
            if preset_defaults and g.p1_starting_words is not None:
                if abs(g.p1_starting_words - preset_defaults['starting_words']) > 0.001:
                    custom_settings['P1 starting words'] = int(g.p1_starting_words)
            if preset_defaults and g.p2_starting_words is not None:
                if abs(g.p2_starting_words - preset_defaults['starting_words']) > 0.001:
                    custom_settings['P2 starting words'] = int(g.p2_starting_words)

        game_data.append({
            'game_id': g.id,
            'is_p1': is_p1,
            'my_slot': my_slot,
            'opp_slot': opp_slot,
            'opponent_username': opp_username,
            'result': result,
            'end_reason': g.end_reason,
            'board_size': g.board_size,
            'preset': g.preset,
            'clock_seconds': g.clock_seconds,
            'accommodations_enabled': g.accommodations_enabled,
            'final_board_json': last_phase.board_state_json if last_phase else None,
            'p1_clock_remaining': _fmt_duration(p1_clock_s),
            'p2_clock_remaining': _fmt_duration(p2_clock_s),
            'total_turns': turn_count,
            'total_time': _fmt_duration(total_time_s),
            'finished_at': g.finished_at,
            'has_custom': has_custom,
            'custom_settings': custom_settings,
            'status': g.status,
        })

    return game_data


@bp.route('/my-games')
@login_required
def my_games():
    game_data = _build_my_game_rows(current_user)

    finished = [g for g in game_data if g['status'] == 'finished']
    featured_games = finished[:1]

    return render_template('my_games.html', game_data=game_data, featured_games=featured_games)


@bp.route('/my-games/<game_id>')
@login_required
def my_game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    if game.player1_id != current_user.id and game.player2_id != current_user.id:
        return render_template('stub.html', page_title='Not found'), 404

    is_p1 = (game.player1_id == current_user.id)
    my_slot = 1 if is_p1 else 2
    opp_slot = 2 if is_p1 else 1

    opp = game.player2 if is_p1 else game.player1
    opponent_username = opp.username if opp else '(unknown)'

    # Result
    if game.is_draw:
        result = 'stalemate' if game.end_reason == 'stalemate' else 'draw'
    elif game.winner == my_slot:
        result = 'win'
    elif game.winner == opp_slot:
        result = 'loss'
    else:
        result = None

    # Game duration
    total_time_s = None
    if game.finished_at and game.created_at:
        total_time_s = (game.finished_at - game.created_at).total_seconds()

    phases = (
        game.phases
        .order_by(ExecutionPhase.phase_number)
        .all()
    )
    scripts = (
        game.scripts
        .filter_by(account_id=current_user.id)
        .order_by(Script.turn_number)
        .all()
    )
    all_functions = (
        game.functions
        .filter_by(account_id=current_user.id)
        .order_by(DefinedFunction.id)
        .all()
    )

    # Clocks at game end (last phase)
    p1_clock_s = None
    p2_clock_s = None
    if phases:
        last_clk_json = phases[-1].clock_remaining_json
        if last_clk_json:
            try:
                clk = json.loads(last_clk_json)
                p1_clock_s = clk.get('1') or clk.get(1)
                p2_clock_s = clk.get('2') or clk.get(2)
            except (ValueError, TypeError):
                pass

    # Average write duration for my turns
    my_durations = [
        s.write_duration_seconds for s in scripts
        if s.write_duration_seconds is not None
    ]
    avg_write_s = (sum(my_durations) / len(my_durations)) if my_durations else None

    # Custom settings detection (same logic as my_games)
    preset_key = game.preset
    preset_defaults = Config.TIME_CONTROL_PRESETS.get(preset_key) if preset_key else None
    custom_settings = {}
    has_custom = False

    if preset_defaults and game.word_rate is not None:
        if abs(game.word_rate - preset_defaults['word_rate']) > 0.001:
            custom_settings['Word rate'] = game.word_rate
            has_custom = True

    if game.accommodations_enabled:
        has_custom = True
        if game.p1_clock_seconds is not None and game.clock_seconds is not None:
            if abs(game.p1_clock_seconds - game.clock_seconds) > 0.001:
                custom_settings['P1 clock'] = _fmt_duration(game.p1_clock_seconds)
        if game.p2_clock_seconds is not None and game.clock_seconds is not None:
            if abs(game.p2_clock_seconds - game.clock_seconds) > 0.001:
                custom_settings['P2 clock'] = _fmt_duration(game.p2_clock_seconds)
        if preset_defaults and game.p1_starting_words is not None:
            if abs(game.p1_starting_words - preset_defaults['starting_words']) > 0.001:
                custom_settings['P1 starting words'] = int(game.p1_starting_words)
        if preset_defaults and game.p2_starting_words is not None:
            if abs(game.p2_starting_words - preset_defaults['starting_words']) > 0.001:
                custom_settings['P2 starting words'] = int(game.p2_starting_words)

    # Build phases_meta JSON — includes coverage % (cheap to compute here,
    # avoids N client requests for the dominance graph)
    board_size = game.board_size or 8
    total_cells = board_size * board_size
    phases_meta = []
    for p in phases:
        coverage_p1 = 0.0
        coverage_p2 = 0.0
        if p.board_state_json:
            try:
                board_raw = json.loads(p.board_state_json)
                p1_cells = sum(1 for row in board_raw for cell in row if cell[0] > cell[1])
                p2_cells = sum(1 for row in board_raw for cell in row if cell[1] > cell[0])
                coverage_p1 = round(p1_cells / total_cells * 100, 1)
                coverage_p2 = round(p2_cells / total_cells * 100, 1)
            except (ValueError, TypeError, IndexError):
                pass

        clock_remaining = {}
        if p.clock_remaining_json:
            try:
                clock_remaining = json.loads(p.clock_remaining_json)
            except (ValueError, TypeError):
                pass

        phases_meta.append({
            'phase_number': p.phase_number,
            'exec_type': p.exec_type,
            'player_slot': p.player_slot,
            'ops_consumed': p.ops_consumed,
            'clock_remaining': clock_remaining,
            'script_id': p.script_id,
            'coverage_p1': coverage_p1,
            'coverage_p2': coverage_p2,
        })

    # Scripts metadata
    scripts_meta = [
        {
            'id': s.id,
            'turn': s.turn_number,
            'word_count': s.word_count,
            'write_duration': s.write_duration_seconds,
            'source': s.source_text,
            'player_slot': s.player_slot,
        }
        for s in scripts
    ]

    # Opponent write times — write_duration only, no script content
    opp_id = game.player2_id if is_p1 else game.player1_id
    opp_scripts = (
        Script.query
        .filter_by(game_id=game.id, account_id=opp_id)
        .order_by(Script.turn_number)
        .all()
    )
    opp_write_times = [
        {'turn': s.turn_number, 'write_duration': s.write_duration_seconds}
        for s in opp_scripts
    ]

    # Functions metadata — de-duplicate by name (keep latest definition)
    seen_funcs = {}
    for f in all_functions:
        seen_funcs[f.func_name] = f

    functions_meta = []
    for f in seen_funcs.values():
        first_line = f.func_body_text.split('\n')[0] if f.func_body_text else ''
        args = []
        m = re.search(r'\(([^)]*)\)', first_line)
        if m:
            args_str = m.group(1).strip()
            if args_str:
                args = [a.strip() for a in args_str.split(',') if a.strip()]
        defined_at_turn = f.script.turn_number if f.script else None
        functions_meta.append({
            'name': f.func_name,
            'args': args,
            'source': f.func_body_text,
            'defined_at_turn': defined_at_turn,
        })

    # Finished datetime formatted for display
    finished_at_str = (
        game.finished_at.strftime('%-d %b %Y, %-I:%M %p')
        if game.finished_at else '—'
    )

    return render_template(
        'my_game_detail.html',
        game=game,
        game_id_short=game.id[:8],
        my_slot=my_slot,
        opp_slot=opp_slot,
        opponent_username=opponent_username,
        result=result,
        total_turns=len(scripts),
        total_time=_fmt_duration(total_time_s),
        p1_clock_remaining=_fmt_duration(p1_clock_s),
        p2_clock_remaining=_fmt_duration(p2_clock_s),
        avg_write_duration=(_fmt_duration(avg_write_s) if avg_write_s is not None else '—'),
        finished_at_str=finished_at_str,
        has_custom=has_custom,
        custom_settings=custom_settings,
        phases_meta_json=json.dumps(phases_meta),
        scripts_meta_json=json.dumps(scripts_meta),
        functions_meta_json=json.dumps(functions_meta),
        opp_write_times_json=json.dumps(opp_write_times),
    )


@bp.route('/how-to-play')
def how_to_play():
    return render_template('stub.html', page_title='How to Play')


@bp.route('/settings/profile')
@login_required
def settings_profile():
    stats = _make_recent_games(current_user)
    return render_template('settings_profile.html', settings_nav='profile', stats=stats)


@bp.route('/settings/account', methods=['GET', 'POST'])
@login_required
def settings_account():
    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'change_username':
            new_username = request.form.get('username', '').strip()
            if not new_username:
                flash('Username cannot be empty.')
            elif new_username != current_user.username and Account.query.filter_by(username=new_username).first():
                flash('That username is already in use.')
            else:
                current_user.username = new_username
                db.session.commit()
                flash('Username updated.')

        elif action == 'change_email':
            new_email = request.form.get('email', '').strip()
            if not _valid_email(new_email):
                flash('Please enter a valid email address.')
            elif new_email != (current_user.email or '') and Account.query.filter_by(email=new_email).first():
                flash('That email is already in use.')
            else:
                current_user.email = new_email
                db.session.commit()
                flash('Email updated.')

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not current_user.check_password(current_password):
                flash('Current password is incorrect.')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters.')
            elif new_password != confirm_password:
                flash('New password and confirmation do not match.')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password updated.')

        elif action == 'disable_account':
            current_user.disabled = True
            db.session.commit()
            flash('Account disabled flag set.')

        elif action == 'delete_account':
            confirmation = request.form.get('confirm_username', '').strip()
            if confirmation != current_user.username:
                flash('Username confirmation did not match.')
            else:
                current_user.deleted = True
                current_user.disabled = True
                current_user.email = None
                current_user.set_password(str(uuid.uuid4()))
                current_user.username = _unique_deleted_username(current_user.id)
                # Scrub private data: clear script text, delete function entries
                Script.query.filter_by(account_id=current_user.id).update(
                    {'account_id': None, 'source_text': ''},
                )
                DefinedFunction.query.filter_by(account_id=current_user.id).delete()
                db.session.commit()
                logout_user()
                flash('Account deleted and anonymized.')
                return redirect(url_for('main.login'))

    return render_template('settings_account.html', settings_nav='account')


@bp.route('/settings/game', methods=['GET', 'POST'])
@login_required
def settings_game():
    settings = _get_or_create_settings(current_user)
    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'save_defaults':
            time_control = request.form.get('time_control', Config.DEFAULT_TIME_CONTROL)
            if time_control not in Config.TIME_CONTROL_PRESETS and time_control != 'custom':
                flash('Invalid time control option.')
            else:
                custom_minutes = settings.custom_minutes
                if time_control == 'custom':
                    try:
                        custom_minutes = int(request.form.get('custom_minutes', Config.DEFAULT_CUSTOM_MINUTES))
                    except (TypeError, ValueError):
                        custom_minutes = Config.DEFAULT_CUSTOM_MINUTES
                    custom_minutes = max(1, min(custom_minutes, 180))
                else:
                    custom_minutes = None

                default_player = request.form.get('default_player', Config.DEFAULT_PLAYER_CHOICE)
                if default_player not in ('p1', 'p2', 'random'):
                    default_player = Config.DEFAULT_PLAYER_CHOICE

                try:
                    board_size = int(request.form.get('default_board_size', Config.BOARD_SIZE))
                except (TypeError, ValueError):
                    board_size = Config.BOARD_SIZE
                board_size = _closest_board_size(board_size)

                settings.default_time_control = time_control
                settings.custom_minutes = custom_minutes
                settings.default_player = default_player
                settings.default_board_size = board_size
                db.session.commit()
                flash('Game defaults saved.')

            return redirect(url_for('main.settings_game', _anchor='defaults'))

        if action == 'save_palette':
            palette = request.form.get('palette', Config.DEFAULT_PALETTE)
            if palette not in _PALETTES:
                flash('Invalid palette selection.')
            else:
                settings.palette = palette
                db.session.commit()
                flash('Appearance saved.')
            return redirect(url_for('main.settings_game', _anchor='appearance'))

    return render_template(
        'settings_game.html',
        settings_nav='game',
        settings=settings,
        board_size_stops=Config.BOARD_SIZE_STOPS,
        time_controls=('60', '30', '15', '5', 'custom'),
    )


@bp.route('/settings/feedback')
@login_required
def settings_feedback():
    return render_template('settings_feedback.html', settings_nav='feedback')


@bp.route('/settings/about-legal')
@login_required
def settings_about_legal():
    return render_template('settings_about_legal.html', settings_nav='about-legal')


@bp.route('/contact', methods=['GET', 'POST'])
@bp.route('/legal/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        log_file = 'legal_contact.log' if request.path.startswith('/legal') else 'contact.log'
        _log_contact(
            log_file,
            name=request.form.get('name', '').strip(),
            email=request.form.get('email', '').strip(),
            message=request.form.get('message', '').strip(),
        )
        if request.form.get('form_source') == 'settings-feedback' and current_user.is_authenticated:
            flash('Thanks for the feedback.')
            return redirect(url_for('main.settings_feedback'))
    return render_template('contact.html')


@bp.route('/legal/terms')
def legal_terms():
    return render_template('terms_of_use.html')


@bp.route('/legal/cookies')
def legal_cookies():
    return render_template('cookies.html')


@bp.route('/legal/privacy')
def legal_privacy():
    return render_template('privacy-policy.html')


@bp.route('/games', methods=['POST'])
@bp.route('/game', methods=['POST'])
@login_required
def create_game():
    """
    Create a new game. player1 is always the logged-in user.

    JSON body (optional):
        { "player2_id": <int> }

    Returns:
        { "game_id": <str> }
    """
    data = request.get_json(silent=True) or {}
    player2_id = data.get('player2_id')

    game = Game(player1_id=current_user.id, player2_id=player2_id, status='active')
    default_settings = {
        'preset': None,
        'size': Config.BOARD_SIZE,
        'op_limit': Config.OP_LIMIT,
        'clock_seconds': Config.CLOCK_SECONDS,
        'word_rate': Config.WORD_RATE,
        'starting_player': 1,
        'accommodations_enabled': False,
        'p1_clock_seconds': Config.CLOCK_SECONDS,
        'p2_clock_seconds': Config.CLOCK_SECONDS,
        'p1_starting_words': 0.0,
        'p2_starting_words': 0.0,
    }
    _populate_game_settings(game, default_settings, created_by=current_user.id)
    db.session.add(game)
    db.session.commit()

    session = create_session(
        game_id=game.id,
        size=Config.BOARD_SIZE,
        op_limit=Config.OP_LIMIT,
        clock_seconds=Config.CLOCK_SECONDS,
        word_rate=Config.WORD_RATE,
    )
    session.set_players(current_user.id, player2_id)

    return jsonify({"game_id": game.id}), 201


@bp.route('/game/lobby', methods=['POST'])
@login_required
def game_create_lobby():
    """Create a pending multiplayer lobby. Returns game_id immediately; session is created only when both players ready."""
    data = request.get_json(silent=True) or {}
    try:
        parsed = _parse_session_config(data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    game_id = str(uuid.uuid4())
    alias = _gen_join_alias()
    create_lobby(game_id, parsed, current_user.id, current_user.username, join_alias=alias)
    return jsonify({'game_id': game_id, 'join_alias': alias}), 201


@bp.route('/join/<alias>', methods=['GET'])
def join_by_alias(alias):
    lobby = get_lobby_by_alias(alias)
    if lobby is None:
        return render_template('stub.html', page_title='Game not found'), 404
    return redirect(url_for('main.game_join_page', game_id=lobby.game_id))


@bp.route('/game/<game_id>/join', methods=['GET'])
@login_required
def game_join_page(game_id):
    session = get_session(game_id)
    if session is not None:
        player_ids = [session._player_ids[1], session._player_ids[2]]
        if not session.game_over and current_user.id in player_ids:
            return redirect(url_for('main.game_page', game_id=game_id))
        return render_template('stub.html', page_title='Game not found'), 404
    lobby = get_lobby(game_id)
    if lobby is None:
        return render_template('stub.html', page_title='Game not found'), 404
    return render_template(
        'game_join.html',
        game_id=game_id,
        settings=lobby.settings,
        p1_username=lobby.player1_username,
    )


@bp.route('/game/<game_id>/join', methods=['POST'])
@login_required
def game_join(game_id):
    lobby = get_lobby(game_id)
    if lobby is None:
        return jsonify({'error': 'game not found'}), 404
    if current_user.id == lobby.player1_id:
        return jsonify({'error': 'cannot join your own game'}), 400
    if lobby.player2_id is not None and lobby.player2_id != current_user.id:
        return jsonify({'error': 'game is full'}), 409
    lobby.player2_id = current_user.id
    lobby.player2_username = current_user.username
    return jsonify({'ok': True}), 200


@bp.route('/game/<game_id>/settings', methods=['PATCH'])
@login_required
def game_update_lobby_settings(game_id):
    lobby = get_lobby(game_id)
    if lobby is None:
        return jsonify({'error': 'game not found'}), 404
    if current_user.id != lobby.player1_id:
        return jsonify({'error': 'forbidden'}), 403
    data = request.get_json(silent=True) or {}
    try:
        parsed = _parse_session_config(data)
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    lobby.settings = parsed
    return jsonify({'ok': True})


@bp.route('/game/<game_id>/lobby', methods=['GET'])
def game_lobby_status(game_id):
    lobby = get_lobby(game_id)
    session = get_session(game_id)
    if session is not None:
        return jsonify({
            "player2_joined": True,
            "player2_username": None,
            "player1_ready": True,
            "player2_ready": True,
            "both_ready": True,
            "started": True,
        })
    if lobby is not None:
        return jsonify(lobby.lobby_status())
    return jsonify({'error': 'game not found'}), 404


@bp.route('/game/<game_id>/ready', methods=['POST'])
@login_required
def game_ready(game_id):
    lobby = get_lobby(game_id)
    if lobby is None:
        return jsonify({'error': 'game not found'}), 404
    if current_user.id == lobby.player1_id:
        lobby.player1_ready = not lobby.player1_ready
        ready = lobby.player1_ready
    elif current_user.id == lobby.player2_id:
        lobby.player2_ready = not lobby.player2_ready
        ready = lobby.player2_ready
    else:
        return jsonify({'error': 'forbidden'}), 403

    status = lobby.lobby_status()
    if status['both_ready']:
        _start_lobby_game(game_id, lobby)
        return jsonify({'ready': True, 'both_ready': True})
    return jsonify({'ready': ready, 'both_ready': False})


@bp.route('/game/<game_id>/leave', methods=['POST'])
@login_required
def game_leave(game_id):
    lobby = get_lobby(game_id)
    if lobby is None:
        return jsonify({'error': 'game not found'}), 404
    if current_user.id != lobby.player2_id:
        return jsonify({'error': 'forbidden'}), 403
    lobby.player2_id = None
    lobby.player2_username = None
    lobby.player2_ready = False
    lobby.player1_ready = False
    return jsonify({'ok': True})


@bp.route('/game/<game_id>/close', methods=['POST'])
@login_required
def game_close(game_id):
    lobby = get_lobby(game_id)
    if lobby is None:
        return jsonify({'error': 'game not found'}), 404
    if current_user.id != lobby.player1_id:
        return jsonify({'error': 'forbidden'}), 403
    remove_lobby(game_id)
    return jsonify({'ok': True})


def _start_lobby_game(game_id: str, lobby) -> None:
    """Create a real GameSession from a ready lobby, then remove the lobby."""
    parsed = lobby.settings

    game = Game(
        id=game_id,
        player1_id=lobby.player1_id,
        player2_id=lobby.player2_id,
        status='active',
        join_alias=lobby.join_alias or None,
    )
    _populate_game_settings(game, parsed, created_by=lobby.player1_id)
    db.session.add(game)
    db.session.commit()

    session = create_session(
        game_id=game_id,
        size=parsed['size'],
        op_limit=parsed['op_limit'],
        clock_seconds=parsed['clock_seconds'],
        word_rate=parsed['word_rate'],
        starting_player=parsed['starting_player'],
    )
    session.engine._word_bank[1] = parsed['p1_starting_words']
    session.engine._word_bank[2] = parsed['p2_starting_words']
    session.engine._word_tick[1] = None
    session.engine._word_tick[2] = None
    session.engine._clock_remaining[1] = parsed['p1_clock_seconds']
    session.engine._clock_remaining[2] = parsed['p2_clock_seconds']
    session.engine._clock_tick[1] = None
    session.engine._clock_tick[2] = None
    session.set_players(lobby.player1_id, lobby.player2_id)
    remove_lobby(game_id)


@bp.route('/game/<game_id>/compile', methods=['POST'])
@login_required
def game_compile_script(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    source = data.get('source', '')

    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    result = session.compile_script(player, source, user_id=user_id)
    if not result.get('ok') and 'forbidden' in result.get('errors', []):
        return jsonify({'error': 'forbidden'}), 403
    return jsonify(result)


@bp.route('/game/<game_id>/deploy', methods=['POST'])
@login_required
def game_deploy_script(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    source = data.get('source', '')

    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    result = session.deploy_script(player, source, user_id=user_id)
    if not result.get('ok') and 'forbidden' in result.get('errors', []):
        return jsonify({'error': 'forbidden'}), 403
    status = 200 if result.get('ok') else 422
    return jsonify(result), status


@bp.route('/game/<game_id>/resign', methods=['POST'])
def game_resign(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    result = session.resign(player, user_id=user_id)
    if not result.get('ok'):
        return jsonify(result), 403
    return jsonify(result)


@bp.route('/game/<game_id>/offer_draw', methods=['POST'])
def game_offer_draw(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    result = session.offer_draw(player, user_id=user_id)
    if not result.get('ok'):
        return jsonify(result), 403
    return jsonify(result)


@bp.route('/game/<game_id>/cancel_draw', methods=['POST'])
def game_cancel_draw(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    result = session.cancel_draw(player, user_id=user_id)
    if not result.get('ok'):
        return jsonify(result), 403
    return jsonify(result)


@bp.route('/game/<game_id>/accept_draw', methods=['POST'])
def game_accept_draw(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    result = session.accept_draw(player, user_id=user_id)
    if not result.get('ok'):
        return jsonify(result), 403
    return jsonify(result)


@bp.route('/game/<game_id>/reject_draw', methods=['POST'])
def game_reject_draw(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400

    user_id = current_user.id if current_user.is_authenticated else None
    result = session.reject_draw(player, user_id=user_id)
    if not result.get('ok'):
        return jsonify(result), 403
    return jsonify(result)


@bp.route('/game/<game_id>/begin_write', methods=['POST'])
def game_begin_write(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    if player not in (1, 2):
        return jsonify({'error': 'player must be 1 or 2'}), 400
    if player != session.current_player:
        return jsonify({'error': 'forbidden'}), 403
    user_id = current_user.id if current_user.is_authenticated else None
    if user_id != session._player_ids.get(player):
        return jsonify({'error': 'forbidden'}), 403

    session.skip_opening_pre_write()
    return jsonify({'ok': True})


@bp.route('/game/<game_id>/state', methods=['GET'])
def game_state(game_id):
    session = get_session(game_id)
    if session is None:
        return jsonify({'error': 'game not found'}), 404

    for_player = None
    if current_user.is_authenticated:
        if session._player_ids.get(1) == current_user.id:
            for_player = 1
        elif session._player_ids.get(2) == current_user.id:
            for_player = 2

    session.check_clock_expired()
    state = session.get_state(for_player=for_player)
    state['total_phases'] = ExecutionPhase.query.filter_by(game_id=game_id).count()
    return jsonify(state)


@bp.route('/game/<game_id>/state/<int:phase_number>', methods=['GET'])
def game_phase_state(game_id, phase_number):
    import json as _json

    game = Game.query.get(game_id)
    if game is None:
        return jsonify({'error': 'game not found'}), 404

    phase = (
        ExecutionPhase.query
        .filter_by(game_id=game_id, phase_number=phase_number)
        .first()
    )
    if phase is None:
        return jsonify({'error': 'phase not found'}), 404

    total_phases = (
        ExecutionPhase.query
        .filter_by(game_id=game_id)
        .count()
    )

    board_raw = _json.loads(phase.board_state_json)
    # Stored as [[p1, p2], ...] tuples; convert to [{"p1": p1, "p2": p2}, ...] for the client
    board = [[{'p1': cell[0], 'p2': cell[1]} for cell in row] for row in board_raw]
    agents_raw = _json.loads(phase.agents_json)
    exec_log = _json.loads(phase.exec_log_json) if phase.exec_log_json else []

    return jsonify({
        'board': board,
        'agents': agents_raw,
        'exec_log': exec_log,
        'exec_ops_consumed': phase.ops_consumed,
        'op_limit': game.op_limit,
        'phase_number': phase.phase_number,
        'total_phases': total_phases,
        'exec_type': phase.exec_type,
        'player_slot': phase.player_slot,
    })


@bp.route('/game/<game_id>/scripts', methods=['GET'])
@login_required
def game_scripts(game_id):
    game = Game.query.get(game_id)
    if game is None:
        return jsonify({'error': 'game not found'}), 404

    if game.player1_id != current_user.id and game.player2_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403

    scripts = (
        Script.query
        .filter_by(game_id=game_id, account_id=current_user.id)
        .order_by(Script.turn_number)
        .all()
    )

    return jsonify([
        {'turn': s.turn_number, 'source': s.source_text}
        for s in scripts
    ])


@bp.route('/game/<game_id>/functions', methods=['GET'])
@login_required
def game_functions(game_id):
    game = Game.query.get(game_id)
    if game is None:
        return jsonify({'error': 'game not found'}), 404

    if game.player1_id != current_user.id and game.player2_id != current_user.id:
        return jsonify({'error': 'forbidden'}), 403

    functions = (
        DefinedFunction.query
        .filter_by(game_id=game_id, account_id=current_user.id)
        .order_by(DefinedFunction.id)
        .all()
    )

    # Keep latest definition per name (functions can be redefined across turns)
    seen = {}
    for f in functions:
        seen[f.func_name] = f

    result = []
    for f in seen.values():
        first_line = f.func_body_text.split('\n')[0] if f.func_body_text else ''
        args = []
        m = re.search(r'\(([^)]*)\)', first_line)
        if m:
            args_str = m.group(1).strip()
            if args_str:
                args = [a.strip() for a in args_str.split(',') if a.strip()]
        result.append({
            'name': f.func_name,
            'args': args,
            'source': f.func_body_text,
        })

    return jsonify(result)
