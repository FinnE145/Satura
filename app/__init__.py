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

    from app.routes import bp
    app.register_blueprint(bp)

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
                    default_player VARCHAR(8) NOT NULL DEFAULT 'random',
                    default_board_size INTEGER NOT NULL DEFAULT 16,
                    palette VARCHAR(16) NOT NULL DEFAULT 'solstice',
                    FOREIGN KEY(account_id) REFERENCES accounts (id)
                )
                """
            ))


@login_manager.user_loader
def load_user(user_id):
    from app.models import Account
    return Account.query.get(int(user_id))
