"""
backend/routers/alerts.py  —  MODULE M3 · F2 Dieu tiet qua tai
===============================================================
Chuc nang BFD: F2.1 - F2.4   (FR-04, FR-05, FR-06, FR-07)

Phan DA CHAY (Minh - chuyen nguyen tu api_server.py cu):
    POST /system_events    camera ghi su kien (canh bao Vang/Do, dong cong...)
    GET  /system_events    danh sach su kien gan nhat

Phan SKELETON - phu trach: HOAN (PB-08 xac nhan xu ly su co, F2.4):
    GET  /incidents                 danh sach su co (canh bao) + trang thai xu ly
    POST /incidents/{id}/ack        nguoi truc xac nhan "da xu ly" (<= 2 thao tac)

    TODO(Hoan, Sprint 4):
      1. Them bang IncidentAck ngay trong file nay (event_id, acked_by,
         acked_at, note) - KHONG sua backend/models.py.
      2. /incidents: ghep system_events voi IncidentAck de biet su co nao
         da xu ly, tinh "thoi gian xu ly" = acked_at - timestamp (KPI O4).
      3. Tu dong dong su co khi <= 15 nguoi lien tuc 15 giay (BRULE) - co
         the do camera gui event "GATE_REOPENED", chi can danh dau dong.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SystemEvent
from ..schemas import SystemEventIn
from ..security import require_api_key

router = APIRouter(tags=["F2 - Dieu tiet qua tai"])

ALERT_TYPES = ("WARNING", "CRITICAL_ALERT", "GATE_CLOSED", "GROUP_DETECTED", "CAMERA_LOST")


@router.post("/system_events", dependencies=[Depends(require_api_key)])
def create_system_event(event: SystemEventIn, db: Session = Depends(get_db)):
    row = SystemEvent(event_type=event.event_type, count=event.count, message=event.message)
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"saved": True, "id": row.id}


@router.get("/system_events")
def list_system_events(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(SystemEvent).order_by(SystemEvent.id.desc()).limit(limit).all()
    return [
        {"id": r.id, "timestamp": r.timestamp.isoformat(), "event_type": r.event_type,
         "count": r.count, "message": r.message}
        for r in rows
    ]


# ------------------------------------------------------------- SKELETON F2.4
@router.get("/incidents")
def list_incidents(limit: int = 50, db: Session = Depends(get_db)):
    """Doc su co THAT tu system_events; cac truong xu ly (acknowledged,
    acked_at, handle_seconds) tam thoi de trong cho den khi Hoan them bang
    IncidentAck. Cau truc JSON da chot trong docs/API_CONTRACT.md."""
    rows = (db.query(SystemEvent)
            .filter(SystemEvent.event_type.in_(ALERT_TYPES))
            .order_by(SystemEvent.id.desc()).limit(limit).all())
    return [
        {"id": r.id, "timestamp": r.timestamp.isoformat(), "event_type": r.event_type,
         "count": r.count, "message": r.message,
         "acknowledged": False, "acked_at": None, "acked_by": None, "handle_seconds": None,
         "mock_fields": ["acknowledged", "acked_at", "acked_by", "handle_seconds"]}
        for r in rows
    ]


@router.post("/incidents/{event_id}/ack")
def ack_incident(event_id: int, acked_by: str = "nguoi_truc", note: str = ""):
    return {"event_id": event_id, "acknowledged": True, "acked_by": acked_by,
            "note": note, "mock": True, "detail": "Chua luu that - F2.4 (PB-08)"}
