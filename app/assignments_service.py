import random
from datetime import datetime
from .extensions import db
from .models import Participant, AssignmentState

def run_assignments() -> None:
    state = AssignmentState.get_singleton()
    if state.is_locked:
        return

    people = Participant.query.all()
    if len(people) < 2:
        raise ValueError("Need at least 2 participants.")

    ids = [p.id for p in people]
    assigned = ids[:]

    # simple derangement
    while True:
        random.shuffle(assigned)
        if all(a != b for a, b in zip(ids, assigned)):
            break

    id_map = {p.id: p for p in people}
    for giver_id, receiver_id in zip(ids, assigned):
        giver = id_map[giver_id]
        receiver = id_map[receiver_id]
        giver.assigned_to = receiver

    state.run_at = datetime.utcnow()
    state.is_locked = True
    db.session.commit()

