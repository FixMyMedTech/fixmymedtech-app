# Claims and the task board (routers/community_work.py, wave 5).
import uuid

from models.models import CommunityTask, Profile
from routers import community_work as cw
from utils.community import powers_from

ME, OTHER, AUTHOR = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def _member():
    return Profile(id=ME, member_status="member")


def test_who_did_the_task_never_checks_it():
    task = CommunityTask(created_by=ME, taken_by=ME, status="review")
    lead = powers_from(False, "member", False, {"community_builder": "lead"})
    assert not cw._can_check(task, _member(), lead)
    assert not cw._can_check(task, _member(), powers_from(True, "member", False, {}))


def test_author_or_lead_checks_a_task():
    task = CommunityTask(created_by=ME, taken_by=OTHER, status="review")
    plain = powers_from(False, "member", False, {})
    assert cw._can_check(task, _member(), plain)                       # author
    task.created_by = AUTHOR
    assert not cw._can_check(task, _member(), plain)                   # just a member
    lead = powers_from(False, "member", False, {"clinics_connector": "lead"})
    assert cw._can_check(task, _member(), lead)                        # a lead


def test_only_members_claim_and_post():
    assert cw._is_member(_member(), powers_from(False, "member", False, {}))
    applicant = Profile(id=ME, member_status="applicant")
    assert not cw._is_member(applicant, powers_from(False, "applicant", False, {}))
    assert cw._is_member(applicant, powers_from(True, "applicant", False, {}))
