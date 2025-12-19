from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask.views import MethodView
from flask_login import login_user, logout_user, current_user

from ..extensions import db
from ..models import Participant
from ..security import hash_client_key, verify_client_key


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


class RegisterView(MethodView):
    def get(self):
        if current_user.is_authenticated:
            return redirect(url_for("santa.dashboard"))
        return render_template("auth/register.html")

    def post(self):
        if current_user.is_authenticated:
            return redirect(url_for("santa.dashboard"))

        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip() or None
        client_hash = (request.form.get("client_hash") or "").strip().lower()

        if not name:
            flash("Name is required.", "error")
            return render_template("auth/register.html")

        if not client_hash:
            flash("Missing passphrase hash. Please refresh and try again.", "error")
            return render_template("auth/register.html")

        if Participant.query.filter_by(name=name).first():
            flash("That name is already registered.", "error")
            return render_template("auth/register.html")

        if email and Participant.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
            return render_template("auth/register.html")

        p = Participant(
            name=name,
            email=email,
            passkey_hash=hash_client_key(client_hash),
        )
        db.session.add(p)
        db.session.commit()

        flash("Registered. You can now log in (this device remembers your passphrase).", "success")
        return redirect(url_for("auth.login"))


class LoginView(MethodView):
    def get(self):
        if current_user.is_authenticated:
            return redirect(url_for("santa.dashboard"))
        return render_template("auth/login.html")

    def post(self):
        if current_user.is_authenticated:
            return redirect(url_for("santa.dashboard"))

        name = (request.form.get("name") or "").strip()
        client_hash = (request.form.get("client_hash") or "").strip().lower()

        if not name:
            flash("Name is required.", "error")
            return render_template("auth/login.html")

        user = Participant.query.filter_by(name=name).first()
        if not user or not client_hash or not verify_client_key(client_hash, user.passkey_hash):
            flash("Invalid name or this device does not have the correct saved passphrase.", "error")
            return render_template("auth/login.html")

        login_user(user)

        # If the organizer issued a temporary passphrase, force change on first use.
        if getattr(user, "must_change_passphrase", False):
            return redirect(url_for("auth.change_passphrase"))

        return redirect(url_for("santa.dashboard"))


class LogoutView(MethodView):
    def get(self):
        if current_user.is_authenticated:
            logout_user()
        return redirect(url_for("auth.login"))


class RequestResetView(MethodView):
    """
    User requests reset by name; admin confirms identity offline and performs reset.
    """
    def post(self):
        name = (request.form.get("name") or "").strip()
        if not name:
            flash("Name is required to request reset.", "error")
            return redirect(url_for("auth.login"))

        p = Participant.query.filter_by(name=name).first()
        if not p:
            flash("No such participant.", "error")
            return redirect(url_for("auth.login"))

        p.reset_requested = True
        db.session.commit()
        flash("Reset requested. Please contact the organizer in person to complete it.", "info")
        return redirect(url_for("auth.login"))

class ChangePassphraseView(MethodView):
    """
    Used after logging in with a temporary passphrase (or anytime user wants to rotate).
    Uses the SAME UI pattern as register: generated phrase or manual entry.
    """
    def get(self):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return render_template("auth/change_passphrase.html")

    def post(self):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        client_hash = (request.form.get("client_hash") or "").strip().lower()
        if not client_hash:
            flash("Missing passphrase hash. Please try again.", "error")
            return render_template("auth/change_passphrase.html")

        current_user.passkey_hash = hash_client_key(client_hash)
        current_user.must_change_passphrase = False
        db.session.commit()

        flash("Passphrase updated.", "success")
        return redirect(url_for("santa.dashboard"))

auth_bp.add_url_rule("/register", view_func=RegisterView.as_view("register"), methods=["GET", "POST"])
auth_bp.add_url_rule("/login", view_func=LoginView.as_view("login"), methods=["GET", "POST"])
auth_bp.add_url_rule("/logout", view_func=LogoutView.as_view("logout"), methods=["GET"])
auth_bp.add_url_rule("/request-reset", view_func=RequestResetView.as_view("request_reset"), methods=["POST"])
auth_bp.add_url_rule("/change-passphrase", view_func=ChangePassphraseView.as_view("change_passphrase"), methods=["GET", "POST"])

