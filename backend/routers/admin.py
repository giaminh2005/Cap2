"""
backend/routers/admin.py  —  MODULE M7 · F6 Quan tri he thong
==============================================================
Chuc nang BFD: F6.1, F6.2, F6.3   (FR-12, FR-13)

Phan DA CHAY (chuyen nguyen tu api_server.py cu):
    GET  /config     xem nguong canh bao (cong khai - camera doc duoc)
    PUT  /config     doi nguong canh bao (can X-Admin-Key neu da set)

Phan SKELETON - phu trach: KHANH (PB-11, F6.3 nguoi nhan canh bao):
    GET    /recipients          danh sach nguoi nhan canh bao
    POST   /recipients          them nguoi nhan
    DELETE /recipients/{id}     xoa nguoi nhan
    -> hien luu TAM trong bo nho (mat khi tat server).
    TODO(Khanh, Sprint 4): them bang Recipient NGAY TRONG FILE NAY
       (id, name, channel, address, active) thay cho list _RECIPIENTS.
       Goi y: chep y het cach lam cua bang SystemConfig trong models.py.
    TODO(Minh, Sprint 5): telegram_alert.py doc danh sach nay de gui canh
       bao toi dung nguoi (thay vi 1 chat_id co dinh trong bien moi truong).

Phan SKELETON - phu trach: MINH (F6.1 quan ly tai khoan, gop trong PB-T3):
    POST /auth/login  -> tra ve vai tro (admin / quan_ly / nguoi_truc) de
    frontend an/hien trang theo vai tro. Hien chi co tai khoan demo.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import get_config
from ..schemas import ConfigIn
from ..security import require_admin

router = APIRouter(tags=["F6 - Quan tri he thong"])


@router.get("/config")
def read_config(db: Session = Depends(get_db)):
    cfg = get_config(db)
    return {"alert_threshold": cfg.alert_threshold,
            "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None}


@router.put("/config", dependencies=[Depends(require_admin)])
def update_config(payload: ConfigIn, db: Session = Depends(get_db)):
    if payload.alert_threshold < 1:
        raise HTTPException(status_code=400, detail="alert_threshold phai >= 1.")
    cfg = get_config(db)
    cfg.alert_threshold = payload.alert_threshold
    db.commit()
    db.refresh(cfg)
    return {"alert_threshold": cfg.alert_threshold,
            "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None}


# ------------------------------------------------------------- SKELETON F6.3
class RecipientIn(BaseModel):
    name: str
    channel: str = "telegram"   # telegram | zalo | sms | email
    address: str                # chat_id / so dien thoai / email
    active: bool = True


_RECIPIENTS: List[dict] = [
    {"id": 1, "name": "Nguoi truc dau cau Bac", "channel": "telegram", "address": "123456789", "active": True},
    {"id": 2, "name": "Quan ly Trung tam", "channel": "telegram", "address": "987654321", "active": True},
]


@router.get("/recipients")
def list_recipients():
    return {"mock": True, "items": _RECIPIENTS}


@router.post("/recipients", dependencies=[Depends(require_admin)])
def add_recipient(payload: RecipientIn):
    new_id = max([r["id"] for r in _RECIPIENTS], default=0) + 1
    item = {"id": new_id, **payload.model_dump()}
    _RECIPIENTS.append(item)
    return {"mock": True, "item": item}


@router.delete("/recipients/{recipient_id}", dependencies=[Depends(require_admin)])
def delete_recipient(recipient_id: int):
    for i, r in enumerate(_RECIPIENTS):
        if r["id"] == recipient_id:
            _RECIPIENTS.pop(i)
            return {"mock": True, "deleted": recipient_id}
    raise HTTPException(status_code=404, detail="Khong tim thay nguoi nhan.")


# ------------------------------------------------------------- SKELETON F6.1
class LoginIn(BaseModel):
    username: str
    password: str


_DEMO_USERS = {
    "admin": ("admin123", "admin"),
    "quanly": ("quanly123", "quan_ly"),
    "truc": ("truc123", "nguoi_truc"),
}


@router.post("/auth/login")
def login(payload: LoginIn):
    user = _DEMO_USERS.get(payload.username)
    if not user or user[0] != payload.password:
        raise HTTPException(status_code=401, detail="Sai ten dang nhap hoac mat khau.")
    return {"mock": True, "username": payload.username, "role": user[1]}
