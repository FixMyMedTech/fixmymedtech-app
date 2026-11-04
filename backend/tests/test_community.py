# Tests for the community journey rules (utils/community.py).
#
# Run from backend/:  python -m pytest tests -q
# These cover the pure rules: who gets in, star levels and who can do what. They
# need no database.

import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import community as cm  # noqa: E402

ALL_QUESTS = {q: 1 for q in cm.WELCOME_QUESTS}


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

def test_powers_pause_after_six_months():
    at = datetime(2026, 10, 30, tzinfo=timezone.utc)
    assert cm.is_paused(None, at) is False
    assert cm.is_paused(at - timedelta(days=30), at) is False
    assert cm.is_paused(at - timedelta(days=200), at) is True


# ── Star levels ──────────────────────────────────────────────

LEVELS = [1, 3, 5, 10, 15, 25, 40, 60, 80, 100]


def test_star_level_counts_thresholds_reached():
    assert cm.star_level(0, LEVELS) == {"level": 0, "count": 0, "next": 1, "prev": 0}
    assert cm.star_level(1, LEVELS)["level"] == 1
    assert cm.star_level(4, LEVELS) == {"level": 2, "count": 4, "next": 5, "prev": 3}
    assert cm.star_level(100, LEVELS) == {"level": 10, "count": 100, "next": None, "prev": 100}
    assert cm.star_level(500, LEVELS)["level"] == 10


def test_seeded_achievements_have_ten_ascending_levels():
    import re
    path = os.path.join(os.path.dirname(__file__), "..", "..", "infrastructure", "migrations",
                        "029_community_journey.sql")
    sql = open(path, encoding="utf-8").read()
    block = sql.split("INSERT INTO fixmymedtech.achievements", 1)[1].split(";", 1)[0]
    levels = re.findall(r"'\{([0-9,]+)\}'", block)
    assert len(levels) == 5
    for raw in levels:
        values = [int(v) for v in raw.split(",")]
        assert len(values) == cm.STAR_LEVELS
        assert values == sorted(set(values))


# ── Powers ───────────────────────────────────────────────────

TEAMS = ("communicator", "community_builder", "clinics_connector")


def powers(places, status="member", paused=False, superuser=False):
    return cm.powers_from(superuser, status, paused, places, TEAMS)


def test_superuser_can_do_everything():
    p = powers({}, status="applicant", superuser=True)
    assert p.view_applicants and p.view_history and p.name_leads
    assert p.can_add("communicator", "lead")
    assert p.recognise == set(TEAMS)


def test_candidates_and_outsiders_have_no_powers():
    assert cm.powers_from(False, "member", False, {}, TEAMS).as_list() == []
    assert powers({"communicator": "candidate"}).as_list() == []


def test_team_member_recognises_own_category_only():
    p = powers({"clinics_connector": "member"})
    assert p.recognise == {"clinics_connector"}
    assert p.view_members
    assert not p.view_applicants
    assert not p.can_add("clinics_connector", "candidate")


def test_community_builders_welcome_and_make_candidates_anywhere():
    p = powers({"community_builder": "member"})
    assert p.view_applicants and p.decide_applicants and p.confirm_quests
    assert p.can_add("communicator", "candidate")
    assert not p.can_add("communicator", "member")
    assert not p.view_history


def test_lead_manages_own_team_but_not_leads():
    p = powers({"communicator": "lead"})
    assert p.can_add("communicator", "member") and p.can_add("communicator", "candidate")
    assert not p.can_add("clinics_connector", "member")
    assert not p.can_add("communicator", "lead")
    assert p.edit_team == {"communicator"}
    assert p.view_history


def test_paused_or_non_members_have_no_powers():
    assert powers({"communicator": "lead"}, paused=True).as_list() == []
    assert powers({"community_builder": "lead"}, status="staff").as_list() == []


def test_powers_as_list_names_teams():
    keys = powers({"communicator": "lead"}).as_list()
    assert "manage_members:communicator" in keys and "recognise:communicator" in keys


def test_localized_falls_back_to_english():
    assert cm.localized({"en": "Mapper", "fr": "Cartographe"}, "fr") == "Cartographe"
    assert cm.localized({"en": "Mapper"}, "es") == "Mapper"
    assert cm.localized(None, "en") == ""
