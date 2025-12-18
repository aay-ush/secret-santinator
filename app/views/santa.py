from __future__ import annotations

from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user

from ..extensions import db
from ..models import Participant, AssignmentState, Exclusion
from ..policies import LoginRequiredMixin, AdminRequiredMixin, ViewOnlyWhenLockedMixin, is_admin_user, assignments_locked
from ..services.assignments import run_and_lock_assignments, unset_and_unlock_assignments, AssignmentError
from ..services.preferences import get_user_preferences, set_user_preferences
from ..models import Exclusion
from ..security import hash_client_key

santa_bp = Blueprint("santa", __name__)


class DashboardView(LoginRequiredMixin):
    def get(self):
        state = AssignmentState.get_singleton()
        num_participants = Participant.query.count()
        reset_count = Participant.query.filter_by(reset_requested=True).count()
        return render_template(
            "santa/dashboard.html",
            assignment_locked=state.is_locked,
            assignment_run_at=state.run_at,
            num_participants=num_participants,
            is_admin=is_admin_user(),
            reset_count=reset_count,
        )


class MyAssignmentView(LoginRequiredMixin):
    def get(self):
        if not current_user.assigned_to_id:
            flash("Assignments have not been run yet (or you are excluded).", "info")
            return redirect(url_for("santa.dashboard"))
        return render_template("santa/assignment.html", assigned_to=current_user.assigned_to)


class PreferencesView(ViewOnlyWhenLockedMixin):
    def get(self):
        state = AssignmentState.get_singleton()
        locked = state.is_locked

        admin_name = (current_app.config.get("SANTA_ADMIN_NAME") or "").strip()
        q = Participant.query
        if admin_name:
            q = q.filter(Participant.name != admin_name)
        candidates = q.order_by(Participant.name.asc()).all()
        candidates = [p for p in candidates if p.id != current_user.id]

        outgoing, incoming = get_user_preferences(current_user.id)

        return render_template(
            "santa/preferences.html",
            candidates=candidates,
            outgoing=outgoing,
            incoming=incoming,
            locked=locked,
            assignment_run_at=state.run_at,
        )

    def post(self):
        # ViewOnlyWhenLockedMixin blocks POST when locked
        admin_name = (current_app.config.get("SANTA_ADMIN_NAME") or "").strip()
        q = Participant.query
        if admin_name:
            q = q.filter(Participant.name != admin_name)
        candidates = q.all()
        valid_ids = {p.id for p in candidates if p.id != current_user.id}

        dont_gift_to = {int(x) for x in request.form.getlist("dont_gift_to")}
        dont_receive_from = {int(x) for x in request.form.getlist("dont_receive_from")}
        dont_gift_to = {i for i in dont_gift_to if i in valid_ids}
        dont_receive_from = {i for i in dont_receive_from if i in valid_ids}

        set_user_preferences(current_user.id, dont_gift_to, dont_receive_from)
        flash("Preferences saved.", "success")
        return redirect(url_for("santa.preferences"))


class AdminRunAssignmentsView(AdminRequiredMixin):
    def get(self):
        try:
            run_and_lock_assignments()
            flash("Assignments have been run and locked.", "success")
        except AssignmentError as e:
            flash(f"Failed to run assignments: {e}", "error")
        return redirect(url_for("santa.dashboard"))


class AdminUnsetAssignmentsView(AdminRequiredMixin):
    def post(self):
        unset_and_unlock_assignments()
        flash("Assignments unset and unlocked. Users can update preferences; you can rerun assignments.", "success")
        return redirect(url_for("santa.dashboard"))


class AdminResetsView(AdminRequiredMixin):
    def get(self):
        pending = Participant.query.filter_by(reset_requested=True).order_by(Participant.name.asc()).all()
        return render_template("santa/admin_resets.html", pending=pending)


class AdminResetPasskeyView(AdminRequiredMixin):
    def get(self, participant_id: int):
        p = Participant.query.get_or_404(participant_id)
        return render_template("santa/admin_reset_passkey.html", participant=p)

    def post(self, participant_id: int):
        p = Participant.query.get_or_404(participant_id)
        client_hash = (request.form.get("client_hash") or "").strip().lower()
        if not client_hash:
            flash("Missing client hash.", "error")
            return redirect(url_for("santa.admin_reset_passkey", participant_id=participant_id))

        p.passkey_hash = hash_client_key(client_hash)
        p.reset_requested = False
        db.session.commit()
        flash(f"Reset complete for {p.name}.", "success")
        return redirect(url_for("santa.admin_resets"))

class AdminDeleteParticipantView(AdminRequiredMixin):
    def post(self, participant_id: int):
        # ✅ Auto-unlock if locked
        if AssignmentState.get_singleton().is_locked:
            unset_and_unlock_assignments()
            flash("Assignments were locked — they have been unset & unlocked due to participant deletion.", "info")

        p = Participant.query.get_or_404(participant_id)

        # Prevent deleting the admin account via UI (recommended)
        if is_admin_user() and p.id == current_user.id:
            flash("You cannot delete the admin account while logged in as it.", "error")
            return redirect(url_for("santa.admin_participants"))

        # Clean up directed exclusions involving this user
        Exclusion.query.filter(
            (Exclusion.giver_id == p.id) | (Exclusion.receiver_id == p.id)
        ).delete(synchronize_session=False)

        # Clear any assignments pointing to this person (defensive)
        Participant.query.filter_by(assigned_to_id=p.id).update(
            {"assigned_to_id": None}, synchronize_session=False
        )

        db.session.delete(p)
        db.session.commit()

        flash(f"Deleted participant: {p.name}", "success")
        return redirect(url_for("santa.admin_participants"))

class AdminParticipantsView(AdminRequiredMixin):
    def get(self):
        state = AssignmentState.get_singleton()
        participants = Participant.query.order_by(Participant.name.asc()).all()
        return render_template(
            "santa/admin_participants.html",
            participants=participants,
            locked=state.is_locked,
        )


# Register routes
santa_bp.add_url_rule("/dashboard", view_func=DashboardView.as_view("dashboard"))
santa_bp.add_url_rule("/my-assignment", view_func=MyAssignmentView.as_view("my_assignment"))
santa_bp.add_url_rule("/preferences", view_func=PreferencesView.as_view("preferences"), methods=["GET", "POST"])

santa_bp.add_url_rule("/admin/run-assignments", view_func=AdminRunAssignmentsView.as_view("admin_run_assignments"))
santa_bp.add_url_rule("/admin/unset-assignments", view_func=AdminUnsetAssignmentsView.as_view("admin_unset_assignments"), methods=["POST"])

santa_bp.add_url_rule("/admin/resets", view_func=AdminResetsView.as_view("admin_resets"))
santa_bp.add_url_rule("/admin/reset-passkey/<int:participant_id>", view_func=AdminResetPasskeyView.as_view("admin_reset_passkey"), methods=["GET", "POST"])

santa_bp.add_url_rule("/admin/participants", view_func=AdminParticipantsView.as_view("admin_participants"))
santa_bp.add_url_rule(
    "/admin/participants/<int:participant_id>/delete",
    view_func=AdminDeleteParticipantView.as_view("admin_delete_participant"),
    methods=["POST"],
)

