from __future__ import annotations

import os
from flask import Flask

from .extensions import db, login_manager, migrate, csrf
from .models import AssignmentState
from .views.auth import auth_bp
from .views.santa import santa_bp
from .views.public import public_bp


def create_app() -> Flask:
    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///secretsanta.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Admin is the participant whose name matches this exactly
    app.config["SANTA_ADMIN_NAME"] = os.environ.get("SANTA_ADMIN_NAME", "").strip()

    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.login_view = "auth.login"

    # Blueprints
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(santa_bp)

    # Global template vars (used to hide register when locked if you want)
    @app.context_processor
    def inject_global_state():
        state = AssignmentState.get_singleton()
        return {
            "registration_closed": state.is_locked,
            "assignment_run_at": state.run_at,
            "is_admin": is_admin_user(),
        }

    return app

