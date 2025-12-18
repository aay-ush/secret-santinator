from datetime import datetime
from flask_login import UserMixin
from .extensions import db, login_manager

class Participant(UserMixin, db.Model):
    __tablename__ = "participants"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)

    # salted Passlib hash of SHA-256(passphrase) from the browser
    passkey_hash = db.Column(db.String(255), nullable=False)

    registered_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    assigned_to_id = db.Column(db.Integer, db.ForeignKey("participants.id"), nullable=True)
    assigned_to = db.relationship("Participant", remote_side=[id], uselist=False)

    reset_requested = db.Column(db.Boolean, default=False, nullable=False)


class AssignmentState(db.Model):
    __tablename__ = "assignment_state"

    id = db.Column(db.Integer, primary_key=True)
    run_at = db.Column(db.DateTime, nullable=True)
    is_locked = db.Column(db.Boolean, default=False, nullable=False)

    @classmethod
    def get_singleton(cls):
        obj = cls.query.first()
        if not obj:
            obj = cls()
            db.session.add(obj)
            db.session.commit()
        return obj


@login_manager.user_loader
def load_user(user_id: str):
    return Participant.query.get(int(user_id))

