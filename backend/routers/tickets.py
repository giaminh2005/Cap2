"""
backend/routers/tickets.py  —  MODULE M5 · F4 Doi chieu ve tham quan
=====================================================================
Phu trach: HOAN.   Chuc nang BFD: F4.1, F4.2   (FR-14)
Backlog: PB-12  (F4.3 doi chieu khach quoc te - NGOAI MVP, khong lam)

Endpoint SKELETON ("mock": true):
    POST /tickets                          F4.1 nhap so cuong ve thu theo gio
    GET  /tickets/reconciliation?date=     F4.2 ty le chenh lech luot vao / ve

TODO(Hoan, Sprint 5):
  1. Them bang TicketCount NGAY TRONG FILE NAY (date, hour, ticket_count,
     entered_by) - khong sua backend/models.py.
  2. /tickets/reconciliation: dem luot vao that tu bang visit_events theo
     gio cua ngay do, so voi TicketCount -> gap = entries - tickets,
     gap_rate_pct = gap / entries * 100.
"""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/tickets", tags=["F4 - Doi chieu ve"])


class TicketCountIn(BaseModel):
    date: str          # "YYYY-MM-DD"
    hour: int          # 0-23
    ticket_count: int
    entered_by: str = ""


@router.post("")
def add_ticket_count(payload: TicketCountIn):
    return {"saved": False, "mock": True, "received": payload.model_dump(),
            "detail": "Chua luu that - F4.1 (PB-12)"}


@router.get("/reconciliation")
def reconciliation(date: str = ""):
    date = date or datetime.now().strftime("%Y-%m-%d")
    entries = [60, 85, 110, 140, 120, 95, 130, 160, 175, 150]
    tickets = [55, 80, 98, 121, 110, 90, 112, 139, 150, 131]
    rows = []
    for i, (e, t) in enumerate(zip(entries, tickets)):
        rows.append({"hour": 8 + i, "entries": e, "tickets": t, "gap": e - t,
                     "gap_rate_pct": round((e - t) / e * 100, 1)})
    total_e, total_t = sum(entries), sum(tickets)
    return {
        "mock": True,
        "date": date,
        "entries_counted": total_e,
        "tickets_sold": total_t,
        "gap": total_e - total_t,
        "gap_rate_pct": round((total_e - total_t) / total_e * 100, 1),
        "by_hour": rows,
    }
