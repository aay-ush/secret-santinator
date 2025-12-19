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

    # --- Assignments ---
    # Legacy plaintext assignment (kept for backward compatibility with existing DBs).
    # We no longer write to this column; it is cleared whenever assignments are run/unset.
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("participants.id", ondelete="SET NULL"), nullable=True)
    assigned_to = db.relationship(
        "Participant",
        remote_side=[id],
        foreign_keys=[assigned_to_id],
        uselist=False,
        post_update=True,
    )

    # Encrypted receiver_id (Fernet token string). This is what we now persist.
    assigned_to_ciphertext = db.Column(db.Text, nullable=True)

    reset_requested = db.Column(db.Boolean, default=False, nullable=False)
    # Organizer-issued temporary passphrase is active; force change on first login.
    must_change_passphrase = db.Column(db.Boolean, default=False, nullable=False)



class Exclusion(db.Model):
    """
    Directed constraint: giver_id cannot gift to receiver_id.
    """
    __tablename__ = "exclusions"
    id = db.Column(db.Integer, primary_key=True)

    giver_id = db.Column(db.Integer, db.ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("participants.id", ondelete="CASCADE"), nullable=False)

    giver = db.relationship("Participant", foreign_keys=[giver_id])
    receiver = db.relationship("Participant", foreign_keys=[receiver_id])

    __table_args__ = (
        db.UniqueConstraint("giver_id", "receiver_id", name="uq_exclusion_giver_receiver"),
    )


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

