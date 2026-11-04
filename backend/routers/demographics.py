"""
backend/routers/demographics.py  —  MODULE M1 · F3 Phan tich khach tham quan
=============================================================================
Phu trach: MINH.   Chuc nang BFD: F3.2, F3.3   (FR-09)
Backlog: PB-07

Cac endpoint DA CHAY (chuyen nguyen tu api_server.py cu):
    POST /visit_events     luu ho so nhan khau hoc (che do 1 camera)
    GET  /visit_events     danh sach ho so, loc theo gender / age_range
    POST /region_stats     +1 bo dem tong hop (ngay, gio, khu vuc)
    GET  /stats/region     doc bo dem khu vuc

Endpoint SKELETON ("mock": true) - Minh lam that, Hoan dung cho trang
"Co cau khach" ngay tu bay gio ma khong phai cho:
    GET  /stats/demographics?date=YYYY-MM-DD
"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import RegionStat, VisitEvent
from ..schemas import RegionStatIn, VisitEventIn
from ..security import require_api_key

router = APIRouter(tags=["F3 - Phan tich khach tham quan"])


@router.post("/visit_events", dependencies=[Depends(require_api_key)])
def create_visit_event(event: VisitEventIn, db: Session = Depends(get_db)):
    row = VisitEvent(track_id=event.track_id, age=event.age,
                     age_range=event.age_range, gender=event.gender)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"saved": True, "id": row.id}


@router.get("/visit_events")
def list_visit_events(limit: int = 50, gender: Optional[str] = None,
                      age_range: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(VisitEvent)
    if gender:
        query = query.filter(VisitEvent.gender == gender)
    if age_range:
        query = query.filter(VisitEvent.age_range == age_range)
    rows = query.order_by(VisitEvent.id.desc()).limit(limit).all()
    return [
        {"id": r.id, "track_id": r.track_id, "timestamp": r.timestamp.isoformat(),
         "age": r.age, "age_range": r.age_range, "gender": r.gender}
        for r in rows
    ]


@router.post("/region_stats", dependencies=[Depends(require_api_key)])
def bump_region_stat(stat: RegionStatIn, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    date_str = now.strftime("%Y-%m-%d")
    row = (db.query(RegionStat)
           .filter(RegionStat.date == date_str, RegionStat.hour == now.hour,
                   RegionStat.region == stat.region)
           .first())
    if row is None:
        row = RegionStat(date=date_str, hour=now.hour, region=stat.region, count=0)
        db.add(row)
    row.count += 1
    db.commit()
    db.refresh(row)
    return {"saved": True, "date": row.date, "hour": row.hour, "region": row.region, "count": row.count}


@router.get("/stats/region")
def region_stats(db: Session = Depends(get_db)):
    rows = db.query(RegionStat).all()
    return [{"date": r.date, "hour": r.hour, "region": r.region, "count": r.count} for r in rows]


# ------------------------------------------------------------- SKELETON F3.3
# TODO(Minh, Sprint 4 - PB-07): thay du lieu mau bang truy van that tu
# visit_events (GROUP BY gio, gioi tinh, khoang tuoi) + region_stats.
# GIU NGUYEN cau truc JSON duoi day de trang "Co cau khach" khong phai sua.
@router.get("/stats/demographics")
def demographics_summary(date: str = ""):
    date = date or datetime.now().strftime("%Y-%m-%d")
    hours = list(range(8, 22))
    men = [5, 8, 12, 15, 11, 9, 14, 18, 22, 25, 30, 28, 20, 12]
    women = [6, 9, 14, 17, 13, 10, 16, 21, 26, 29, 35, 31, 22, 13]
    return {
        "mock": True,
        "date": date,
        "by_hour": [{"hour": h, "Man": m, "Woman": w} for h, m, w in zip(hours, men, women)],
        "age_range": {"0-12": 18, "13-17": 22, "18-24": 96, "25-34": 120,
                      "35-44": 71, "45-54": 40, "55-64": 25, "65+": 12},
        "domestic_vs_foreign": {"Trong nuoc": 230, "Nuoc ngoai": 174},
    }
