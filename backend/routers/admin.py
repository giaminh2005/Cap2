"""
backend/routers/admin.py  —  MODULE M7 · F6 Quan tri he thong
==============================================================
Chuc nang BFD: F6.2, F6.3, PB-06   (FR-13, NFR-04, NFR-05, BRULE-07, BRULE-09)
Phu trach: KHANH.

    GET  /config                      nguong canh bao + khung gio hoat dong (cong khai, camera doc)
    PUT  /config                      (admin) doi nguong / gio mo-dong cua, ghi nhat ky
    GET  /recipients                  (da dang nhap) danh sach nguoi nhan canh bao
    POST /recipients                  (admin) them
    PUT  /recipients/{id}             (admin) sua / bat-tat
    DELETE /recipients/{id}           (admin) xoa
    POST /recipients/{id}/test        (admin) gui tin nhan thu
    GET  /privacy/summary             (quan ly) du lieu dang luu tru
    POST /privacy/purge?older_than_days=   (admin) xoa du lieu cu hon N ngay (>= 730, BRULE-09)
    GET  /telegram/status             (admin) bot da ket noi chua, ten bot
    PUT  /telegram/token              (admin) luu token bot (kiem tra bang getMe truoc khi luu)
    DELETE /telegram/token            (admin) ngat ket noi
    GET  /telegram/chats              (admin) cac chat vua nhan tin cho bot -> lay chat_id
"""

import re
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from .. import notify
from ..database import Base, get_db
from ..models import OccupancySnapshot, SystemEvent, VisitEvent, get_config, log_audit
from ..security import Principal, require_admin, require_manager, require_staff
from ..timeutil import iso, local_now

router = APIRouter(tags=["F6 - Quan tri he thong"])

CHANNELS = {"telegram": "Telegram", "zalo": "Zalo OA", "sms": "SMS", "email": "Email"}
RETENTION_MIN_DAYS = 730   # BRULE-09: luu toi thieu 24 thang


# ------------------------------------------------------------------- bang
class Recipient(Base):
    """F6.3 - nguoi nhan canh bao."""
    __tablename__ = "recipients"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    channel = Column(String, default="telegram")
    address = Column(String)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def active_recipients(db: Session) -> List[dict]:
    return [{"name": r.name, "channel": r.channel, "address": r.address}
            for r in db.query(Recipient).filter(Recipient.active.is_(True)).all()]


# ----------------------------------------------------------------- cau hinh
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def is_open_now(cfg) -> bool:
    now = local_now()
    cur = now.hour * 60 + now.minute
    o, c = _minutes(cfg.open_time), _minutes(cfg.close_time)
    return o <= cur < c if o <= c else (cur >= o or cur < c)


def _config_json(cfg) -> dict:
    warning = min(cfg.alert_threshold, max(1, round(cfg.alert_threshold * 0.75)))
    return {"alert_threshold": cfg.alert_threshold, "warning_threshold": warning,
            "open_time": cfg.open_time, "close_time": cfg.close_time, "is_open_now": is_open_now(cfg),
            "updated_at": iso(cfg.updated_at), "updated_by": cfg.updated_by}


class ConfigUpdate(BaseModel):
    alert_threshold: Optional[int] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None


@router.get("/config")
def read_config(db: Session = Depends(get_db)):
    return _config_json(get_config(db))


