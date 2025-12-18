from __future__ import annotations

from flask import Blueprint, render_template
from flask.views import MethodView

from ..models import AssignmentState, Participant


public_bp = Blueprint("public", __name__)


class LandingView(MethodView):
    def get(self):
        state = AssignmentState.get_singleton()
        return render_template(
            "landing.html",
            registration_closed=state.is_locked,
            assignment_run_at=state.run_at,
            num_participants=Participant.query.count(),
        )


public_bp.add_url_rule("/", view_func=LandingView.as_view("landing"))

