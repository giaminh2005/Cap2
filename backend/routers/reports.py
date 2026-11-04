"""
backend/routers/reports.py  —  MODULE M4 · F5 Lap bao cao luong khach
======================================================================
Phu trach: HOAN.   Chuc nang BFD: F5.2, F5.3   (FR-11)

    GET /reports/summary?period=day|week|month&date=YYYY-MM-DD
        - luot vao cau (2 camera chan cau), luot qua mat tien
        - theo khung 15 phut (bao cao ngay), 4 khung gio trong ngay, theo ngay
        - gio cao diem va so nguoi tren cau cao nhat
        - co cau khach (gioi tinh, khoang tuoi, trong nuoc / nuoc ngoai)
        - canh bao, su co, thoi gian xu ly trung binh
F5.3 xuat PDF / Excel lam o trang "Bao cao dinh ky" tu JSON nay.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import OccupancySnapshot, SystemEvent, VisitEvent
from ..timeutil import local_day_range_utc, local_now, parse_day, to_local
from .demographics import summarize_visits

router = APIRouter(prefix="/reports", tags=["F5 - Lap bao cao"])

TIME_SLOTS = [("Sáng (06–11h)", 6, 11), ("Trưa (11–14h)", 11, 14),
              ("Chiều (14–18h)", 14, 18), ("Tối (18–23h)", 18, 23)]


@router.get("/summary")
def report_summary(period: str = "day", date: str = "", db: Session = Depends(get_db)):
    from .alerts import Incident
    from .bridge import BridgeCrossing
    from .counting import FacadePass

    if period not in ("day", "week", "month"):
        raise HTTPException(status_code=400, detail="period phải là day, week hoặc month.")
    try:
        end = parse_day(date) if date else local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày phải có dạng YYYY-MM-DD.")
    span = {"day": 1, "week": 7, "month": 30}[period]
    start = end - timedelta(days=span - 1)
    s_utc, e_utc = local_day_range_utc(start, end)

    entries = [to_local(ts) for (ts,) in db.query(BridgeCrossing.timestamp)
               .filter(BridgeCrossing.direction == "in", BridgeCrossing.timestamp >= s_utc,
                       BridgeCrossing.timestamp < e_utc).all()]
    exits = (db.query(BridgeCrossing).filter(BridgeCrossing.direction == "out",
                                             BridgeCrossing.timestamp >= s_utc,
                                             BridgeCrossing.timestamp < e_utc).count())
    facade = (db.query(FacadePass).filter(FacadePass.timestamp >= s_utc, FacadePass.timestamp < e_utc).count())

    by_day = {(start + timedelta(days=i)).strftime("%Y-%m-%d"): 0 for i in range(span)}
    by_hour, by_15 = {}, {}
    for t in entries:
        by_day[t.strftime("%Y-%m-%d")] = by_day.get(t.strftime("%Y-%m-%d"), 0) + 1
        by_hour[t.hour] = by_hour.get(t.hour, 0) + 1
        slot = f"{t.hour:02d}:{(t.minute // 15) * 15:02d}"
        by_15[slot] = by_15.get(slot, 0) + 1
    slots = [{"slot": name, "entries": sum(v for h, v in by_hour.items() if a <= h < b)}
             for name, a, b in TIME_SLOTS]

    peak = (db.query(OccupancySnapshot).filter(OccupancySnapshot.timestamp >= s_utc,
                                                OccupancySnapshot.timestamp < e_utc)
            .order_by(OccupancySnapshot.count.desc()).first())
    peak_hour_entries = max(by_hour, key=by_hour.get) if by_hour else None

    events = {}
    for (et,) in db.query(SystemEvent.event_type).filter(SystemEvent.timestamp >= s_utc,
                                                         SystemEvent.timestamp < e_utc).all():
        events[et] = events.get(et, 0) + 1
    incidents = db.query(Incident).filter(Incident.opened_at >= s_utc, Incident.opened_at < e_utc).all()
    handled = [(i.acked_at - i.opened_at).total_seconds() for i in incidents if i.acked_at]
    durations = [((i.closed_at or datetime.utcnow()) - i.opened_at).total_seconds() for i in incidents]

    visits = db.query(VisitEvent).filter(VisitEvent.timestamp >= s_utc, VisitEvent.timestamp < e_utc).all()

    return {
        "period": period,
        "date_from": start.strftime("%Y-%m-%d"),
        "date_to": end.strftime("%Y-%m-%d"),
        "total_entries": len(entries),
        "total_exits": exits,
        "facade_passes": facade,
        "peak_hour": peak_hour_entries,
        "peak_hour_entries": by_hour.get(peak_hour_entries, 0) if peak_hour_entries is not None else 0,
        "peak_count": peak.count if peak else 0,
        "peak_time": to_local(peak.timestamp).isoformat() if peak else None,
        "by_day": [{"date": d, "entries": n} for d, n in sorted(by_day.items())],
        "by_hour": [{"hour": h, "entries": by_hour[h]} for h in sorted(by_hour)],
        "by_15min": [{"slot": k, "entries": by_15[k]} for k in sorted(by_15)] if period == "day" else [],
        "time_slots": slots,
        "demographics": summarize_visits(visits),
        "alerts": {"WARNING": events.get("WARNING", 0), "CRITICAL_ALERT": events.get("CRITICAL_ALERT", 0),
                   "GROUP_DETECTED": events.get("GROUP_DETECTED", 0), "CAMERA_LOST": events.get("CAMERA_LOST", 0)},
        "incidents": len(incidents),
        "incidents_acked": len(handled),
        "avg_handle_seconds": round(sum(handled) / len(handled)) if handled else None,
        "avg_incident_seconds": round(sum(durations) / len(durations)) if durations else None,
    }
