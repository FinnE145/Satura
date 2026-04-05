# [AI Summary] Flask route handlers for all HTTP endpoints: game creation,
# script submission, state polling, and real-time compiler feedback.
# Imports: app/game/session.py, app/game/engine.py, app/lang/compiler.py,
#          app/lang/interpreter.py. Imported by: app/__init__.py.

import uuid

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import db
from .models import Game, Account
from .game.session import create_session, get_session
from config import Config

bp = Blueprint('main', __name__)


def _player_authorized(game, player):
    """Return True if current_user is the account for the given player slot."""
    if player == 1:
        return current_user.id == game.player1_id
    if player == 2:
        return current_user.id == game.player2_id
    return False


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
    return redirect(url_for('main.login'))


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


@bp.route('/profile')
def profile():
    return render_template('stub.html', page_title='Profile')


@bp.route('/settings')
def settings_page():
    return render_template('stub.html', page_title='Settings')


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
    No DB accounts required. Animation is skipped and both word banks
    are pre-filled so the user can compile and deploy immediately.
    """
    game_id = str(uuid.uuid4())
    session = create_session(
        game_id=game_id,
        size=Config.BOARD_SIZE,
        op_limit=Config.OP_LIMIT,
        clock_seconds=Config.TEST_CLOCK_SECONDS,
        word_rate=Config.TEST_WORD_RATE,
    )
    # Skip the initial animation so the session is immediately in write phase
    session._anim_deadline = 0
    session._maybe_advance_animation()
    # Start with a pre-loaded bank; accrues at TEST_WORD_RATE from there
    session.engine._word_bank[1] = Config.TEST_WORD_BANK_START
    session.engine._word_bank[2] = Config.TEST_WORD_BANK_START
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
