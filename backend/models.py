"""
backend/models.py  (MODULE M2 - Nen tang backend, phu trach: Minh)
--------------------------------------------------------------------
Cac bang CSDL LOI dung chung nhieu module. Bang rieng cua 1 module khai bao
ngay trong file router cua module do (vd bang ve tham quan nam trong
routers/tickets.py) de 3 nguoi khong cung sua 1 file -> tranh xung dot.

Cot moi them vao bang cu duoc tu dong bo sung khi khoi dong
(database.ensure_schema) nen file smartcau.db cu van dung duoc.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from .database import Base


class VisitEvent(Base):
    """F3.2 - 1 dong = nhan nhan khau hoc cua 1 luot khach VAO cau.
    Khong luu anh, khong luu dac trung khuon mat (BRULE-05, NFR-05).
    gender = None / age_range = "Khong xac dinh" khi do tin cay < 70% (BRULE-06).
    origin = "Trong nuoc" / "Nuoc ngoai" / None - UOC LUONG tu nhom khu vuc rong."""
    __tablename__ = "visit_events"
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    age = Column(Integer, nullable=True)
    age_range = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    camera_id = Column(Integer, nullable=True)


class OccupancySnapshot(Base):
    """F1.2 / F5.1 - so nguoi tren cau + muc canh bao, camera gui moi 2 giay."""
    __tablename__ = "occupancy_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    count = Column(Integer)
    status = Column(String)


class OccupancyState(Base):
    """F1.2 - CHI 1 dong (id=1): so nguoi dang tren cau thoi gian thuc."""
    __tablename__ = "occupancy_state"
    id = Column(Integer, primary_key=True)
    current_count = Column(Integer, default=0)


class SystemEvent(Base):
    """F2 - nhat ky su kien: WARNING, CRITICAL_ALERT, CRITICAL_CLEARED,
    GROUP_DETECTED, CAMERA_LOST, CAMERA_RESTORED, GATE_CLOSED, GATE_REOPENED."""
    __tablename__ = "system_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    event_type = Column(String, index=True)
    count = Column(Integer, nullable=True)
    message = Column(String, nullable=True)
    camera_id = Column(Integer, nullable=True)


class SystemConfig(Base):
    """F6.2 - CHI 1 dong (id=1): nguong canh bao + khung gio hoat dong (FR-13)."""
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True)
    alert_threshold = Column(Integer, default=20)
    open_time = Column(String, default="07:00")
    close_time = Column(String, default="21:30")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(String, nullable=True)
    telegram_token = Column(String, nullable=True)   # token bot Telegram (chi admin xem/sua)


class User(Base):
    """F6.1 - tai khoan dang nhap. role: admin | quan_ly | nguoi_truc (FR-12)."""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    full_name = Column(String, default="")
    password_hash = Column(String)
    role = Column(String, default="nguoi_truc")
    active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    token = Column(String, primary_key=True)
    user_id = Column(Integer, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)


class AuditLog(Base):
    """NFR-04 / BRULE-07 - moi thay doi cau hinh, tai khoan, nguoi nhan deu ghi lai."""
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    username = Column(String)
    action = Column(String)
    detail = Column(String, default="")


ROLES = {"admin": "Quản trị viên", "quan_ly": "Quản lý", "nguoi_truc": "Người trực"}


def get_state(db) -> OccupancyState:
    state = db.query(OccupancyState).filter(OccupancyState.id == 1).first()
    if state is None:
        state = OccupancyState(id=1, current_count=0)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def get_config(db) -> SystemConfig:
    cfg = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
    if cfg is None:
        cfg = SystemConfig(id=1, alert_threshold=20, open_time="07:00", close_time="21:30")
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    if cfg.open_time is None or cfg.close_time is None:
        cfg.open_time = cfg.open_time or "07:00"
        cfg.close_time = cfg.close_time or "21:30"
        db.commit()
    return cfg


def log_audit(db, username: str, action: str, detail: str = ""):
    db.add(AuditLog(username=username or "?", action=action, detail=detail))
