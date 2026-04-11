import uuid
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


class Account(UserMixin, db.Model):
    __tablename__ = 'accounts'

    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(64), unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at    = db.Column(db.DateTime, nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    disabled      = db.Column(db.Boolean, nullable=False, default=False)
    deleted       = db.Column(db.Boolean, nullable=False, default=False)

    games_as_p1 = db.relationship('Game', foreign_keys='Game.player1_id', backref='player1')
    games_as_p2 = db.relationship('Game', foreign_keys='Game.player2_id', backref='player2')
    settings = db.relationship(
        'AccountSettings',
        back_populates='account',
        uselist=False,
        cascade='all, delete-orphan',
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Game(db.Model):
    __tablename__ = 'games'

    id          = db.Column(db.String(36), primary_key=True,
                            default=lambda: str(uuid.uuid4()))
    status      = db.Column(db.String(16), nullable=False, default='waiting')
    # status values: 'waiting' | 'active' | 'finished'

    player1_id  = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    player2_id  = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    winner      = db.Column(db.Integer, nullable=True)  # 1 or 2, None if unfinished
    is_draw     = db.Column(db.Boolean, nullable=False, default=False)
    end_reason  = db.Column(db.String(16), nullable=True)

    created_at  = db.Column(db.DateTime, nullable=False,
                            default=lambda: datetime.now(timezone.utc))
    finished_at = db.Column(db.DateTime, nullable=True)
    created_by  = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)

    # Game settings
    preset                 = db.Column(db.String(8), nullable=True)
    board_size             = db.Column(db.Integer, nullable=True)
    op_limit               = db.Column(db.Integer, nullable=True)
    clock_seconds          = db.Column(db.Float, nullable=True)
    word_rate              = db.Column(db.Float, nullable=True)
    starting_player        = db.Column(db.Integer, nullable=True)
    accommodations_enabled = db.Column(db.Boolean, nullable=False, default=False)
    p1_clock_seconds       = db.Column(db.Float, nullable=True)
    p2_clock_seconds       = db.Column(db.Float, nullable=True)
    p1_starting_words      = db.Column(db.Float, nullable=True)
    p2_starting_words      = db.Column(db.Float, nullable=True)

    # Relationships to new tables
    scripts    = db.relationship('Script', backref='game', lazy='dynamic')
    phases     = db.relationship('ExecutionPhase', backref='game', lazy='dynamic')
    functions  = db.relationship('DefinedFunction', backref='game', lazy='dynamic')


class Script(db.Model):
    __tablename__ = 'scripts'
    __table_args__ = (
        db.Index('ix_scripts_game_turn', 'game_id', 'turn_number'),
        db.Index('ix_scripts_account', 'account_id'),
    )

    id                     = db.Column(db.Integer, primary_key=True)
    game_id                = db.Column(db.String(36), db.ForeignKey('games.id'), nullable=False)
    account_id             = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    player_slot            = db.Column(db.Integer, nullable=False)
    source_text            = db.Column(db.Text, nullable=False)
    word_count             = db.Column(db.Integer, nullable=False)
    write_duration_seconds = db.Column(db.Float, nullable=True)
    turn_number            = db.Column(db.Integer, nullable=False)
    created_at             = db.Column(db.DateTime, nullable=False,
                                       default=lambda: datetime.now(timezone.utc))


class ExecutionPhase(db.Model):
    __tablename__ = 'execution_phases'
    __table_args__ = (
        db.Index('ix_exec_phases_game', 'game_id', 'phase_number'),
    )

    id                   = db.Column(db.Integer, primary_key=True)
    game_id              = db.Column(db.String(36), db.ForeignKey('games.id'), nullable=False)
    phase_number         = db.Column(db.Integer, nullable=False)
    player_slot          = db.Column(db.Integer, nullable=False)
    exec_type            = db.Column(db.String(8), nullable=False)  # 'exec1', 'exec2', 'initial'
    script_id            = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=True)
    outcome              = db.Column(db.String(8), nullable=True)   # 'normal', 'halt', 'reset'
    exec_log_json        = db.Column(db.Text, nullable=True)
    ops_consumed         = db.Column(db.Integer, nullable=False, default=0)
    board_state_json     = db.Column(db.Text, nullable=False)
    agents_json          = db.Column(db.Text, nullable=False)
    word_banks_json      = db.Column(db.Text, nullable=True)
    clock_remaining_json = db.Column(db.Text, nullable=True)
    prev_phase_id        = db.Column(db.Integer, db.ForeignKey('execution_phases.id'), nullable=True)
    created_at           = db.Column(db.DateTime, nullable=False,
                                    default=lambda: datetime.now(timezone.utc))

    script     = db.relationship('Script', foreign_keys=[script_id])
    prev_phase = db.relationship('ExecutionPhase', remote_side='ExecutionPhase.id',
                                 foreign_keys=[prev_phase_id])


class DefinedFunction(db.Model):
    __tablename__ = 'defined_functions'
    __table_args__ = (
        db.Index('ix_defined_funcs_game_account', 'game_id', 'account_id'),
        db.Index('ix_defined_funcs_script', 'script_id'),
    )

    id             = db.Column(db.Integer, primary_key=True)
    game_id        = db.Column(db.String(36), db.ForeignKey('games.id'), nullable=False)
    account_id     = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=True)
    script_id      = db.Column(db.Integer, db.ForeignKey('scripts.id'), nullable=False)
    func_name      = db.Column(db.String(64), nullable=False)
    func_body_text = db.Column(db.Text, nullable=False)
    created_at     = db.Column(db.DateTime, nullable=False,
                               default=lambda: datetime.now(timezone.utc))

    script = db.relationship('Script', foreign_keys=[script_id])


class AccountSettings(db.Model):
    __tablename__ = 'account_settings'

    id                   = db.Column(db.Integer, primary_key=True)
    account_id           = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False, unique=True)
    default_time_control = db.Column(db.String(16), nullable=False, default='15')
    custom_minutes       = db.Column(db.Integer, nullable=True)
    default_player       = db.Column(db.String(8), nullable=False, default='random')
    default_board_size   = db.Column(db.Integer, nullable=False, default=16)
    palette              = db.Column(db.String(16), nullable=False, default='solstice')

    account = db.relationship('Account', back_populates='settings')
