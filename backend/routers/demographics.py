"""
backend/routers/demographics.py  —  MODULE M1 · F3 Phan tich khach tham quan
=============================================================================
Phu trach: MINH.   Chuc nang BFD: F3.2, F3.3   (FR-09, BRULE-05, BRULE-06)

    POST /visit_events             camera luu nhan cua 1 luot khach vao (gioi tinh, khoang tuoi, trong/ngoai nuoc)
    GET  /visit_events             tra cuu, loc theo ngay / gioi tinh / tuoi / nguon khach
    GET  /stats/demographics       co cau khach theo gio, khoang tuoi, trong nuoc / nuoc ngoai

BRULE-06: luot co gender = None (do tin cay < 70%) duoc dem rieng la
"Khong xac dinh" va KHONG dua vao ty le.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import VisitEvent
from ..schemas import VisitEventIn
from ..security import require_api_key
from ..timeutil import iso, local_day_range_utc, local_now, parse_day, to_local

router = APIRouter(tags=["F3 - Phan tich khach tham quan"])

AGE_ORDER = ["0-5", "6-12", "13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65-69", "70+"]
ORIGINS = ("Trong nuoc", "Nuoc ngoai")


def _range(date_from: str, date_to: str):
    try:
        d1 = parse_day(date_from) if date_from else local_now()
        d2 = parse_day(date_to) if date_to else d1
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày phải có dạng YYYY-MM-DD.")
    if d2 < d1:
        raise HTTPException(status_code=400, detail="Ngày kết thúc phải sau ngày bắt đầu.")
    return d1, d2


@router.post("/visit_events", dependencies=[Depends(require_api_key)])
def create_visit_event(event: VisitEventIn, db: Session = Depends(get_db)):
    origin = event.origin if event.origin in ORIGINS else None
    row = VisitEvent(track_id=event.track_id, age=event.age, age_range=event.age_range,
                     gender=event.gender, origin=origin, camera_id=event.camera_id)
    db.add(row)
    db.commit()
    return {"saved": True, "id": row.id}


@router.get("/visit_events")
def list_visit_events(limit: int = 200, gender: Optional[str] = None, age_range: Optional[str] = None,
                      origin: Optional[str] = None, date_from: str = "", date_to: str = "",
                      db: Session = Depends(get_db)):
    q = db.query(VisitEvent)
    if date_from or date_to:
        d1, d2 = _range(date_from, date_to)
        start, end = local_day_range_utc(d1, d2)
        q = q.filter(VisitEvent.timestamp >= start, VisitEvent.timestamp < end)
    if gender == "unknown":
        q = q.filter(VisitEvent.gender.is_(None))
    elif gender:
        q = q.filter(VisitEvent.gender == gender)
    if age_range:
        q = q.filter(VisitEvent.age_range == age_range)
    if origin:
        q = q.filter(VisitEvent.origin == origin)
    rows = q.order_by(VisitEvent.id.desc()).limit(limit).all()
    return [{"id": r.id, "track_id": r.track_id, "timestamp": iso(r.timestamp), "age": r.age,
             "age_range": r.age_range, "gender": r.gender, "origin": r.origin, "camera_id": r.camera_id}
            for r in rows]


def summarize_visits(rows):
    """Dung chung cho /stats/demographics va /reports/summary."""
    gender, age, origin = {"Man": 0, "Woman": 0}, {a: 0 for a in AGE_ORDER}, {o: 0 for o in ORIGINS}
    unknown = 0
    by_hour = {}
    for r in rows:
        h = to_local(r.timestamp).hour
        b = by_hour.setdefault(h, {"hour": h, "Man": 0, "Woman": 0, "unknown": 0})
        if r.gender not in ("Man", "Woman"):
            unknown += 1
            b["unknown"] += 1
            continue
        gender[r.gender] += 1
        b[r.gender] += 1
        if r.age_range in age:
            age[r.age_range] += 1
        if r.origin in origin:
            origin[r.origin] += 1
    return {"total": len(rows), "identified": len(rows) - unknown, "unknown": unknown,
            "gender": gender, "age_range": age, "origin": origin,
            "by_hour": [by_hour[h] for h in sorted(by_hour)]}


@router.get("/stats/demographics")
def demographics_summary(date_from: str = "", date_to: str = "", date: str = "", db: Session = Depends(get_db)):
    d1, d2 = _range(date_from or date, date_to or date)
    start, end = local_day_range_utc(d1, d2)
    rows = db.query(VisitEvent).filter(VisitEvent.timestamp >= start, VisitEvent.timestamp < end).all()
    return {"date_from": d1.strftime("%Y-%m-%d"), "date_to": d2.strftime("%Y-%m-%d"), **summarize_visits(rows)}

