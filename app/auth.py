from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user
from .extensions import db
from .models import Participant
from .security import hash_client_key, verify_client_key

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("santa.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip() or None
        client_hash = (request.form.get("client_hash") or "").strip().lower()

        if not name or not client_hash:
            flash("Name is required.", "error")
            return render_template("auth/register.html")

        if Participant.query.filter_by(name=name).first():
            flash("That name is already registered.", "error")
            return render_template("auth/register.html")

        if email and Participant.query.filter_by(email=email).first():
            flash("That email is already registered.", "error")
            return render_template("auth/register.html")

        p = Participant(name=name, email=email, passkey_hash=hash_client_key(client_hash))
        db.session.add(p)
        db.session.commit()

        flash("Registered. Now log in (this device remembers your passphrase).", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("santa.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        client_hash = (request.form.get("client_hash") or "").strip().lower()

        user = Participant.query.filter_by(name=name).first()
        if user and client_hash and verify_client_key(client_hash, user.passkey_hash):
            login_user(user)
            return redirect(url_for("santa.dashboard"))

        flash("Invalid name or passphrase on this device.", "error")

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/request-reset", methods=["POST"])
def request_reset():
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

