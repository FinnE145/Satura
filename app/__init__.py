# [AI Summary] Flask application factory. Initializes the Flask app, registers
# blueprints, and applies configuration from config.py.
# Imported by: wsgi entry point (flask run). Imports: config.py, app/routes.py.

from flask import Flask
from config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    from app.routes import bp
    app.register_blueprint(bp)

    return app
