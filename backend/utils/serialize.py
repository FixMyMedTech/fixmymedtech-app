# utils/serialize.py — response dicts built from table columns
#
# Never return ORM rows that reach a Profile: Profile.user is
# lazy="selectin", so FastAPI's encoder walks Profile → User and sends
# hashed_password with the response (see the header of
# routers/fault_reports.py). These helpers copy columns only and add the few
# related objects the pages read, again as columns only.

from typing import Optional


def row(obj) -> Optional[dict]:
    """Table columns only, never relationships."""
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def profile_brief(p) -> Optional[dict]:
    if p is None:
        return None
    return {"id": p.id, "username": p.username, "full_name": p.full_name, "avatar_key": p.avatar_key}


def _loaded(obj, attr: str):
    """A relationship's value if it is already loaded, else None (no lazy
    load on an async session)."""
    from sqlalchemy import inspect
    state = inspect(obj)
    if attr in state.unloaded:
        return None
    return getattr(obj, attr)


def device_out(device) -> Optional[dict]:
    """A device with its category and organizations, when they were loaded."""
    if device is None:
        return None
    d = row(device)
    for rel in ("category", "organization", "organization_maintenance", "healthsite"):
        d[rel] = row(_loaded(device, rel))
    return d


def log_out(log) -> Optional[dict]:
    """A maintenance log with its device and the two people, when loaded."""
    if log is None:
        return None
    d = row(log)
    d["device"] = row(_loaded(log, "device"))
    d["performed_by_profile"] = profile_brief(_loaded(log, "performed_by_profile"))
    d["assigned_to_profile"] = profile_brief(_loaded(log, "assigned_to_profile"))
    return d


def fault_brief(f) -> Optional[dict]:
    """A fault report's columns and its assignee, when loaded."""
    if f is None:
        return None
    d = row(f)
    d["assigned_to_profile"] = profile_brief(_loaded(f, "assigned_to_profile"))
    return d
