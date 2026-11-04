"""
tests/test_api.py  —  Kiem thu nhanh backend sau khi to chuc lai thu muc
=========================================================================
CHAY (tu thu muc goc):   pip install pytest httpx   (1 lan)
                         pytest tests/test_api.py -q

Dung CSDL rieng trong bo nho (khong dung toi backend/smartcau.db that).
Moi lan ai do sua backend -> chay lai file nay TRUOC khi tao Pull Request.
"""

import os
import sys

os.environ["SMARTCAU_DATABASE_URL"] = "sqlite:///:memory:"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import backend.database as database  # noqa: E402

# SQLite in-memory can dung chung 1 ket noi cho moi request
database.engine = database.create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
database.SessionLocal.configure(bind=database.engine)

from backend.main import app  # noqa: E402

database.Base.metadata.create_all(bind=database.engine)
client = TestClient(app)


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_entry_exit_updates_occupancy():
    start = client.get("/stats/occupancy").json()["current_count"]
    client.post("/entry", json={"gender": "Woman", "age_range": "18-24", "age": 21})
    client.post("/entry", json={"gender": "Man", "age_range": "25-34", "age": 30})
    client.post("/exit")
    assert client.get("/stats/occupancy").json()["current_count"] == start + 1


def test_exit_never_negative():
    for _ in range(10):
        client.post("/exit")
    assert client.get("/stats/occupancy").json()["current_count"] == 0


def test_config_roundtrip():
    assert client.put("/config", json={"alert_threshold": 25}).json()["alert_threshold"] == 25
    assert client.get("/config").json()["alert_threshold"] == 25
    assert client.put("/config", json={"alert_threshold": 0}).status_code == 400


def test_visit_event_filter():
    client.post("/visit_events", json={"gender": "Woman", "age_range": "35-44"})
    rows = client.get("/visit_events", params={"gender": "Woman", "age_range": "35-44"}).json()
    assert rows and all(r["gender"] == "Woman" for r in rows)


def test_incidents_read_system_events():
    client.post("/system_events", json={"event_type": "CRITICAL_ALERT", "count": 22})
    items = client.get("/incidents").json()
    assert items[0]["event_type"] == "CRITICAL_ALERT"


def test_skeleton_endpoints_answer():
    for path in ("/stats/demographics", "/reports/summary", "/tickets/reconciliation",
                 "/recipients", "/stats/facade"):
        r = client.get(path)
        assert r.status_code == 200, path
