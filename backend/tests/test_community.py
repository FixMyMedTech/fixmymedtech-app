# Tests for the community journey rules (utils/community.py).
#
# Run from backend/:  python -m pytest tests -q
# These cover the pure rules that decide who gets in and what unlocks. They
# need no database.

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import community as cm  # noqa: E402

ALL_QUESTS = {q: 1 for q in cm.WELCOME_QUESTS}


def status(req, held=(), metrics=None, quests=None, confirmations=()):
    return cm.requirement_status(req, set(held), metrics or {}, quests or {}, set(confirmations))


# ── Requirements ─────────────────────────────────────────────

def test_role_requirement():
    req = {"kind": "role", "ref": "mapper", "threshold": None}
    assert status(req)["met"] is False
    assert status(req, held=["mapper"])["met"] is True


def test_metric_requirement_counts_up_to_threshold():
    req = {"kind": "metric", "ref": "repairs_and_maintenance", "threshold": 5}
    s = status(req, metrics={"repairs_and_maintenance": 3})
    assert s == {"met": False, "done": 3, "needed": 5}
    s = status(req, metrics={"repairs_and_maintenance": 9})
    assert s == {"met": True, "done": 5, "needed": 5}


def test_quest_requirement_with_count():
    req = {"kind": "quest", "ref": "watched_approval_meeting", "threshold": 2}
    assert status(req, quests={"watched_approval_meeting": 1})["met"] is False
    assert status(req, quests={"watched_approval_meeting": 2})["met"] is True


def test_confirmation_requirement():
    req = {"kind": "confirmation", "ref": "community_team", "threshold": None}
    assert status(req)["met"] is False
    assert status(req, confirmations=["community_team"])["met"] is True


def test_unknown_kind_is_never_met():
    assert status({"kind": "vote", "ref": "x", "threshold": None})["met"] is False


# ── Member status ────────────────────────────────────────────

def test_applicant_becomes_member_only_with_all_quests():
    partial = dict(ALL_QUESTS)
    partial["meeting_held"] = 0
    assert cm.next_status("applicant", "community", partial) == "applicant"
    assert cm.next_status("applicant", "community", ALL_QUESTS) == "member"


def test_clinic_staff_get_in_with_the_video_only():
    assert cm.next_status("applicant", "clinic_staff", {}) == "applicant"
    assert cm.next_status("applicant", "clinic_staff", {"intro_video": 1}) == "staff"


def test_staff_become_members_after_all_quests():
    assert cm.next_status("staff", "clinic_staff", {"intro_video": 1}) == "staff"
    assert cm.next_status("staff", "clinic_staff", ALL_QUESTS) == "member"


def test_community_applicant_does_not_skip_quests_with_the_video():
    assert cm.next_status("applicant", "community", {"intro_video": 1}) == "applicant"


def test_refused_and_members_never_move():
    assert cm.next_status("refused", "community", ALL_QUESTS) == "refused"
    assert cm.next_status("member", "community", {}) == "member"


def test_quests_done_keeps_order():
    assert cm.quests_done({"consent_answered": 1, "intro_video": 1}) == ["intro_video", "consent_answered"]


# ── Pausing ──────────────────────────────────────────────────

def test_roles_pause_after_six_months():
    at = datetime(2026, 10, 30, tzinfo=timezone.utc)
    assert cm.is_paused(None, at) is False
    assert cm.is_paused(at - timedelta(days=30), at) is False
    assert cm.is_paused(at - timedelta(days=200), at) is True


# ── Scopes ───────────────────────────────────────────────────

def test_scope_covers_countries_and_teams():
    s = cm.Scope()
    assert not s
    s.countries.add("Ghana")
    assert s.covers(country="Ghana")
    assert not s.covers(country="Kenya")
    s.teams.add("software")
    assert s.covers(teams={"software"})
    everywhere = cm.Scope(); everywhere.everywhere = True
    assert everywhere.covers(country="Kenya")


def test_every_seeded_permission_is_known():
    """The migration may only grant keys the code defines."""
    path = os.path.join(os.path.dirname(__file__), "..", "..", "infrastructure", "migrations",
                        "029_community_roles.sql")
    sql = open(path, encoding="utf-8").read()
    block = sql.split("INSERT INTO fixmymedtech.community_role_permissions", 1)[1].split(";", 1)[0]
    import re
    keys = set(re.findall(r"\('[a-z_]+', '([a-z_]+)'\)", block))
    assert keys, "no permissions found in the seed"
    assert keys <= set(cm.PERMISSIONS), keys - set(cm.PERMISSIONS)


def test_localized_falls_back_to_english():
    assert cm.localized({"en": "Mapper", "fr": "Cartographe"}, "fr") == "Cartographe"
    assert cm.localized({"en": "Mapper"}, "es") == "Mapper"
    assert cm.localized(None, "en") == ""
