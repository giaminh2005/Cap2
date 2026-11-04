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


# ---------------------------------------------------- F1 dem khach 2 camera
def _cross(cam, direction):
    r = client.post("/bridge/crossing", json={"camera_id": cam, "direction": direction})
    assert r.status_code == 200, r.text
    return r.json()


def test_bridge_counting_rules():
    client.post("/bridge/reset", params={"reset_dem": True})
    dem0 = client.get("/bridge/state").json()["dem"]
    assert dem0 == 0

    s = _cross(1, "in")                       # num1 += 1, dem += 1
    assert (s["num1"], s["num2"], s["onbridge"], s["dem"]) == (1, 0, 1, 1)
    s = _cross(1, "in")
    s = _cross(2, "in")
    assert (s["num1"], s["num2"], s["onbridge"], s["dem"]) == (2, 1, 3, 3)
    s = _cross(2, "out")
    s = _cross(2, "out")                      # num2 am: khach vao o cam 1, ra o cam 2
    assert (s["num1"], s["num2"], s["onbridge"]) == (2, -1, 1)
    s = _cross(1, "out")                      # onbridge == 0 -> reset num1, num2
    assert (s["num1"], s["num2"], s["onbridge"], s["reset"]) == (0, 0, 0, True)
    assert s["dem"] == 3                      # dem khong bi reset

    s = _cross(2, "out")                      # camera bo sot -> onbridge < 0 cung reset
    assert (s["num1"], s["num2"], s["onbridge"]) == (0, 0, 0)

    _cross(1, "in")
    assert client.get("/stats/occupancy").json()["current_count"] == 1   # dong bo dashboard


def test_bridge_validation():
    assert client.post("/bridge/crossing", json={"camera_id": 3, "direction": "in"}).status_code == 400
    assert client.post("/bridge/crossing", json={"camera_id": 1, "direction": "len"}).status_code == 400
    assert client.get("/bridge/stats", params={"group": "tuan"}).status_code == 400


def test_bridge_dem_resets_on_new_day(monkeypatch):
    from datetime import datetime, timedelta
    import backend.routers.bridge as bridge

    client.post("/bridge/reset", params={"reset_dem": True})
    _cross(1, "in")
    _cross(2, "in")
    assert client.get("/bridge/state").json()["dem"] == 2

    tomorrow = datetime.utcnow() + bridge.LOCAL_UTC_OFFSET + timedelta(days=1)
    monkeypatch.setattr(bridge, "_local_now", lambda: tomorrow)
    s = client.get("/bridge/state").json()
    assert s["dem"] == 0 and s["date"] == tomorrow.strftime("%Y-%m-%d")
    assert _cross(1, "in")["dem"] == 1


def test_bridge_stats_grouping():
    today = client.get("/bridge/state").json()["date"]
    for group in ("hour", "day", "month", "year"):
        d = client.get("/bridge/stats", params={"group": group, "date_from": today,
                                                 "date_to": today}).json()
        assert d["total_entries"] == sum(r["entries"] for r in d["rows"])
        assert all(r["entries"] == r["entries_cam1"] + r["entries_cam2"] for r in d["rows"])
    day = client.get("/bridge/stats", params={"group": "day", "date_from": today, "date_to": today}).json()
    assert day["rows"][0]["period"] == today and day["total_entries"] > 0
