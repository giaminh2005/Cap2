"""
backend/routers/display.py  —  MODULE M3 · F2.2 Bang LED tai cho co mascot (FR-05, FR-17)
==========================================================================================
Phu trach: HOAN.

    GET /display/state    1 lan goi = du so lieu cho bang LED (trang /led goi moi giay)
    /led/                 trang LED toan man hinh (backend/led_display/, HTML + JS + video)

Trang LED chay doc lap trong trinh duyet dat o dau cau (Chrome / Edge, toan man hinh F11),
khong can dang nhap, chi doc so lieu.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import OccupancySnapshot, get_config, get_state
from ..timeutil import UTC_OFFSET_HOURS, local_now

router = APIRouter(prefix="/display", tags=["F2.2 - Bang LED"])

STALE_SEC = 30


@router.get("/state")
def display_state(db: Session = Depends(get_db)):
    from .admin import is_open_now
    from .bridge import _get_bridge_state, _roll_day
    from .insights import wait_now

    cfg = get_config(db)
    latest = db.query(OccupancySnapshot).order_by(OccupancySnapshot.timestamp.desc()).first()
    stale = latest is None or datetime.utcnow() - latest.timestamp > timedelta(seconds=STALE_SEC)
    level = "OK" if stale else (latest.status or "OK")
    st = _get_bridge_state(db)
    _roll_day(st, local_now().strftime("%Y-%m-%d"))
    db.commit()
    lv = wait_now(db)
    warning = min(cfg.alert_threshold, max(1, round(cfg.alert_threshold * 0.75)))
    return {
        "onbridge": get_state(db).current_count,
        "level": level,                       # OK | WARNING | ALERT | CRITICAL
        "stale": stale,
        "dem": st.dem,
        "capacity": cfg.alert_threshold,
        "warning_threshold": warning,
        "wait_label": lv["wait_label"], "wait_label_en": lv["wait_label_en"],
        "is_open_now": is_open_now(cfg),
        "utc_offset_hours": UTC_OFFSET_HOURS,
        "server_time": local_now().isoformat(timespec="seconds"),
    }
