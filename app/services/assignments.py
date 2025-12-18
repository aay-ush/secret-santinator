from __future__ import annotations

import random
from datetime import datetime
from flask import current_app

from ..extensions import db
from ..models import Participant, AssignmentState, Exclusion


class AssignmentError(RuntimeError):
    pass


def _pool_participants_excluding_admin() -> list[Participant]:
    admin_name = (current_app.config.get("SANTA_ADMIN_NAME") or "").strip()
    q = Participant.query
    if admin_name:
        q = q.filter(Participant.name != admin_name)
    return q.all()


def _exclusion_map(participants: list[Participant]) -> dict[int, set[int]]:
    ids = {p.id for p in participants}
    excluded = {p.id: set() for p in participants}
    for e in Exclusion.query.all():
        if e.giver_id in ids and e.receiver_id in ids:
            excluded[e.giver_id].add(e.receiver_id)
    return excluded


def _find_matching(giver_ids: list[int], allowed: dict[int, list[int]]) -> dict[int, int] | None:
    giver_order = sorted(giver_ids, key=lambda gid: len(allowed[gid]))
    used = set()
    result: dict[int, int] = {}

    def dfs(i: int) -> bool:
        if i == len(giver_order):
            return True
        g = giver_order[i]
        candidates = allowed[g][:]
        random.shuffle(candidates)
        for r in candidates:
            if r in used:
                continue
            used.add(r)
            result[g] = r
            if dfs(i + 1):
                return True
            used.remove(r)
            result.pop(g, None)
        return False

    return result if dfs(0) else None


def run_and_lock_assignments() -> None:
    state = AssignmentState.get_singleton()
    if state.is_locked:
        return

    people = _pool_participants_excluding_admin()
    if len(people) < 2:
        raise AssignmentError("Need at least 2 non-admin participants to run assignments.")

    ids = [p.id for p in people]
    excluded = _exclusion_map(people)
    all_receivers = set(ids)

    allowed: dict[int, list[int]] = {}
    for gid in ids:
        disallowed = set(excluded.get(gid, set()))
        disallowed.add(gid)
        allowed_list = sorted(list(all_receivers - disallowed))
        allowed[gid] = allowed_list

    if any(len(allowed[gid]) == 0 for gid in ids):
        raise AssignmentError("No valid assignment: someone has zero allowed recipients.")

    assignment = _find_matching(ids, allowed)
    if not assignment:
        raise AssignmentError("No valid assignment satisfies the current filters.")

    id_map = {p.id: p for p in people}
    for giver_id, receiver_id in assignment.items():
        id_map[giver_id].assigned_to_id = receiver_id

    state.is_locked = True
    state.run_at = datetime.utcnow()
    db.session.commit()


def unset_and_unlock_assignments() -> None:
    state = AssignmentState.get_singleton()

    # Clear assignments for non-admin pool
    people = _pool_participants_excluding_admin()
    for p in people:
        p.assigned_to_id = None

    state.is_locked = False
    state.run_at = None
    db.session.commit()

