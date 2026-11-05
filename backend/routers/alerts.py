"""
backend/routers/alerts.py  —  MODULE M3 · F2 Dieu tiet qua tai
===============================================================
Chuc nang BFD: F2.1 - F2.4   (FR-04, FR-05, FR-06, FR-07, BRULE-04)
Phu trach: MINH (F2.1-F2.3), HOAN (F2.4).

    POST /system_events            camera ghi su kien -> backend gui thong bao + mo/dong su co
    GET  /system_events            nhat ky su kien
    GET  /incidents?status=        su co Do (open | closed | all)
    POST /incidents/{id}/ack       nguoi truc xac nhan "da xu ly" (1 cham, AC-04.1)
    POST /incidents/{id}/close     dong su co bang tay (vd camera mat tin hieu)
    POST /incidents/{id}/false_alarm   danh dau / bo danh dau "bao sai" (KPI O5)

Vong doi su co (FR-07):
    CRITICAL_ALERT (lan dau)  -> MO su co moi, gui tin Do
    CRITICAL_ALERT (nhac lai) -> cap nhat so nguoi cao nhat, gui tin nhac (camera da gioi han 3 phut)
    CRITICAL_CLEARED          -> TU DONG DONG su co (<= 15 nguoi lien tuc 15 giay),
                                 gui bao cao su co cho quan ly (AC-04.2)
"""

from datetime import datetime
from html import escape
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import Session

from .. import messages, notify
from ..database import Base, get_db
from ..models import SystemEvent, get_config, log_audit
from ..schemas import SystemEventIn
from ..security import Principal, require_api_key, require_staff
from ..timeutil import iso, to_local
from .admin import active_recipients, is_open_now

router = APIRouter(tags=["F2 - Dieu tiet qua tai"])

EVENT_LABELS = {
    "WARNING": "Cảnh báo Vàng",
    "CRITICAL_ALERT": "Cảnh báo Đỏ",
    "CRITICAL_CLEARED": "Hết quá tải",
    "GROUP_DETECTED": "Đoàn khách lớn",
    "CAMERA_LOST": "Mất tín hiệu camera",
    "CAMERA_RESTORED": "Camera hoạt động lại",
    "GATE_CLOSED": "Tạm dừng cho khách lên",
    "GATE_REOPENED": "Cho khách lên lại",
    "MORNING_BRIEF": "Bản tin đầu ngày",
    "TICKET_REMINDER": "Nhắc nhập số cuống vé",
}
ALWAYS_NOTIFY = {"CRITICAL_ALERT", "CAMERA_LOST"}          # gui ca ngoai gio mo cua
NOTIFY_IN_HOURS = {"WARNING", "GROUP_DETECTED", "CAMERA_RESTORED"}


