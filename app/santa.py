from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
from flask_login import login_required, current_user
from .models import Participant, AssignmentState
from .assignment_service import run_assignments
from .security import hash_client_key
from .extensions import db

santa_bp = Blueprint("santa", __name__)

def _is_admin() -> bool:
    admin_name = current_app.config.get("SANTA_ADMIN_NAME")
    return bool(admin_name) and current_user.is_authenticated and current_user.name == admin_name

@santa_bp.route("/")
def index():
    return redirect(url_for("santa.dashboard"))

@santa_bp.route("/dashboard")
@login_required
def dashboard():
    state = AssignmentState.get_singleton()
    num_participants = Participant.query.count()
    reset_count = Participant.query.filter_by(reset_requested=True).count()

    return render_template(
        "santa/dashboard.html",
        assignment_locked=state.is_locked,
        assignment_run_at=state.run_at,
        num_participants=num_participants,
        is_admin=_is_admin(),
        reset_count=reset_count,
    )

@santa_bp.route("/my-assignment")
@login_required
def my_assignment():
    if not current_user.assigned_to:
        flash("Assignments have not been run yet.", "info")
        return redirect(url_for("santa.dashboard"))
    return render_template("santa/assignment.html", assigned_to=current_user.assigned_to)

@santa_bp.route("/admin/run-assignments")
@login_required
def admin_run_assignments():
    if not _is_admin():
        flash("Not authorized.", "error")
        return redirect(url_for("santa.dashboard"))

    try:
        run_assignments()
        flash("Assignments have been run and locked.", "success")
    except Exception as e:
        flash(f"Failed to run assignments: {e}", "error")
    return redirect(url_for("santa.dashboard"))

@santa_bp.route("/admin/resets")
@login_required
def admin_resets():
    if not _is_admin():
        flash("Not authorized.", "error")
        return redirect(url_for("santa.dashboard"))

    pending = Participant.query.filter_by(reset_requested=True).order_by(Participant.name.asc()).all()
    return render_template("santa/admin_resets.html", pending=pending)

@santa_bp.route("/admin/reset-passkey/<int:participant_id>", methods=["GET", "POST"])
@login_required
def admin_reset_passkey(participant_id: int):
    if not _is_admin():
        flash("Not authorized.", "error")
        return redirect(url_for("santa.dashboard"))

    p = Participant.query.get_or_404(participant_id)

    if request.method == "POST":
        client_hash = (request.form.get("client_hash") or "").strip().lower()
        if not client_hash:
            flash("Missing client hash.", "error")
            return redirect(url_for("santa.admin_reset_passkey", participant_id=participant_id))

        p.passkey_hash = hash_client_key(client_hash)
        p.reset_requested = False
        db.session.commit()

        flash(f"Reset complete for {p.name}. Make sure they keep the new passphrase on their device.", "success")
        return redirect(url_for("santa.admin_resets"))

    return render_template("santa/admin_reset_passkey.html", participant=p)

