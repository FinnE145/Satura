import json
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy import inspect, text
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    app.jinja_env.filters['fromjson'] = json.loads

    from app.routes import bp
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(_e):
        from flask import render_template
        return render_template('stub.html', page_title='Page Not Found'), 404

    with app.app_context():
        from app import models  # noqa: F401 — ensure models are registered
        db.create_all()
        _upgrade_schema()
        _seed_accounts()

    return app


def _seed_accounts():
    from app.models import Account

    accounts = [
        ('P1_Test', 'p1@test.com', 'test123'),
        ('P2_Test', 'p2@test.com', 'test123'),
    ]
    for username, email, password in accounts:
        if not Account.query.filter_by(username=username).first():
            account = Account(username=username, email=email)
            account.set_password(password)
            db.session.add(account)
    db.session.commit()


def _upgrade_schema():
    """Apply small, idempotent schema updates for local SQLite deployments."""
    inspector = inspect(db.engine)
    with db.engine.begin() as conn:
        if inspector.has_table('accounts'):
            account_cols = {col['name'] for col in inspector.get_columns('accounts')}
            if 'disabled' not in account_cols:
                conn.execute(text('ALTER TABLE accounts ADD COLUMN disabled BOOLEAN NOT NULL DEFAULT 0'))
            if 'deleted' not in account_cols:
                conn.execute(text('ALTER TABLE accounts ADD COLUMN deleted BOOLEAN NOT NULL DEFAULT 0'))

        if not inspector.has_table('account_settings'):
            conn.execute(text(
                """
                CREATE TABLE account_settings (
                    id INTEGER PRIMARY KEY,
                    account_id INTEGER NOT NULL UNIQUE,
                    default_time_control VARCHAR(16) NOT NULL DEFAULT '15',
                    custom_minutes INTEGER,
                    default_board_size INTEGER NOT NULL DEFAULT 16,
                    palette VARCHAR(16) NOT NULL DEFAULT 'solstice',
                    FOREIGN KEY(account_id) REFERENCES accounts (id)
                )
                """
            ))

        # -- Extend account_settings with custom/accom defaults --
        if inspector.has_table('account_settings'):
            settings_cols = {col['name'] for col in inspector.get_columns('account_settings')}
            new_settings_cols = {
                'custom_clock_seconds':    'REAL',
                'custom_board_size_val':   'INTEGER',
                'custom_op_limit':         'INTEGER',
                'custom_word_rate':        'REAL',
                'custom_starting_words':   'REAL',
                'accom_p1_clock_seconds':  'REAL',
                'accom_p2_clock_seconds':  'REAL',
                'accom_p1_starting_words': 'REAL',
                'accom_p2_starting_words': 'REAL',
                'accom_starting_player':   'VARCHAR(8)',
            }
            for col_name, col_def in new_settings_cols.items():
                if col_name not in settings_cols:
                    conn.execute(text(f'ALTER TABLE account_settings ADD COLUMN {col_name} {col_def}'))

        # -- Extend games table with settings/result columns --
        if inspector.has_table('games'):
            game_cols = {col['name'] for col in inspector.get_columns('games')}
            new_game_cols = {
                'preset':                  "VARCHAR(8)",
                'board_size':              "INTEGER",
                'op_limit':                "INTEGER",
                'clock_seconds':           "REAL",
                'word_rate':               "REAL",
                'starting_player':         "INTEGER",
                'accommodations_enabled':  "BOOLEAN NOT NULL DEFAULT 0",
                'p1_clock_seconds':        "REAL",
                'p2_clock_seconds':        "REAL",
                'p1_starting_words':       "REAL",
                'p2_starting_words':       "REAL",
                'end_reason':              "VARCHAR(16)",
                'is_draw':                 "BOOLEAN NOT NULL DEFAULT 0",
                'created_by':              "INTEGER",
            }
            for col_name, col_def in new_game_cols.items():
                if col_name not in game_cols:
                    conn.execute(text(f'ALTER TABLE games ADD COLUMN {col_name} {col_def}'))
            if 'join_alias' not in game_cols:
                conn.execute(text('ALTER TABLE games ADD COLUMN join_alias VARCHAR(6)'))
                conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS ix_games_join_alias ON games (join_alias)'))


@login_manager.user_loader
def load_user(user_id):
    from app.models import Account
    return Account.query.get(int(user_id))
