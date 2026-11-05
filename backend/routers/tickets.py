"""
backend/routers/tickets.py  —  MODULE M5 · F4 Doi chieu ve tham quan
=====================================================================
Phu trach: HOAN.   Chuc nang BFD: F4.1, F4.2   (FR-14, BRULE-08)
(F4.3 doi chieu khach quoc te - NGOAI MVP)

    POST   /tickets                       nhap so cuong ve theo ngay (hour = null) hoac theo gio
    POST   /tickets/bulk                  nhap nhieu dong (tu file CSV/Excel)
    GET    /tickets?date_from=&date_to=   danh sach so ve da nhap
    DELETE /tickets/{id}
    GET    /tickets/reconciliation?date=  ty le chenh lech luot vao long cau / so ve

BRULE-08: chi so LUOT VAO LONG CAU (2 camera chan cau), KHONG dung luot qua
vung mat tien. Ket qua chi dung de dieu phoi, khong lam bang chung xu phat.
    gap = luot vao - so ve;  gap_rate_pct = gap / luot vao * 100
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from ..database import Base, get_db
from ..models import log_audit
from ..security import Principal, require_staff
from ..timeutil import iso, local_day_range_utc, local_now, parse_day, to_local

router = APIRouter(prefix="/tickets", tags=["F4 - Doi chieu ve"])


class TicketCount(Base):
    __tablename__ = "ticket_counts"
    id = Column(Integer, primary_key=True)
    date = Column(String, index=True)          # YYYY-MM-DD (gio dia phuong)
    hour = Column(Integer, nullable=True)      # None = ca ngay
    ticket_count = Column(Integer)
    entered_by = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class TicketIn(BaseModel):
    date: str
    hour: Optional[int] = None
    ticket_count: int


def _validate(t: TicketIn):
    try:
        parse_day(t.date)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Ngày '{t.date}' phải có dạng YYYY-MM-DD.")
    if t.hour is not None and not 0 <= t.hour <= 23:
        raise HTTPException(status_code=400, detail="Giờ phải từ 0 đến 23.")
    if t.ticket_count < 0:
        raise HTTPException(status_code=400, detail="Số vé không được âm.")


def _upsert(db, t: TicketIn, who: str) -> TicketCount:
    row = db.query(TicketCount).filter(TicketCount.date == t.date, TicketCount.hour.is_(None)
                                       if t.hour is None else TicketCount.hour == t.hour).first()
    if row is None:
        row = TicketCount(date=t.date, hour=t.hour)
        db.add(row)
    row.ticket_count, row.entered_by, row.created_at = t.ticket_count, who, datetime.utcnow()
    return row


def _json(r: TicketCount) -> dict:
    return {"id": r.id, "date": r.date, "hour": r.hour, "ticket_count": r.ticket_count,
            "entered_by": r.entered_by, "created_at": iso(r.created_at)}


@router.post("")
def add_ticket_count(payload: TicketIn, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    _validate(payload)
    row = _upsert(db, payload, p.display)
    log_audit(db, p.username, "Nhập số vé", f"{payload.date} {'cả ngày' if payload.hour is None else f'{payload.hour}h'}: {payload.ticket_count}")
    db.commit()
    db.refresh(row)
    return _json(row)


@router.post("/bulk")
def add_bulk(items: List[TicketIn], p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    for t in items:
        _validate(t)
    for t in items:
        _upsert(db, t, p.display)
    log_audit(db, p.username, "Nhập số vé từ tệp", f"{len(items)} dòng")
    db.commit()
    return {"saved": len(items)}


@router.get("")
def list_tickets(date_from: str = "", date_to: str = "", db: Session = Depends(get_db)):
    q = db.query(TicketCount)
    if date_from:
        q = q.filter(TicketCount.date >= date_from)
    if date_to:
        q = q.filter(TicketCount.date <= date_to)
    return [_json(r) for r in q.order_by(TicketCount.date.desc(), TicketCount.hour).all()]


@router.delete("/{tid}")
def delete_ticket(tid: int, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    r = db.query(TicketCount).filter(TicketCount.id == tid).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy dòng số vé.")
    log_audit(db, p.username, "Xóa số vé", f"{r.date} {r.hour}")
    db.delete(r)
    db.commit()
    return {"deleted": tid}


def _rate(entries, tickets):
    return round((entries - tickets) / entries * 100, 1) if entries else None


@router.get("/reconciliation")
def reconciliation(date: str = "", db: Session = Depends(get_db)):
    from .bridge import BridgeCrossing
    try:
        day = parse_day(date) if date else local_now()
    except ValueError:
        raise HTTPException(status_code=400, detail="Ngày phải có dạng YYYY-MM-DD.")
    day_s = day.strftime("%Y-%m-%d")
    start, end = local_day_range_utc(day, day)
    entries_by_hour = {}
    for (ts,) in db.query(BridgeCrossing.timestamp).filter(
            BridgeCrossing.direction == "in", BridgeCrossing.timestamp >= start,
            BridgeCrossing.timestamp < end).all():
        h = to_local(ts).hour
        entries_by_hour[h] = entries_by_hour.get(h, 0) + 1
    tickets = db.query(TicketCount).filter(TicketCount.date == day_s).all()
    hourly = {t.hour: t.ticket_count for t in tickets if t.hour is not None}
    daily = next((t.ticket_count for t in tickets if t.hour is None), None)

    entries_total = sum(entries_by_hour.values())
    tickets_total = daily if daily is not None else (sum(hourly.values()) if hourly else None)
    compared_entries = entries_total
    if daily is None and hourly:
        # chi so sanh nhung gio DA nhap so ve, tranh lech do gio chua nhap
        compared_entries = sum(entries_by_hour.get(h, 0) for h in hourly)
    rows = []
    if hourly:
        for h in sorted(set(entries_by_hour) | set(hourly)):
            e, t = entries_by_hour.get(h, 0), hourly.get(h)
            rows.append({"hour": h, "entries": e, "tickets": t,
                         "gap": e - t if t is not None else None,
                         "gap_rate_pct": _rate(e, t) if t is not None else None})
    else:
        rows = [{"hour": h, "entries": entries_by_hour[h], "tickets": None, "gap": None, "gap_rate_pct": None}
                for h in sorted(entries_by_hour)]
    return {
        "date": day_s,
        "mode": "hour" if hourly and daily is None else "day",
        "entries_counted": entries_total,
        "tickets_sold": tickets_total,
        "compared_entries": compared_entries,
        "gap": compared_entries - tickets_total if tickets_total is not None else None,
        "gap_rate_pct": _rate(compared_entries, tickets_total) if tickets_total is not None else None,
        "by_hour": rows,
    }
