from __future__ import annotations

from functools import wraps
from flask import current_app, redirect, url_for, flash, request, abort
from flask_login import current_user
from flask.views import MethodView

from .models import AssignmentState


def is_admin_user() -> bool:
    admin_name = (current_app.config.get("SANTA_ADMIN_NAME") or "").strip()
    return bool(admin_name) and current_user.is_authenticated and current_user.name == admin_name


def assignments_locked() -> bool:
    return AssignmentState.get_singleton().is_locked


# --------- Function-view decorators (if you ever want them) ----------

def login_required_view(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not is_admin_user():
            flash("Not authorized.", "error")
            return redirect(url_for("santa.dashboard"))
        return fn(*args, **kwargs)
    return wrapper


# --------- Class-based view Mixins (recommended) ----------

class LoginRequiredMixin(MethodView):
    def dispatch_request(self, *args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))

        # ✅ Force passphrase change immediately after temp passphrase login
        # Allow only change-passphrase + logout while in this state.
        if getattr(current_user, "must_change_passphrase", False):
            if request.endpoint not in {"auth.change_passphrase", "auth.logout"}:
                return redirect(url_for("auth.change_passphrase"))

        return super().dispatch_request(*args, **kwargs)


class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch_request(self, *args, **kwargs):
        if not is_admin_user():
            flash("Not authorized.", "error")
            return redirect(url_for("santa.dashboard"))
        return super().dispatch_request(*args, **kwargs)


class ViewOnlyWhenLockedMixin(LoginRequiredMixin):
    """
    Allows GET always.
    Blocks POST/PUT/PATCH/DELETE when assignments are locked.
    """
    def dispatch_request(self, *args, **kwargs):
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and assignments_locked():
            flash("This is view-only because assignments are locked.", "info")
            return redirect(request.path)
        return super().dispatch_request(*args, **kwargs)

