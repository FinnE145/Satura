# [AI Summary] App-wide configuration: Flask settings, secret key, port, and
# game constants (board size, win threshold, op limits, word bank rates).
# Imported by: app/__init__.py.

import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev')
    PORT = 45630