@router.put("/config")
def update_config(payload: ConfigUpdate, p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    cfg = get_config(db)
    changes = []
    if payload.alert_threshold is not None:
        if not 1 <= payload.alert_threshold <= 500:
            raise HTTPException(status_code=400, detail="Sức chứa tối đa phải từ 1 đến 500 người.")
        if payload.alert_threshold != cfg.alert_threshold:
            changes.append(f"sức chứa {cfg.alert_threshold} → {payload.alert_threshold}")
            cfg.alert_threshold = payload.alert_threshold
    for field, label in (("open_time", "giờ mở cửa"), ("close_time", "giờ đóng cửa")):
        val = getattr(payload, field)
        if val is None:
            continue
        if not _TIME_RE.match(val):
            raise HTTPException(status_code=400, detail=f"{label.capitalize()} phải có dạng HH:MM.")
        if val != getattr(cfg, field):
            changes.append(f"{label} {getattr(cfg, field)} → {val}")
            setattr(cfg, field, val)
    if changes:
        cfg.updated_by = p.display
        cfg.updated_at = datetime.utcnow()
        log_audit(db, p.username, "Đổi cấu hình", "; ".join(changes))
    db.commit()
    db.refresh(cfg)
    return _config_json(cfg)


# --------------------------------------------------------------- nguoi nhan
class RecipientIn(BaseModel):
    name: str
    channel: str = "telegram"
    address: str
    active: bool = True


class RecipientUpdate(BaseModel):
    name: Optional[str] = None
    channel: Optional[str] = None
    address: Optional[str] = None
    active: Optional[bool] = None


def _rec_json(r: Recipient) -> dict:
    return {"id": r.id, "name": r.name, "channel": r.channel, "channel_label": CHANNELS.get(r.channel, r.channel),
            "address": r.address, "active": r.active, "created_at": iso(r.created_at)}


def _validate_rec(name, channel, address):
    if not (name or "").strip() or not (address or "").strip():
        raise HTTPException(status_code=400, detail="Cần nhập tên và địa chỉ nhận.")
    if channel not in CHANNELS:
        raise HTTPException(status_code=400, detail="Kênh không hợp lệ.")


@router.get("/recipients")
def list_recipients(p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    return [_rec_json(r) for r in db.query(Recipient).order_by(Recipient.id).all()]


@router.post("/recipients")
def add_recipient(payload: RecipientIn, p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    _validate_rec(payload.name, payload.channel, payload.address)
    r = Recipient(name=payload.name.strip(), channel=payload.channel, address=payload.address.strip(),
                  active=payload.active)
    db.add(r)
    log_audit(db, p.username, "Thêm người nhận", f"{r.name} ({CHANNELS[r.channel]})")
    db.commit()
    db.refresh(r)
    return _rec_json(r)


@router.put("/recipients/{rid}")
def update_recipient(rid: int, payload: RecipientUpdate, p: Principal = Depends(require_admin),
                     db: Session = Depends(get_db)):
    r = db.query(Recipient).filter(Recipient.id == rid).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người nhận.")
    for f in ("name", "channel", "address", "active"):
        v = getattr(payload, f)
        if v is not None:
            setattr(r, f, v.strip() if isinstance(v, str) else v)
    _validate_rec(r.name, r.channel, r.address)
    log_audit(db, p.username, "Sửa người nhận", f"{r.name} ({'bật' if r.active else 'tắt'})")
    db.commit()
    db.refresh(r)
    return _rec_json(r)


@router.delete("/recipients/{rid}")
def delete_recipient(rid: int, p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    r = db.query(Recipient).filter(Recipient.id == rid).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người nhận.")
    log_audit(db, p.username, "Xóa người nhận", r.name)
    db.delete(r)
    db.commit()
    return {"deleted": rid}


@router.post("/recipients/{rid}/test")
def test_recipient(rid: int, p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    r = db.query(Recipient).filter(Recipient.id == rid).first()
    if r is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy người nhận.")
    from html import escape

    from ..messages import status_message
    text = (f"🔔 <b>Tin nhắn thử</b> gửi bởi {escape(p.display)} lúc {local_now():%H:%M %d/%m/%Y}.\n"
            f"Từ nay {escape(r.name)} sẽ nhận cảnh báo của Chùa Cầu tại đây. Gõ /help để xem lệnh.\n\n"
            + status_message(db))
    return notify.deliver([{"name": r.name, "channel": r.channel, "address": r.address}], text)[0]


# -------------------------------------------------------------- quyen rieng tu
@router.get("/privacy/summary")
def privacy_summary(p: Principal = Depends(require_manager), db: Session = Depends(get_db)):
    from .bridge import BridgeCrossing
    oldest = db.query(VisitEvent.timestamp).order_by(VisitEvent.timestamp).first()
    return {
        "visit_events": db.query(VisitEvent).count(),
        "bridge_crossings": db.query(BridgeCrossing).count(),
        "occupancy_snapshots": db.query(OccupancySnapshot).count(),
        "system_events": db.query(SystemEvent).count(),
        "oldest_visit": iso(oldest[0]) if oldest else None,
        "face_images_stored": 0,
        "retention_min_days": RETENTION_MIN_DAYS,
    }


@router.post("/privacy/purge")
def purge(older_than_days: int, p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    if older_than_days < RETENTION_MIN_DAYS:
        raise HTTPException(status_code=400,
                            detail=f"Theo BRULE-09 phải giữ dữ liệu tối thiểu {RETENTION_MIN_DAYS} ngày (24 tháng).")
    from .bridge import BridgeCrossing
    cutoff = datetime.utcnow() - timedelta(days=older_than_days)
    n = 0
    n += db.query(VisitEvent).filter(VisitEvent.timestamp < cutoff).delete()
    n += db.query(OccupancySnapshot).filter(OccupancySnapshot.timestamp < cutoff).delete()
    n += db.query(BridgeCrossing).filter(BridgeCrossing.timestamp < cutoff).delete()
    log_audit(db, p.username, "Xóa dữ liệu cũ", f"{n} dòng cũ hơn {older_than_days} ngày")
    db.commit()
    return {"deleted_rows": n}


# ------------------------------------------------------------------ Telegram
class TelegramTokenIn(BaseModel):
    token: str


def load_telegram_token(db: Session):
    notify.set_db_token(get_config(db).telegram_token or "")


@router.get("/telegram/status")
def telegram_status(p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    load_telegram_token(db)
    if not notify.telegram_token():
        return {"connected": False, "source": "", "bot": None, "error": None}
    ok, res = notify.telegram_api("getMe")
    return {"connected": ok, "source": notify.token_source(),
            "bot": {"username": res.get("username"), "name": res.get("first_name")} if ok else None,
            "error": None if ok else res}


@router.put("/telegram/token")
def set_telegram_token(payload: TelegramTokenIn, p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    token = payload.token.strip()
    if ":" not in token:
        raise HTTPException(status_code=400, detail="Token không đúng dạng (vd 123456789:AAH...). Lấy token từ @BotFather.")
    ok, res = notify.telegram_api("getMe", token=token)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Telegram từ chối token: {res}")
    cfg = get_config(db)
    cfg.telegram_token = token
    log_audit(db, p.username, "Kết nối Telegram", f"bot @{res.get('username')}")
    db.commit()
    notify.set_db_token(token)
    return {"connected": True, "bot": {"username": res.get("username"), "name": res.get("first_name")}}


@router.delete("/telegram/token")
def clear_telegram_token(p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    cfg = get_config(db)
    cfg.telegram_token = None
    log_audit(db, p.username, "Ngắt kết nối Telegram", "")
    db.commit()
    notify.set_db_token("")
    return {"connected": bool(notify.telegram_token())}


@router.get("/telegram/chats")
def telegram_chats(p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    """Danh sach chat vua nhan tin cho bot (getUpdates) de lay chat_id ma khong can mo trinh duyet."""
    from .. import telegram_bot
    load_telegram_token(db)
    known = {r.address for r in db.query(Recipient).all()}
    if telegram_bot.running():   # bot dang doc tin nhan -> lay tu bo nho cua bot (getUpdates chi 1 noi doc duoc)
        return [dict(c, added=c["chat_id"] in known) for c in telegram_bot.SEEN.values()]
    ok, res = notify.telegram_api("getUpdates", limit=100)
    if not ok:
        raise HTTPException(status_code=400, detail=res)
    chats = {}
    for upd in res:
        msg = upd.get("message") or upd.get("channel_post") or upd.get("my_chat_member") or {}
        chat = msg.get("chat")
        if not chat:
            continue
        name = chat.get("title") or " ".join(x for x in (chat.get("first_name"), chat.get("last_name")) if x) \
            or chat.get("username") or str(chat["id"])
        chats[str(chat["id"])] = {"chat_id": str(chat["id"]), "name": name, "type": chat.get("type"),
                                  "username": chat.get("username"), "added": str(chat["id"]) in known}
    return list(chats.values())
