# [AI Summary] App-wide configuration: Flask settings, secret key, port, and
# game constants (board size, win threshold, op limits, word bank rates).
# Imported by: app/__init__.py.

import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    HOST = '0.0.0.0'
    PORT = 45630
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///satura.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DELETED_USERNAME = '[Deleted]'

    # ── User settings defaults ───────────────────────────────────────────────
    DEFAULT_PALETTE = 'solstice'
    DEFAULT_TIME_CONTROL = '15'       # '60' | '30' | '15' | '5' | 'custom'
    DEFAULT_CUSTOM_MINUTES = 10
    BOARD_SIZE_STOPS = (4, 6, 8, 10, 12, 14, 16, 18, 20, 24, 28, 32)

    # Preset knobs for future game-creation requests.
    # Keys are minute labels used by UI controls.
    TIME_CONTROL_PRESETS = {
        '60': {
            'clock_seconds': 3600.0,
            'board_size': 16,
            'op_limit': 75,
            'word_rate': 0.1,
            'starting_words': 50.0,
        },
        '30': {
            'clock_seconds': 1800.0,
            'board_size': 12,
            'op_limit': 50,
            'word_rate': 0.2,
            'starting_words': 25.0,
        },
        '15': {
            'clock_seconds': 900.0,
            'board_size': 8,
            'op_limit': 25,
            'word_rate': 0.5,
            'starting_words': 25.0,
        },
        '5': {
            'clock_seconds': 300.0,
            'board_size': 6,
            'op_limit': 25,
            'word_rate': 1,
            'starting_words': 30.0,
        },
    }

    # ── Game constants ────────────────────────────────────────────────────────
    BOARD_SIZE      = TIME_CONTROL_PRESETS['5']['board_size']
    OP_LIMIT        = TIME_CONTROL_PRESETS['5']['op_limit']
    CLOCK_SECONDS   = TIME_CONTROL_PRESETS['5']['clock_seconds']
    WORD_RATE       = TIME_CONTROL_PRESETS['5']['word_rate']      # words per second during live games
    ANIMATION_STEP_DURATION = 0.5  # seconds for each step in the animation to wait
    INITIAL_PRE_WRITE_SECONDS = 30.0  # one-time opening think timer before first write phase

