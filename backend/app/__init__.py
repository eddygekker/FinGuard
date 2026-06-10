from flask import Flask
from flask_cors import CORS

from config import Config
from app.routes.api import api_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app, resources={r"/api/*": {"origins": "*"}})

    app.register_blueprint(api_bp, url_prefix="/api")

    return app
