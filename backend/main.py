"""
backend/main.py  —  Diem khoi dong backend SmartCau AI (FastAPI)
=================================================================
Thay cho src/api_server.py cu. Moi chuc nang BFD nam o 1 file rieng trong
backend/routers/ de 3 thanh vien lam SONG SONG ma khong sua chung 1 file:

    routers/counting.py      F1 Giam sat luong khach      (Minh)
    routers/bridge.py        F1 Dem khach tren cau bang 2 camera (Minh)
    routers/alerts.py        F2 Dieu tiet qua tai         (Minh + Hoan)
    routers/demographics.py  F3 Phan tich khach tham quan (Minh)
    routers/tickets.py       F4 Doi chieu ve              (Hoan)
    routers/reports.py       F5 Lap bao cao               (Hoan)
    routers/admin.py         F6 Quan tri he thong         (Khanh)
    routers/accounts.py      F6.1 Tai khoan & phan quyen   (Minh)

CHAY (tu THU MUC GOC du an, khong phai tu trong backend/):
    uvicorn backend.main:app --reload --port 8000

Mo http://127.0.0.1:8000/docs de xem/test toan bo API (nhom theo F1-F6).

Moi endpoint giu NGUYEN duong dan nhu api_server.py cu -> camera_in.py,
camera_out.py va trang admin KHONG can sua gi.

LUU Y: database o backend/smartcau.db (tu tao). Lan dau chay tu tao tai
khoan admin / admin123. Cot moi trong cac bang cu duoc tu bo sung khi khoi dong.
"""

from fastapi import FastAPI

from . import daily_report, models  # noqa: F401  (dang ky cac bang voi Base)
from .database import SessionLocal, ensure_schema
from .routers import accounts, admin, alerts, bridge, counting, demographics, reports, tickets
from .security import ADMIN_API_KEY, API_KEY
from .timeutil import UTC_OFFSET_HOURS

app = FastAPI(
    title="SmartCau AI API",
    description="Backend hệ thống Camera AI quản lý đám đông Chùa Cầu - Nhóm 50",
    version="1.0.0",
)

for r in (counting.router, bridge.router, alerts.router, demographics.router,
          tickets.router, reports.router, admin.router, accounts.router):
    app.include_router(r)

# Tao bang + bo sung cot moi SAU khi da import moi router.
ensure_schema()
with SessionLocal() as _db:
    accounts.ensure_default_admin(_db)
    admin.load_telegram_token(_db)        # token bot luu trong CSDL (trang Nguoi nhan canh bao)


@app.on_event("startup")
def _start_background_jobs():
    # Bao cao ngay tu dong sau gio dong cua (FR-11). Tat: SMARTCAU_DISABLE_SCHEDULER=1
    daily_report.start_scheduler()


@app.get("/health", tags=["He thong"])
def health():
    return {"status": "ok", "api_key_required": bool(API_KEY),
            "admin_key_required": bool(ADMIN_API_KEY), "utc_offset_hours": UTC_OFFSET_HOURS}
