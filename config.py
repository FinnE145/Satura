# [AI Summary] App-wide configuration: Flask settings, secret key, port, and
# game constants (board size, win threshold, op limits, word bank rates).
# Imported by: app/__init__.py.

import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    PORT = 45630
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///satura.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ── Game constants ────────────────────────────────────────────────────────
    BOARD_SIZE      = 16
    OP_LIMIT        = 25
    CLOCK_SECONDS   = 300.0
    WORD_RATE       = 2.0      # words per second during live games
    ANIMATION_DURATION = 15.0  # seconds for post-exec animation phase

    # ── Test bench overrides ──────────────────────────────────────────────────
    TEST_CLOCK_SECONDS  = 3600.0
    TEST_WORD_RATE      = 1 / 3   # one word every 3 seconds
    TEST_WORD_BANK_START = 10.0   # words pre-loaded at session start
