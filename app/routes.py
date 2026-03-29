# [AI Summary] Flask route handlers for all HTTP endpoints: game creation,
# script submission, state polling, and real-time compiler feedback.
# Imports: app/game/session.py, app/game/engine.py, app/lang/compiler.py,
#          app/lang/interpreter.py. Imported by: app/__init__.py.

from flask import Blueprint, request, jsonify, render_template

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    return render_template('index.html')