class Incident(Base):
    """F2.4 - 1 dong = 1 su co qua tai (canh bao Do)."""
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    opened_at = Column(DateTime, default=datetime.utcnow, index=True)
    peak_count = Column(Integer, default=0)
    alert_count = Column(Integer, default=1)
    acked_at = Column(DateTime, nullable=True)
    acked_by = Column(String, nullable=True)
    note = Column(String, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    close_reason = Column(String, nullable=True)   # "auto" | "manual"
    closed_by = Column(String, nullable=True)
    false_alarm = Column(Boolean, default=False)   # KPI O5 / NFR-02: nguoi truc danh dau bao sai
    false_note = Column(String, nullable=True)
    false_by = Column(String, nullable=True)


def _open_incident(db) -> Optional[Incident]:
    return db.query(Incident).filter(Incident.closed_at.is_(None)).order_by(Incident.id.desc()).first()


def _secs(a, b):
    return int((b - a).total_seconds()) if a and b else None


def _incident_json(i: Incident) -> dict:
    return {"id": i.id, "opened_at": iso(i.opened_at), "peak_count": i.peak_count,
            "alert_count": i.alert_count, "acknowledged": i.acked_at is not None,
            "acked_at": iso(i.acked_at), "acked_by": i.acked_by, "note": i.note,
            "closed_at": iso(i.closed_at), "close_reason": i.close_reason, "closed_by": i.closed_by,
            "status": "open" if i.closed_at is None else "closed",
            "false_alarm": bool(i.false_alarm), "false_note": i.false_note, "false_by": i.false_by,
            "handle_seconds": _secs(i.opened_at, i.acked_at),
            "duration_seconds": _secs(i.opened_at, i.closed_at or datetime.utcnow())}


def buttons(incident: Optional[Incident] = None):
    """Nut bam duoi tin Telegram (bot xu ly, xem backend/telegram_bot.py)."""
    rows = []
    if incident is not None and incident.closed_at is None and incident.acked_at is None:
        rows.append([("✅ Đã xử lý", f"ack:{incident.id}")])
    rows.append([("📍 Tình hình", "status"), ("📊 Hôm nay", "today")])
    if notify.WEB_URL:
        rows.append([("🖥 Mở trang quản lý", notify.WEB_URL)])
    return rows


def _close(db, inc: Incident, reason: str, by: str):
    inc.closed_at = datetime.utcnow()
    inc.close_reason, inc.closed_by = reason, by
    try:
        return messages.incident_closed_message(db, inc, reason, by)
    except Exception as e:  # tin dep loi -> van gui tin ngan
        print(f"[alerts] Không lập được tin đóng sự cố: {e}")
        dur = _secs(inc.opened_at, inc.closed_at) or 0
        return (f"✅ SỰ CỐ #{inc.id} ĐÃ ĐÓNG. Bắt đầu {to_local(inc.opened_at):%H:%M %d/%m}, "
                f"kéo dài {dur // 60} phút {dur % 60} giây, cao nhất {inc.peak_count} người.")


@router.post("/system_events", dependencies=[Depends(require_api_key)])
def create_system_event(event: SystemEventIn, db: Session = Depends(get_db)):
    row = SystemEvent(event_type=event.event_type, count=event.count, message=event.message,
                      camera_id=event.camera_id)
    db.add(row)
    text = escape(event.message or f"[SmartCau AI] {EVENT_LABELS.get(event.event_type, event.event_type)}")
    incident_id = None
    inc = None

    if event.event_type == "CRITICAL_ALERT":
        inc = _open_incident(db)
        if inc is None:
            inc = Incident(peak_count=event.count or 0)
            db.add(inc)
        else:
            inc.alert_count += 1
            inc.peak_count = max(inc.peak_count or 0, event.count or 0)
        db.flush()
        incident_id = inc.id
        text = f"{text} (Sự cố #{inc.id})"
    elif event.event_type == "CRITICAL_CLEARED":
        inc = _open_incident(db)
        if inc is not None:
            text = _close(db, inc, "auto", "hệ thống")
            incident_id = inc.id
    db.commit()
    if event.event_type != "CRITICAL_CLEARED":
        try:   # tin dinh dang dep kem tinh hinh hien tai; loi thi dung tin goc cua camera
            text = messages.event_message(db, event.event_type, event.count, event.camera_id, inc) or text
        except Exception as e:
            print(f"[alerts] Không lập được tin {event.event_type}: {e}")

    send = event.event_type in ALWAYS_NOTIFY or (
        event.event_type in NOTIFY_IN_HOURS and is_open_now(get_config(db)))
    if event.event_type == "CRITICAL_CLEARED" and incident_id is not None:
        send = True
    if send:
        notify.deliver_async(active_recipients(db), text, buttons(inc if event.event_type == "CRITICAL_ALERT" else None))
    return {"saved": True, "id": row.id, "incident_id": incident_id, "notified": send}


@router.get("/system_events")
def list_system_events(limit: int = 50, event_type: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(SystemEvent)
    if event_type:
        q = q.filter(SystemEvent.event_type == event_type)
    rows = q.order_by(SystemEvent.id.desc()).limit(limit).all()
    return [{"id": r.id, "timestamp": iso(r.timestamp), "event_type": r.event_type,
             "label": EVENT_LABELS.get(r.event_type, r.event_type), "count": r.count,
             "message": r.message, "camera_id": r.camera_id} for r in rows]


@router.get("/incidents")
def list_incidents(status: str = "all", limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(Incident)
    if status == "open":
        q = q.filter(Incident.closed_at.is_(None))
    elif status == "closed":
        q = q.filter(Incident.closed_at.isnot(None))
    return [_incident_json(i) for i in q.order_by(Incident.id.desc()).limit(limit).all()]


class AckIn(BaseModel):
    note: str = ""


@router.post("/incidents/{incident_id}/ack")
def ack_incident(incident_id: int, payload: AckIn = AckIn(), p: Principal = Depends(require_staff),
                 db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if inc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự cố.")
    acknowledge(db, inc, p.display, payload.note, via="web")
    db.refresh(inc)
    return _incident_json(inc)


def acknowledge(db, inc: Incident, who: str, note: str = "", via: str = "web") -> bool:
    """Nguoi truc nhan xu ly su co (tu web hoac nut Telegram). Lan dau -> bao cho moi nguoi nhan."""
    first = inc.acked_at is None
    if first:
        inc.acked_at = datetime.utcnow()
        inc.acked_by = who
    if note:
        inc.note = note
    db.commit()
    if first and inc.closed_at is None:
        secs = _secs(inc.opened_at, inc.acked_at)
        notify.deliver_async(active_recipients(db),
                             f"🙋 <b>{escape(who)}</b> đã nhận xử lý <b>sự cố #{inc.id}</b> "
                             f"sau {secs // 60} phút {secs % 60} giây"
                             f"{' (qua Telegram)' if via == 'telegram' else ''}.\n"
                             "Các bạn khác không cần ra điều tiết thêm.", buttons())
    return first


@router.post("/incidents/{incident_id}/close")
def close_incident(incident_id: int, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if inc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự cố.")
    if inc.closed_at is None:
        text = _close(db, inc, "manual", p.display)
        db.commit()
        notify.deliver_async(active_recipients(db), text, buttons())
    db.refresh(inc)
    return _incident_json(inc)


class FalseAlarmIn(BaseModel):
    is_false: bool = True
    note: str = ""


@router.post("/incidents/{incident_id}/false_alarm")
def mark_false_alarm(incident_id: int, payload: FalseAlarmIn = FalseAlarmIn(), p: Principal = Depends(require_staff),
                     db: Session = Depends(get_db)):
    """KPI O5: ty le canh bao sai = so su co bi danh dau bao sai / tong su co."""
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if inc is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy sự cố.")
    inc.false_alarm = payload.is_false
    inc.false_note = payload.note if payload.is_false else None
    inc.false_by = p.display if payload.is_false else None
    log_audit(db, p.username, "Đánh dấu báo sai" if payload.is_false else "Bỏ đánh dấu báo sai",
              f"Sự cố #{inc.id}" + (f": {payload.note}" if payload.note else ""))
    db.commit()
    db.refresh(inc)
    return _incident_json(inc)
