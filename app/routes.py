# [AI Summary] Flask route handlers for all HTTP endpoints: game creation,
# script submission, state polling, and real-time compiler feedback.
# Imports: app/game/session.py, app/game/engine.py, app/lang/compiler.py,
#          app/lang/interpreter.py. Imported by: app/__init__.py.

from flask import Blueprint, request, jsonify, render_template
from . import db
from .models import Game, Account
from .game.session import create_session, get_session

bp = Blueprint('main', __name__)

# Game defaults — move to Config when tuning is needed
_BOARD_SIZE = 16
_OP_LIMIT = 25
_CLOCK_SECONDS = 300.0
_WORD_RATE = 2.0


@bp.route('/')
def index():
    return render_template('index.html')


@bp.route('/games', methods=['POST'])
def create_game():
    """
    Create a new game.

    JSON body:
        { "player1_id": <int>, "player2_id": <int> }

    Returns:
        { "game_id": <str> }
    """
    data = request.get_json(silent=True) or {}
    player1_id = data.get('player1_id')
    player2_id = data.get('player2_id')

    if not player1_id:
        return jsonify({"error": "player1_id required"}), 400

    game = Game(player1_id=player1_id, player2_id=player2_id, status='active')
    db.session.add(game)
    db.session.commit()

    create_session(
        game_id=game.id,
        size=_BOARD_SIZE,
        op_limit=_OP_LIMIT,
        clock_seconds=_CLOCK_SECONDS,
        word_rate=_WORD_RATE,
    )

    return jsonify({"game_id": game.id}), 201


@bp.route('/games/<game_id>/compile', methods=['POST'])
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

    result = session.compile_script(player, source)
    return jsonify(result)


@bp.route('/games/<game_id>/deploy', methods=['POST'])
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

    result = session.deploy_script(player, source)
    status = 200 if result.get('ok') else 422
    return jsonify(result), status


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
