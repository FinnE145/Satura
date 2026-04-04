from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
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


@login_manager.user_loader
def load_user(user_id):
    from app.models import Account
    return Account.query.get(int(user_id))
