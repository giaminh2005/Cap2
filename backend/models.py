"""
backend/models.py  (MODULE M2 - Nen tang backend, phu trach: Minh)
--------------------------------------------------------------------
Cac bang CSDL LOI da co tu api_server.py cu (giu nguyen ten bang/cot de
du lieu cu van doc duoc). Day la nguon cho ERD/Data Dictionary Sprint 3.

QUY UOC LAM VIEC SONG SONG: bang MOI cua module nao thi khai bao NGAY
TRONG file router cua module do (vd bang ve tham quan nam trong
routers/tickets.py) de 3 nguoi khong cung sua 1 file nay -> khong bi
xung dot (merge conflict) tren GitHub. File nay chi Minh sua.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from .database import Base


class VisitEvent(Base):
    """F1.3 + F3.2 - 1 dong = 1 ho so nhan khau hoc cua 1 luot khach VAO.
    Khong luu anh khuon mat, khong luu khu vuc/quoc tich theo ca nhan
    (US-12 / PB-06: cam ket quyen rieng tu)."""
    __tablename__ = "visit_events"
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    age = Column(Integer, nullable=True)
    age_range = Column(String, nullable=True)
    gender = Column(String, nullable=True)


class OccupancySnapshot(Base):
    """F1.2 / F5.1 - so nguoi tren cau duoc camera bao cao dinh ky (de ve
    bieu do lich su)."""
    __tablename__ = "occupancy_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    count = Column(Integer)
    status = Column(String)


class OccupancyState(Base):
    """F1.2 - CHI 1 dong (id=1): so nguoi dang tren cau thoi gian thuc,
    camera VAO +1, camera RA -1."""
    __tablename__ = "occupancy_state"
    id = Column(Integer, primary_key=True)
    current_count = Column(Integer, default=0)


class SystemEvent(Base):
    """F2 - nhat ky su kien: canh bao Vang/Do, dong/mo cong, doan khach lon...
    event_type vi du: "WARNING", "CRITICAL_ALERT", "GATE_CLOSED",
    "GATE_REOPENED", "GROUP_DETECTED", "CAMERA_LOST"."""
    __tablename__ = "system_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String, index=True)
    count = Column(Integer, nullable=True)
    message = Column(String, nullable=True)


class RegionStat(Base):
    """F3.3 - thong ke TONG HOP theo (ngay, gio, khu vuc), khong gan ca nhan."""
    __tablename__ = "region_stats"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)   # "YYYY-MM-DD"
    hour = Column(Integer, index=True)  # 0-23
    region = Column(String, index=True)
    count = Column(Integer, default=0)


class SystemConfig(Base):
    """F6.2 - CHI 1 dong (id=1): nguong canh bao doi tu xa qua trang admin."""
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True)
    alert_threshold = Column(Integer, default=20)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
        cfg = SystemConfig(id=1, alert_threshold=20)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg
