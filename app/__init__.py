import os
from flask import Flask
from .extensions import db, login_manager, migrate
from .auth import auth_bp
from .santa import santa_bp

def create_app():
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Render provides DATABASE_URL for Postgres. We also support SQLite locally.
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///secretsanta.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Admin is the participant with this exact name
    app.config["SANTA_ADMIN_NAME"] = os.environ.get("SANTA_ADMIN_NAME", "")

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"

    app.register_blueprint(auth_bp)
    app.register_blueprint(santa_bp)

    return app

