"""
backend/main.py  —  Diem khoi dong backend SmartCau AI (FastAPI)
=================================================================
Thay cho src/api_server.py cu. Moi chuc nang BFD nam o 1 file rieng trong
backend/routers/ de 3 thanh vien lam SONG SONG ma khong sua chung 1 file:

    routers/counting.py      F1 Giam sat luong khach      (Minh)
    routers/alerts.py        F2 Dieu tiet qua tai         (Minh + Hoan)
    routers/demographics.py  F3 Phan tich khach tham quan (Minh)
    routers/tickets.py       F4 Doi chieu ve              (Hoan)
    routers/reports.py       F5 Lap bao cao               (Hoan)
    routers/admin.py         F6 Quan tri he thong         (Khanh + Minh)

CHAY (tu THU MUC GOC du an, khong phai tu trong backend/):
    uvicorn backend.main:app --reload --port 8000

Mo http://127.0.0.1:8000/docs de xem/test toan bo API (nhom theo F1-F6).

Moi endpoint giu NGUYEN duong dan nhu api_server.py cu -> camera_in.py,
camera_out.py va trang admin KHONG can sua gi.

LUU Y: database gio nam o backend/smartcau.db (khong con o src/). Lan dau
chay se tao file moi, rong - chay "python tools/seed_demo_data.py" de nap
du lieu mau khi chua bat camera.
"""

from fastapi import FastAPI

from . import models  # noqa: F401  (dang ky cac bang loi voi Base)
from .database import Base, engine
from .routers import admin, alerts, counting, demographics, reports, tickets
from .security import ADMIN_API_KEY, API_KEY

app = FastAPI(
    title="SmartCau AI API",
    description="Backend he thong Camera AI quan ly dam dong Chua Cau - Nhom 50",
    version="0.3.0",
)

for r in (counting.router, alerts.router, demographics.router,
          tickets.router, reports.router, admin.router):
    app.include_router(r)

# Tao bang SAU khi da import moi router (bang moi khai bao trong router
# cung duoc tao).
Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["He thong"])
def health():
    return {"status": "ok", "api_key_required": bool(API_KEY),
            "admin_key_required": bool(ADMIN_API_KEY)}
