# Service plan helpers (utils/service.py, wave 2).
from datetime import date

from models.models import Device, DeviceCategory
from utils import service as svc


def test_add_months_clamps_month_end():
    assert svc.add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert svc.add_months(date(2026, 11, 14), 6) == date(2027, 5, 14)


def test_interval_override_then_category_then_default():
    cat = DeviceCategory(service_interval_months=3)
    assert svc.interval_months(Device(service_interval_months=12), cat) == 12
    assert svc.interval_months(Device(), cat) == 3
    assert svc.interval_months(Device(), None) == svc.DEFAULT_INTERVAL_MONTHS


def test_service_state():
    today = date(2026, 11, 14)
    assert svc.service_state(None, today) == "none"
    assert svc.service_state(date(2026, 11, 13), today) == "overdue"
    assert svc.service_state(date(2026, 11, 28), today) == "due_soon"
    assert svc.service_state(date(2026, 11, 29), today) == "ok"
