# [AI Summary] App-wide configuration: Flask settings, secret key, port, and
# game constants (board size, win threshold, op limits, word bank rates).
# Imported by: app/__init__.py.

import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    PORT = 45630
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///satura.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DELETED_USERNAME = '[Deleted]'

    # ── User settings defaults ───────────────────────────────────────────────
    DEFAULT_PLAYER_CHOICE = 'random'  # 'p1' | 'p2' | 'random'
    DEFAULT_PALETTE = 'solstice'
    DEFAULT_TIME_CONTROL = '15'       # '60' | '30' | '15' | '5' | 'custom'
    DEFAULT_CUSTOM_MINUTES = 10
    BOARD_SIZE_STOPS = (8, 10, 12, 14, 16, 18, 20, 24, 28, 32)

    # Preset knobs for future game-creation requests.
    # Keys are minute labels used by UI controls.
    TIME_CONTROL_PRESETS = {
        '60': {
            'clock_seconds': 3600.0,
            'board_size': 16,
            'op_limit': 25,
            'word_rate': 2.0,
            'starting_words': 0.0,
        },
        '30': {
            'clock_seconds': 1800.0,
            'board_size': 16,
            'op_limit': 25,
            'word_rate': 2.0,
            'starting_words': 0.0,
        },
        '15': {
            'clock_seconds': 900.0,
            'board_size': 16,
            'op_limit': 25,
            'word_rate': 2.0,
            'starting_words': 0.0,
        },
        '5': {
            'clock_seconds': 300.0,
            'board_size': 16,
            'op_limit': 25,
            'word_rate': 2.0,
            'starting_words': 0.0,
        },
    }

    # ── Game constants ────────────────────────────────────────────────────────
    BOARD_SIZE      = TIME_CONTROL_PRESETS['5']['board_size']
    OP_LIMIT        = TIME_CONTROL_PRESETS['5']['op_limit']
    CLOCK_SECONDS   = TIME_CONTROL_PRESETS['5']['clock_seconds']
    WORD_RATE       = TIME_CONTROL_PRESETS['5']['word_rate']      # words per second during live games
    ANIMATION_DURATION = 15.0  # seconds for post-exec animation phase

    # ── Test bench overrides ──────────────────────────────────────────────────
    TEST_CLOCK_SECONDS  = 3600.0
    TEST_WORD_RATE      = 1 / 3   # one word every 3 seconds
    TEST_WORD_BANK_START = 10.0   # words pre-loaded at session start
