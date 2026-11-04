"""
backend/routers/counting.py  —  MODULE M1 · F1 Giam sat luong khach
=====================================================================
Phu trach: MINH.   Chuc nang BFD: F1.2, F1.4, F5.1   (FR-02, FR-10, FR-16, BRULE-10)

    POST /occupancy                camera bao so nguoi + muc canh bao (moi 2 giay)
    GET  /stats/occupancy          so nguoi dang tren cau
    GET  /stats/current            tong hop cho dashboard (3 bo dem tach rieng, muc canh bao, su co mo)
    GET  /stats/occupancy/history  dien bien so nguoi (mac dinh 60 phut gan nhat)
    POST /facade_pass              F1.4 1 nguoi di qua vung mat tien ma KHONG len cau
    GET  /stats/facade?date=       F1.4 luot mat tien theo gio

    (cu, giu cho camera_in.py / camera_out.py) POST /entry, POST /exit
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer
from sqlalchemy.orm import Session

from ..database import Base, get_db
from ..models import OccupancySnapshot, VisitEvent, get_config, get_state
from ..schemas import OccupancyIn, VisitEventIn
from ..security import require_api_key
from ..timeutil import iso, local_day_range_utc, local_now, parse_day, to_local

router = APIRouter(tags=["F1 - Giam sat luong khach"])


class FacadePass(Base):
    """F1.4 - 1 dong = 1 luot di qua vung mat tien ngoai cau (khong vao cau)."""
    __tablename__ = "facade_passes"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    camera_id = Column(Integer, nullable=True)


class FacadeIn(BaseModel):
    camera_id: Optional[int] = None
    count: int = 1


@router.post("/entry", dependencies=[Depends(require_api_key)])
def person_entry(event: VisitEventIn, db: Session = Depends(get_db)):
    row = VisitEvent(track_id=event.track_id, age=event.age, age_range=event.age_range,
                     gender=event.gender, origin=event.origin, camera_id=event.camera_id)
    db.add(row)
    state = get_state(db)
    state.current_count += 1
    db.commit()
    return {"saved": True, "id": row.id, "current_count": state.current_count}


@router.post("/exit", dependencies=[Depends(require_api_key)])
def person_exit(db: Session = Depends(get_db)):
    state = get_state(db)
    state.current_count = max(0, state.current_count - 1)
    db.commit()
    return {"current_count": state.current_count}


@router.post("/occupancy", dependencies=[Depends(require_api_key)])
def create_occupancy(snap: OccupancyIn, db: Session = Depends(get_db)):
    row = OccupancySnapshot(count=snap.count, status=snap.status)
    db.add(row)
    db.commit()
    return {"saved": True, "id": row.id}


@router.get("/stats/occupancy")
def occupancy_stats(db: Session = Depends(get_db)):
    return {"current_count": get_state(db).current_count}


def _today_range():
    today = local_now()
    return local_day_range_utc(today, today)


@router.get("/stats/current")
def current_stats(db: Session = Depends(get_db)):
    from .alerts import Incident
    from .bridge import BridgeCrossing

    state = get_state(db)
    cfg = get_config(db)
    latest = db.query(OccupancySnapshot).order_by(OccupancySnapshot.timestamp.desc()).first()
    status = "OK"
    stale = True
    if latest is not None:
        stale = datetime.utcnow() - latest.timestamp > timedelta(seconds=30)
        status = latest.status if not stale else "OK"
    start, end = _today_range()
    entries_today = (db.query(BridgeCrossing)
                     .filter(BridgeCrossing.direction == "in",
                             BridgeCrossing.timestamp >= start, BridgeCrossing.timestamp < end).count())
    facade_today = (db.query(FacadePass)
                    .filter(FacadePass.timestamp >= start, FacadePass.timestamp < end).count())
    visits_today = db.query(VisitEvent).filter(VisitEvent.timestamp >= start, VisitEvent.timestamp < end)
    genders = {}
    for (g,) in visits_today.with_entities(VisitEvent.gender).all():
        if g:
            genders[g] = genders.get(g, 0) + 1
    open_inc = db.query(Incident).filter(Incident.closed_at.is_(None)).count()
    return {
        "current_count": state.current_count,
        "current_status": status,
        "status_stale": stale,
        "alert_threshold": cfg.alert_threshold,
        "entries_today": entries_today,
        "facade_today": facade_today,
        "profiles_today": visits_today.count(),
        "gender_today": genders,
        "open_incidents": open_inc,
        "last_update": iso(latest.timestamp) if latest else None,
    }


@router.get("/stats/occupancy/history")
def occupancy_history(minutes: int = 60, limit: int = 5000, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(minutes=minutes)
    rows = (db.query(OccupancySnapshot).filter(OccupancySnapshot.timestamp >= since)
            .order_by(OccupancySnapshot.timestamp.desc()).limit(limit).all())
    return [{"timestamp": iso(r.timestamp), "count": r.count, "status": r.status} for r in reversed(rows)]


@router.post("/facade_pass", dependencies=[Depends(require_api_key)])
def facade_pass(payload: FacadeIn = FacadeIn(), db: Session = Depends(get_db)):
    for _ in range(max(1, min(payload.count, 100))):
        db.add(FacadePass(camera_id=payload.camera_id))
    db.commit()
    return {"saved": True}


@router.get("/stats/facade")
def facade_stats(date: str = "", db: Session = Depends(get_db)):
    day = parse_day(date) if date else local_now()
    start, end = local_day_range_utc(day, day)
    by_hour = {}
    for (ts,) in db.query(FacadePass.timestamp).filter(FacadePass.timestamp >= start,
                                                        FacadePass.timestamp < end).all():
        h = to_local(ts).hour
        by_hour[h] = by_hour.get(h, 0) + 1
    return {"date": day.strftime("%Y-%m-%d"), "total": sum(by_hour.values()),
            "by_hour": [{"hour": h, "facade_passes": by_hour[h]} for h in sorted(by_hour)]}
