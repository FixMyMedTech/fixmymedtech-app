# Call an engineer helpers (utils/calls.py, wave 4).
from models.models import FaultOffer, Organization
from utils import calls as cl


def test_city_match_uses_region_address_or_name():
    clinic = Organization(name="Hôpital Laquintinie", region="Littoral", address="Akwa, Douala")
    assert cl._city_match("Douala", clinic)
    assert cl._city_match(" douala ", clinic)
    assert not cl._city_match("Yaoundé", clinic)
    assert not cl._city_match(None, clinic)


def test_accepting_one_offer_lapses_the_open_others():
    a, b, c, d = (FaultOffer(id=i, status=s) for i, s in
                  ((1, "pending"), (2, "countered"), (3, "declined"), (4, "pending")))
    cl.lapse_others([a, b, c, d], keep_id=4)
    assert [o.status for o in (a, b, c, d)] == ["lapsed", "lapsed", "declined", "pending"]
