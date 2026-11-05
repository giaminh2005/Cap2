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
        - KPI Sprint 0: O1 (so phut co hon suc chua tren cau), O4 (% su co
          xu ly trong 3 phut), O5 (% canh bao sai), O8 (ty le chenh lech ve)
    GET /reports/heatmap?date_from=&date_to=      luot vao theo gio x thu trong tuan
    GET /reports/daily                            danh sach bao cao ngay tu dong
    GET /reports/daily/{date}/pdf                 tai PDF bao cao ngay
    POST /reports/daily/{date}/send               (quan ly) tao lai + gui lai
F5.3 xuat PDF / Excel dung backend/report_export.py.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import OccupancySnapshot, SystemEvent, VisitEvent, get_config
from ..security import require_manager
from ..timeutil import iso, local_day_range_utc, local_now, parse_day, to_local
from .demographics import summarize_visits

router = APIRouter(prefix="/reports", tags=["F5 - Lap bao cao"])

HANDLE_TARGET_SEC = 180      # O4: xu ly trong 3 phut
WEEKDAYS_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"]

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

    # O1: so phut (theo gio dia phuong) co it nhat 1 lan do > suc chua
    cap = get_config(db).alert_threshold
    over_minutes = {to_local(ts).strftime("%Y-%m-%d %H:%M") for (ts,) in db.query(OccupancySnapshot.timestamp)
                    .filter(OccupancySnapshot.timestamp >= s_utc, OccupancySnapshot.timestamp < e_utc,
                            OccupancySnapshot.count > cap).all()}
    real = [i for i in incidents if not i.false_alarm]
    within = [i for i in real if i.acked_at and (i.acked_at - i.opened_at).total_seconds() <= HANDLE_TARGET_SEC]
    false_n = len(incidents) - len(real)
    from .tickets import TicketCount, reconciliation
    ticket_days = sorted({d for (d,) in db.query(TicketCount.date).filter(
        TicketCount.date >= start.strftime("%Y-%m-%d"), TicketCount.date <= end.strftime("%Y-%m-%d")).all()})
    o8_entries = o8_tickets = 0
    for d in ticket_days:          # cung cach tinh voi trang Doi chieu ve (chi so cac gio da nhap ve)
        rec = reconciliation(date=d, db=db)
        if rec["tickets_sold"] is not None:
            o8_entries += rec["compared_entries"]
            o8_tickets += rec["tickets_sold"]
    kpis = {
        "o1_minutes_over": len(over_minutes),
        "o1_minutes_per_day": round(len(over_minutes) / span, 1),
        "o4_handled_within_3min_pct": round(len(within) / len(real) * 100, 1) if real else None,
        "o4_real_incidents": len(real),
        "o5_false_alarm_pct": round(false_n / len(incidents) * 100, 1) if incidents else None,
        "o5_false_alarms": false_n,
        "o8_gap_rate_pct": round((o8_entries - o8_tickets) / o8_entries * 100, 1) if o8_entries else None,
        "capacity": cap,
    }

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
        "kpis": kpis,
    }


@router.get("/heatmap")
def heatmap(date_from: str = "", date_to: str = "", db: Session = Depends(get_db)):
    """Luot vao cau theo (thu trong tuan x gio) - Sprint 0 F7 'bieu do nhiet theo gio va thu'.
    Mac dinh 8 tuan gan nhat. cells[weekday][hour] = tong luot vao; avg = trung binh moi ngay do."""
    from .bridge import BridgeCrossing
    try:
        end = parse_day(date_to) if date_to else local_now()
        start = parse_day(date_from) if date_from else end - timedelta(days=55)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày phải có dạng YYYY-MM-DD.")
    if end < start:
        raise HTTPException(status_code=400, detail="Ngày kết thúc phải sau ngày bắt đầu.")
    s_loc = datetime(start.year, start.month, start.day)
    e_loc = datetime(end.year, end.month, end.day) + timedelta(days=1)
    cells = [[0] * 24 for _ in range(7)]
    for (t,) in db.query(BridgeCrossing.local_time).filter(
            BridgeCrossing.direction == "in", BridgeCrossing.local_time >= s_loc, BridgeCrossing.local_time < e_loc).all():
        cells[t.weekday()][t.hour] += 1
    n_days = [0] * 7
    d = datetime(start.year, start.month, start.day)
    while d.date() <= end.date():
        n_days[d.weekday()] += 1
        d += timedelta(days=1)
    avg = [[round(cells[w][h] / n_days[w], 1) if n_days[w] else 0 for h in range(24)] for w in range(7)]
    return {"date_from": start.strftime("%Y-%m-%d"), "date_to": end.strftime("%Y-%m-%d"),
            "weekdays": WEEKDAYS_VI, "hours": list(range(24)), "cells": cells, "avg_per_day": avg, "days": n_days}


# --------------------------------------------------------- bao cao ngay tu dong
@router.get("/daily")
def list_daily(limit: int = 60, db: Session = Depends(get_db)):
    from ..daily_report import DailyReport
    rows = db.query(DailyReport).order_by(DailyReport.date.desc()).limit(limit).all()
    return [{"date": r.date, "created_at": iso(r.created_at), "sent_at": iso(r.sent_at),
             "delivery": r.delivery or "", "total_entries": r.total_entries, "incidents": r.incidents}
            for r in rows]


@router.get("/daily/{date}/pdf")
def daily_pdf(date: str, db: Session = Depends(get_db)):
    from ..daily_report import DailyReport, pdf_of
    r = db.query(DailyReport).filter(DailyReport.date == date).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Chưa có báo cáo ngày này.")
    return Response(pdf_of(r), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="bao_cao_ngay_{date}.pdf"'})


@router.post("/daily/{date}/send", dependencies=[Depends(require_manager)])
def resend_daily(date: str, db: Session = Depends(get_db)):
    from ..daily_report import generate
    try:
        day = parse_day(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày phải có dạng YYYY-MM-DD.")
    r = generate(db, day, send=True, sync_send=True)
    return {"date": r.date, "sent_at": iso(r.sent_at), "delivery": r.delivery}


@router.get("/weekly/pdf")
def weekly_pdf(db: Session = Depends(get_db)):
    """PDF bao cao tuan vua qua (Thu 2 - Chu nhat)."""
    from ..daily_report import weekly_summaries
    from ..report_export import to_pdf
    cur, _ = weekly_summaries(db, local_now().replace(hour=0, minute=0, second=0, microsecond=0))
    return Response(to_pdf(cur), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="bao_cao_tuan_{cur["date_from"]}_{cur["date_to"]}.pdf"'})


@router.post("/weekly/send", dependencies=[Depends(require_manager)])
def send_weekly_now(db: Session = Depends(get_db)):
    """Gui ngay bao cao tuan vua qua (binh thuong tu gui sang thu Hai)."""
    from ..daily_report import send_weekly
    return send_weekly(db, sync_send=True)
