"""
backend/routers/counting.py  —  MODULE M1 · F1 Giam sat luong khach
=====================================================================
Phu trach: MINH.   Chuc nang BFD: F1.2, F1.3, F1.4   (FR-02, FR-03, FR-16)
Backlog: PB-02, PB-13

Cac endpoint DA CHAY (chuyen nguyen tu api_server.py cu, khong doi hanh vi):
    POST /entry            camera VAO: +1 nguoi + luu ho so nhan khau hoc
    POST /exit             camera RA : -1 nguoi
    POST /occupancy        camera bao cao dinh ky so nguoi + trang thai
    GET  /stats/occupancy  so nguoi dang tren cau (thoi gian thuc)
    GET  /stats/current    tong hop nhanh cho dashboard

Endpoint SKELETON (tra du lieu mau, "mock": true) - Minh lam that o Sprint 4-5:
    POST /facade_pass      F1.4 dem luot qua vung mat tien (khong len cau)
    GET  /stats/facade     F1.4 thong ke luot mat tien theo gio
"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import OccupancySnapshot, VisitEvent, get_state
from ..schemas import OccupancyIn, VisitEventIn
from ..security import require_api_key

router = APIRouter(tags=["F1 - Giam sat luong khach"])


@router.post("/entry", dependencies=[Depends(require_api_key)])
def person_entry(event: VisitEventIn, db: Session = Depends(get_db)):
    row = VisitEvent(track_id=event.track_id, age=event.age,
                     age_range=event.age_range, gender=event.gender)
    db.add(row)
    state = get_state(db)
    state.current_count += 1
    db.commit()
    db.refresh(row)
    db.refresh(state)
    return {"saved": True, "id": row.id, "current_count": state.current_count}


@router.post("/exit", dependencies=[Depends(require_api_key)])
def person_exit(db: Session = Depends(get_db)):
    state = get_state(db)
    state.current_count = max(0, state.current_count - 1)
    db.commit()
    db.refresh(state)
    return {"current_count": state.current_count}


@router.post("/occupancy", dependencies=[Depends(require_api_key)])
def create_occupancy(snap: OccupancyIn, db: Session = Depends(get_db)):
    row = OccupancySnapshot(count=snap.count, status=snap.status)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"saved": True, "id": row.id}


@router.get("/stats/occupancy")
def occupancy_stats(db: Session = Depends(get_db)):
    state = get_state(db)
    return {"current_count": state.current_count}


@router.get("/stats/current")
def current_stats(db: Session = Depends(get_db)):
    state = get_state(db)
    latest_snapshot = db.query(OccupancySnapshot).order_by(OccupancySnapshot.id.desc()).first()
    total_visitors = db.query(VisitEvent).count()

    genders = {}
    ages = []
    for row in db.query(VisitEvent).all():
        if row.gender:
            genders[row.gender] = genders.get(row.gender, 0) + 1
        if row.age is not None:
            ages.append(row.age)

    return {
        "current_count": state.current_count,
        "current_status": latest_snapshot.status if latest_snapshot else "OK",
        "total_visitors_logged": total_visitors,
        "gender_breakdown": genders,
        "average_age": round(sum(ages) / len(ages), 1) if ages else None,
    }


@router.get("/stats/occupancy/history")
def occupancy_history(limit: int = 500, db: Session = Depends(get_db)):
    """Lich su so nguoi tren cau (tu bang occupancy_snapshots) - dung cho
    bieu do theo thoi gian o trang Tong quan / Bao cao."""
    rows = db.query(OccupancySnapshot).order_by(OccupancySnapshot.id.desc()).limit(limit).all()
    return [{"timestamp": r.timestamp.isoformat(), "count": r.count, "status": r.status}
            for r in reversed(rows)]


# ------------------------------------------------------------- SKELETON F1.4
# TODO(Minh, Sprint 5 - PB-13): them bang FacadePass vao file nay, camera
# goi POST /facade_pass khi 1 nguoi di qua vung mat tien ma KHONG len cau.
@router.post("/facade_pass", dependencies=[Depends(require_api_key)])
def facade_pass():
    return {"saved": False, "mock": True, "note": "Chua lam - F1.4 (PB-13)"}


@router.get("/stats/facade")
def facade_stats(date: str = ""):
    date = date or datetime.now().strftime("%Y-%m-%d")
    sample = [12, 18, 25, 30, 22, 15, 40, 65, 80, 55]
    return {
        "mock": True,
        "date": date,
        "by_hour": [{"hour": 8 + i, "facade_passes": v} for i, v in enumerate(sample)],
    }
