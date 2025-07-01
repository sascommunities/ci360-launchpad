from flask import Flask
import os
from .config import Config
from .routes.export_routes import export_bp

def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config)

    with app.app_context():
        app.register_blueprint(export_bp)

    return app
