"""
backend/routers/reports.py  —  MODULE M4 · F5 Lap bao cao luong khach
======================================================================
Phu trach: HOAN.   Chuc nang BFD: F5.2, F5.3   (FR-11)
Backlog: PB-10

Endpoint SKELETON ("mock": true):
    GET /reports/summary?period=day|week|month&date=YYYY-MM-DD

TODO(Hoan, Sprint 4-5):
  1. Thay du lieu mau bang truy van that tu bang visit_events (luot vao),
     occupancy_snapshots (gio cao diem) va system_events (so lan canh bao).
     Goi y: dung db.query(...).filter(VisitEvent.timestamp >= tu_ngay, ...).
  2. GIU NGUYEN cac khoa JSON duoi day -> trang "Bao cao" khong phai sua.
  3. F5.3 Xuat bao cao: trang Bao cao tu xuat CSV/Excel tu JSON nay (khong
     can endpoint rieng).
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/reports", tags=["F5 - Lap bao cao"])


@router.get("/summary")
def report_summary(period: str = "day", date: str = ""):
    if period not in ("day", "week", "month"):
        raise HTTPException(status_code=400, detail="period phai la day, week hoac month.")
    end = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    span = {"day": 1, "week": 7, "month": 30}[period]
    start = end - timedelta(days=span - 1)
    return {
        "mock": True,
        "period": period,
        "date_from": start.strftime("%Y-%m-%d"),
        "date_to": end.strftime("%Y-%m-%d"),
        "total_entries": 1240 * span,
        "peak_hour": 16,
        "peak_count": 23,
        "by_day": [{"date": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
                    "entries": 1100 + (i * 37) % 300} for i in range(span)],
        "gender": {"Man": 560 * span, "Woman": 680 * span},
        "age_range": {"18-24": 300 * span, "25-34": 420 * span, "35-44": 260 * span, "khac": 260 * span},
        "alerts": {"WARNING": 6 * span, "CRITICAL_ALERT": 2 * span},
        "avg_handle_seconds": 95,
    }
