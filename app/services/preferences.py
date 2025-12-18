from __future__ import annotations

from ..extensions import db
from ..models import Exclusion


def get_user_preferences(user_id: int) -> tuple[set[int], set[int]]:
    """
    Returns:
      outgoing = {receiver_id} that user cannot gift to
      incoming = {giver_id} that cannot gift to user
    """
    outgoing = {e.receiver_id for e in Exclusion.query.filter_by(giver_id=user_id).all()}
    incoming = {e.giver_id for e in Exclusion.query.filter_by(receiver_id=user_id).all()}
    return outgoing, incoming


def set_user_preferences(user_id: int, dont_gift_to: set[int], dont_receive_from: set[int]) -> None:
    """
    Persists:
      user_id -> rid exclusions for dont_gift_to
      gid -> user_id exclusions for dont_receive_from
    """
    Exclusion.query.filter_by(giver_id=user_id).delete()
    for rid in dont_gift_to:
        db.session.add(Exclusion(giver_id=user_id, receiver_id=rid))

    Exclusion.query.filter_by(receiver_id=user_id).delete()
    for gid in dont_receive_from:
        db.session.add(Exclusion(giver_id=gid, receiver_id=user_id))

    db.session.commit()

