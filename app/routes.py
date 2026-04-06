# [AI Summary] Flask route handlers for all HTTP endpoints: game creation,
# script submission, state polling, and real-time compiler feedback.
# Imports: app/game/session.py, app/game/engine.py, app/lang/compiler.py,
#          app/lang/interpreter.py. Imported by: app/__init__.py.

import uuid
import re
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_
from . import db
from .models import Game, Account, AccountSettings
from .game.session import create_session, get_session
from config import Config

bp = Blueprint('main', __name__)

_LOG_DIR = Path(__file__).parent.parent
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


def _player_authorized(game, player):
    """Return True if current_user is the account for the given player slot."""
    if player == 1:
        return current_user.id == game.player1_id
    if player == 2:
        return current_user.id == game.player2_id
    return False


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

    rows = []
    for game in finished[:6]:
        user_slot = _player_slot_for_game(account.id, game)
        opponent = game.player2 if user_slot == 1 else game.player1
        opponent_name = opponent.username if opponent is not None else 'Unassigned'

        if game.winner is None:
            result = 'Draw'
            why = 'Stalemate'
        elif user_slot == game.winner:
            result = 'Won'
            why = 'Board control at finish'
        else:
            result = 'Lost'
            why = 'Opponent reached control threshold'

        rows.append({
            'opponent': opponent_name,
            'turns': '--',
            'result': result,
            'why': why,
            'game_id': game.id,
        })

    while len(rows) < 4:
        idx = len(rows) + 1
        rows.append({
            'opponent': '—',
            'turns': '--',
            'result': '—',
            'why': 'Data pending',
            'game_id': f'placeholder-{idx}',
        })

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
        account = Account.query.filter_by(username=username).first()
        if account and account.check_password(password):
            login_user(account)
            return redirect(url_for('main.index'))
        flash('Invalid username or password.')

    return render_template('login.html')


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
def new_game():
    return render_template('stub.html', page_title='New Game')


@bp.route('/my-games')
def my_games():
    return render_template('stub.html', page_title='My Games')


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
                # TODO: remove user-owned script/function rows once those tables exist;
                # keep shared game history and opponent-authored artifacts.
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
    db.session.add(game)
    db.session.commit()

    create_session(
        game_id=game.id,
        size=Config.BOARD_SIZE,
        op_limit=Config.OP_LIMIT,
        clock_seconds=Config.CLOCK_SECONDS,
        word_rate=Config.WORD_RATE,
    )

    return jsonify({"game_id": game.id}), 201


@bp.route('/games/<game_id>/compile', methods=['POST'])
@login_required
def compile_script(game_id):
    """
    Lint a script without advancing game state.

    JSON body:
        { "player": <1|2>, "source": <str> }

    Returns:
        { "ok": bool, "errors": [...], "warnings": [...], "word_count": int }
    """
    session = get_session(game_id)
    if session is None:
        return jsonify({"error": "game not found"}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    source = data.get('source', '')

    if player not in (1, 2):
        return jsonify({"error": "player must be 1 or 2"}), 400

    game = db.session.get(Game, game_id)
    if game is not None:
        if not current_user.is_authenticated or not _player_authorized(game, player):
            return jsonify({"error": "forbidden"}), 403

    result = session.compile_script(player, source)
    return jsonify(result)


@bp.route('/games/<game_id>/deploy', methods=['POST'])
@login_required
def deploy_script(game_id):
    """
    Deploy a script, ending the current write phase.

    JSON body:
        { "player": <1|2>, "source": <str> }

    Returns:
        { "ok": bool, "errors": [...], "warnings": [...], "game_over": bool, "winner": ... }
    """
    session = get_session(game_id)
    if session is None:
        return jsonify({"error": "game not found"}), 404

    data = request.get_json(silent=True) or {}
    player = data.get('player')
    source = data.get('source', '')

    if player not in (1, 2):
        return jsonify({"error": "player must be 1 or 2"}), 400

    game = db.session.get(Game, game_id)
    if game is not None:
        if not current_user.is_authenticated or not _player_authorized(game, player):
            return jsonify({"error": "forbidden"}), 403

    result = session.deploy_script(player, source)
    status = 200 if result.get('ok') else 422
    return jsonify(result), status


@bp.route('/test')
def test_page():
    return render_template('test.html')


@bp.route('/test/session', methods=['POST'])
def test_create_session():
    """
    Create a throw-away in-memory session for the test bench.
    No DB accounts required. Both word banks are pre-filled for quick
    compile/deploy testing once the normal animation phase advances.
    """
    game_id = str(uuid.uuid4())
    session = create_session(
        game_id=game_id,
        size=Config.BOARD_SIZE,
        op_limit=Config.OP_LIMIT,
        clock_seconds=Config.TEST_CLOCK_SECONDS,
        word_rate=Config.TEST_WORD_RATE,
    )
    # Start with a pre-loaded bank; accrues at TEST_WORD_RATE from there
    session.engine._word_bank[1] = Config.TEST_WORD_BANK_START
    session.engine._word_bank[2] = Config.TEST_WORD_BANK_START
    session.configure_auto_writer(
        player=2,
        first_script=Config.TEST_BOT_FIRST_SCRIPT,
        repeat_script=Config.TEST_BOT_REPEAT_SCRIPT,
        write_delay_seconds=Config.TEST_BOT_WRITE_DELAY_SECONDS,
    )
    return jsonify({"game_id": game_id}), 201


@bp.route('/games/<game_id>/state', methods=['GET'])
def game_state(game_id):
    """
    Poll current game state. Auto-advances animation phases and checks clock expiry.

    Returns full state dict.
    """
    session = get_session(game_id)
    if session is None:
        return jsonify({"error": "game not found"}), 404

    session.check_clock_expired()
    state = session.get_state()
    return jsonify(state)
