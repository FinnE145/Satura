import uuid
from datetime import datetime, timezone
from . import db


class Account(db.Model):
    __tablename__ = 'accounts'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, nullable=False,
                              default=lambda: datetime.now(timezone.utc))

    games_as_p1 = db.relationship('Game', foreign_keys='Game.player1_id', backref='player1')
    games_as_p2 = db.relationship('Game', foreign_keys='Game.player2_id', backref='player2')


class Game(db.Model):
    __tablename__ = 'games'

    id          = db.Column(db.String(36), primary_key=True,
                            default=lambda: str(uuid.uuid4()))
    status      = db.Column(db.String(16), nullable=False, default='waiting')
    # status values: 'waiting' | 'active' | 'finished'

    player1_id  = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    player2_id  = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    winner      = db.Column(db.Integer, nullable=True)  # 1 or 2, None if unfinished

    created_at  = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    finished_at = db.Column(db.DateTime, nullable=True)
