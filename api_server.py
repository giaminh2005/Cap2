"""
api_server.py
---------------
Backend API don gian: FastAPI + SQLAlchemy (ORM) + SQLite.

Day la ban "rut gon" cua kien truc PostgreSQL trong ke hoach goc - GIU
NGUYEN kien truc (API + ORM + database chuan hoa), chi doi PostgreSQL
(can cai dat server rieng) sang SQLite (chi la 1 file .db ngay trong thu
muc nay, khong can cai them phan mem database nao). Neu sau nay can
chuyen sang PostgreSQL that, chi can doi DATABASE_URL ben duoi, code con
lai giu nguyen (day la loi ich cua dung SQLAlchemy ORM).

BAN CAP NHAT NAY THEM: "so nguoi dang co mat" (occupancy) dung CHUNG cho
CA 2 CAMERA (vao/ra) - la 1 dong duy nhat trong bang occupancy_state, tu
dong +1 khi co nguoi VAO (POST /entry) va -1 khi co nguoi RA (POST /exit).
Day la "nguon su that" (source of truth) duy nhat ve so nguoi tren cau -
ca camera_in.py va camera_out.py deu doc/ghi vao day thay vi tu dem rieng,
nen 2 camera luon thay CUNG 1 con so.

Cai dat (chay tren MAY CUA BAN, moi truong build demo khong co mang):
    pip install fastapi uvicorn sqlalchemy

Chay (giu terminal nay MO SUOT qua trinh chay camera o (cac) terminal khac):
    uvicorn api_server:app --reload --port 8000

Sau khi chay, mo trinh duyet: http://127.0.0.1:8000/docs
-> FastAPI tu sinh giao dien de xem/test truc tiep cac API, rat tien khi
   bao cao/trinh bay cho giang vien xem "backend that".

=== NANG CAP (Phase 1, bug #7) - DUONG DAN DATABASE ===
Ban truoc dung duong dan TUONG DOI ("sqlite:///./smartcau.db"), nghia la
file .db duoc tao o THU MUC DANG CHAY LENH (CWD) - neu ban chay uvicorn
tu 1 thu muc khac (vd tu thu muc goc du an thay vi tu thu muc src/), file
.db se bi tao SAI CHO, gay nham lan/mat du lieu "ao". Sua: luon dung
duong dan TUYET DOI, tinh tu VI TRI THAT SU cua file api_server.py nay -
du ban chay uvicorn tu dau, file .db luon nam cung thu muc voi file nay.

=== NANG CAP (Phase 1, bug #8) - XAC THUC API (TUY CHON) ===
Mac dinh server VAN MO (khong can API key) de de chay demo/test nhanh.
Neu muon bat xac thuc don gian (1 API key dung chung), set bien moi
truong SMARTCAU_API_KEY TRUOC khi chay uvicorn:
    export SMARTCAU_API_KEY="mot-chuoi-bi-mat-tuy-chon"
    uvicorn api_server:app --reload --port 8000
Khi do, moi request GHI DU LIEU (POST) phai co header "X-API-Key" dung
gia tri nay, neu khong se bi tu choi (401). Cac script camera_in.py/
camera_out.py/webcam_tracking_demo.py se TU DONG gui header nay neu may
ban cung set CUNG bien moi truong SMARTCAU_API_KEY do (xem camera_in.py).
KHONG set bien nay o ca 2 phia (server va camera) -> mac dinh KHONG xac
thuc, phu hop demo/do an hoc phan trong mang noi bo.

=== NANG CAP (Google Sheets + Admin Web) - CAU HINH TU XA (/config) ===
Them bang SystemConfig (1 dong duy nhat) + endpoint GET/PUT /config de
trang Admin Web (xem admin_web/app.py) co the XEM/DOI nguong canh bao
(alert_threshold) TU XA, khong can sua code/restart camera. GET /config
la endpoint CONG KHAI (de camera_in.py/camera_out.py doc duoc ma khong
can key) - PUT /config (doi gia tri) moi can xac thuc, dung 1 bien
MOI/RIENG la ADMIN_API_KEY (KHAC voi SMARTCAU_API_KEY o tren - 1 key
danh cho "ghi du lieu camera", 1 key danh cho "admin doi cau hinh", tach
rieng de ban co the dua SMARTCAU_API_KEY cho nguoi van hanh camera ma
khong lo ho doi duoc nguong canh bao he thong):
    export ADMIN_API_KEY="mot-chuoi-bi-mat-khac-cho-admin"
Neu KHONG set ADMIN_API_KEY, PUT /config se TU DONG CHO PHEP moi request
(mac dinh demo) - PHAI set bien nay truoc khi dung that/trinh bay cong
khai cho nguoi ngoai nhom.

LUU Y (dev-only): neu ban da chay ban CU cua file nay truoc do, file
smartcau.db da duoc tao voi cau truc bang CU (thieu cot/bang moi). SQLite
KHONG tu dong cap nhat cau truc bang cu. Neu gap loi kieu "no such column"
hoac "no such table", chi can XOA file smartcau.db (nam cung thu muc voi
file nay) roi chay lai uvicorn - bang se duoc tao lai tu dau (mat du lieu
demo cu, khong sao vi day la du lieu demo).
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# --- Duong dan database TUYET DOI (xem giai thich o dau file) ---
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_THIS_DIR, "smartcau.db")
DATABASE_URL = f"sqlite:///{_DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()

# --- Xac thuc API (tuy chon - xem giai thich o dau file) ---
_API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
# --- Xac thuc rieng cho ADMIN (doi cau hinh qua /config - xem giai thich o dau file) ---
_ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Dependency cho cac endpoint GHI du lieu (camera). Neu SMARTCAU_API_KEY
    khong duoc set phia server, bo qua xac thuc hoan toan (mac dinh demo)."""
    if not _API_KEY:
        return
    if x_api_key != _API_KEY:
        raise HTTPException(status_code=401, detail="Thieu hoac sai X-API-Key.")


def require_admin(x_admin_key: Optional[str] = Header(default=None)):
    """Dependency RIENG cho endpoint PUT /config (admin doi cau hinh he
    thong). Neu ADMIN_API_KEY khong duoc set phia server, bo qua xac thuc
    hoan toan (mac dinh demo) - xem giai thich o dau file."""
    if not _ADMIN_API_KEY:
        return
    if x_admin_key != _ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Thieu hoac sai X-Admin-Key.")


class VisitEvent(Base):
    """1 dong = 1 HO SO NHAN KHAU HOC cua 1 luot khach MOI VAO cua (ghi tu
    camera VAO - camera_in.py / webcam_tracking_demo.py). Moi ID chi ghi 1
    lan (co cache o phia camera script), khong ghi lap lai moi frame.

    LUU Y: CO Y KHONG co cot "khu vuc/quoc tich" o bang nay (du lieu PER-
    FACE/ca nhan) - du lieu khu vuc (neu bat Phase 3) CHI duoc luu TONG
    HOP theo gio trong bang RegionStat ben duoi, khong gan cho tung ho so
    ca nhan - dung nguyen tac da thong nhat (xem region_mapping.py)."""
    __tablename__ = "visit_events"
    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    age = Column(Integer, nullable=True)
    age_range = Column(String, nullable=True)
    gender = Column(String, nullable=True)


class OccupancySnapshot(Base):
    """1 dong = 1 lan camera BAO CAO DINH KY so nguoi dang co mat (dung de
    ve bieu do lich su theo thoi gian - khac voi occupancy_state la con so
    THOI GIAN THUC hien tai)."""
    __tablename__ = "occupancy_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    count = Column(Integer)
    status = Column(String)


class OccupancyState(Base):
    """CHI 1 DONG DUY NHAT (id=1): so nguoi dang co mat tren cau THOI GIAN
    THUC, dung chung boi camera VAO (+1 moi luot) va camera RA (-1 moi
    luot). Day la diem "tu dong tru so luong khi khach ra" ma de bai yeu
    cau - khong can 2 camera nhan dien lai CUNG 1 nguoi, moi camera chi can
    bao cho server biet "co 1 nguoi VUA vao/ra" la du."""
    __tablename__ = "occupancy_state"
    id = Column(Integer, primary_key=True)
    current_count = Column(Integer, default=0)


class SystemEvent(Base):
    """NANG CAP Phase 4 - Nhat ky su kien he thong KIEM SOAT TU DONG: dong/
    mo cong, canh bao khan cap... Dung de xem lai lich su "cong da dong may
    lan, luc nao" khi phan tich/bao cao, khong lien quan ho so ca nhan nao.
    event_type vi du: "GATE_CLOSED", "GATE_REOPENED", "CRITICAL_ALERT"."""
    __tablename__ = "system_events"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String, index=True)
    count = Column(Integer, nullable=True)
    message = Column(String, nullable=True)


class RegionStat(Base):
    """NANG CAP Phase 3 - THONG KE TONG HOP theo GIO cho tinh nang "phan
    nhom khu vuc" (tuy chon, mac dinh TAT - xem region_mapping.py). CO Y
    THIET KE: bang nay KHONG co cot lien ket toi track_id/ho so ca nhan
    nao - chi la 1 BO DEM theo (ngay, gio, khu_vuc), dung nguyen tac "chi
    luu du lieu tong hop, khong luu per-face" da thong nhat."""
    __tablename__ = "region_stats"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)   # "YYYY-MM-DD"
    hour = Column(Integer, index=True)  # 0-23
    region = Column(String, index=True)
    count = Column(Integer, default=0)


class SystemConfig(Base):
    """NANG CAP (Google Sheets + Admin Web) - CHI 1 DONG DUY NHAT (id=1):
    cau hinh he thong co the doi TU XA qua trang Admin Web (xem
    admin_web/app.py, muc "Cau hinh") ma khong can sua code/restart
    camera. Hien tai chi co alert_threshold (nguong "canh bao" - tuong
    duong CameraThresholds.alert) - cac nguong warning/critical con lai
    duoc TU DONG suy ra ty le tuong ung qua CameraThresholds.from_critical()
    o crowd_counter.py de admin chi can chinh 1 so duy nhat."""
    __tablename__ = "system_config"
    id = Column(Integer, primary_key=True)
    alert_threshold = Column(Integer, default=20)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="SmartCau AI API", description="Backend luu du lieu tu camera AI Chua Cau (ban demo)")


def _get_state(db) -> OccupancyState:
    state = db.query(OccupancyState).filter(OccupancyState.id == 1).first()
    if state is None:
        state = OccupancyState(id=1, current_count=0)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _get_config(db) -> SystemConfig:
    cfg = db.query(SystemConfig).filter(SystemConfig.id == 1).first()
    if cfg is None:
        cfg = SystemConfig(id=1, alert_threshold=20)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


class VisitEventIn(BaseModel):
    track_id: Optional[int] = None
    age: Optional[int] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None


class OccupancyIn(BaseModel):
    count: int
    status: str


class SystemEventIn(BaseModel):
    event_type: str
    count: Optional[int] = None
    message: Optional[str] = None


class RegionStatIn(BaseModel):
    region: str


class ConfigIn(BaseModel):
    alert_threshold: int


@app.get("/health")
def health():
    return {"status": "ok", "api_key_required": bool(_API_KEY), "admin_key_required": bool(_ADMIN_API_KEY)}


@app.post("/entry", dependencies=[Depends(require_api_key)])
def person_entry(event: VisitEventIn):
    """Goi khi CAMERA VAO phat hien 1 nguoi MOI: luu ho so nhan khau hoc
    (neu co) VA +1 vao so nguoi dang co mat tren cau."""
    db = SessionLocal()
    try:
        row = VisitEvent(
            track_id=event.track_id,
            age=event.age,
            age_range=event.age_range,
            gender=event.gender,
        )
        db.add(row)

        state = _get_state(db)
        state.current_count += 1
        db.commit()
        db.refresh(row)
        db.refresh(state)
        return {"saved": True, "id": row.id, "current_count": state.current_count}
    finally:
        db.close()


@app.post("/exit", dependencies=[Depends(require_api_key)])
def person_exit():
    """Goi khi CAMERA RA phat hien 1 nguoi MOI roi khoi cau: -1 vao so
    nguoi dang co mat tren cau (khong am duoi 0, phong truong hop le mat
    frame/loi dem)."""
    db = SessionLocal()
    try:
        state = _get_state(db)
        state.current_count = max(0, state.current_count - 1)
        db.commit()
        db.refresh(state)
        return {"current_count": state.current_count}
    finally:
        db.close()


# Giu lai 2 endpoint cu (/visit_events, /occupancy) de tuong thich nguoc
# voi webcam_tracking_demo.py (ban 1-camera don gian) - tuong duong /entry
# nhung KHONG cong don vao occupancy_state (vi ban 1 camera tu quan ly so
# dem cua rieng no bang thuat toan tracking, khong dua vao vao/ra).
@app.post("/visit_events", dependencies=[Depends(require_api_key)])
def create_visit_event(event: VisitEventIn):
    db = SessionLocal()
    try:
        row = VisitEvent(
            track_id=event.track_id, age=event.age,
            age_range=event.age_range, gender=event.gender,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"saved": True, "id": row.id}
    finally:
        db.close()


@app.post("/occupancy", dependencies=[Depends(require_api_key)])
def create_occupancy(snap: OccupancyIn):
    db = SessionLocal()
    try:
        row = OccupancySnapshot(count=snap.count, status=snap.status)
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"saved": True, "id": row.id}
    finally:
        db.close()


@app.post("/system_events", dependencies=[Depends(require_api_key)])
def create_system_event(event: SystemEventIn):
    """NANG CAP Phase 4: ghi lai 1 su kien he thong (vd dong/mo cong, canh
    bao khan). Camera script chi nen goi 1 LAN cho moi lan DOI TRANG THAI
    (vd luc cong CHUYEN TU mo SANG dong), khong goi lap lai moi frame."""
    db = SessionLocal()
    try:
        row = SystemEvent(event_type=event.event_type, count=event.count, message=event.message)
        db.add(row)
        db.commit()
        db.refresh(row)
        return {"saved": True, "id": row.id}
    finally:
        db.close()


@app.get("/system_events")
def list_system_events(limit: int = 50):
    db = SessionLocal()
    try:
        rows = db.query(SystemEvent).order_by(SystemEvent.id.desc()).limit(limit).all()
        return [
            {"id": r.id, "timestamp": r.timestamp.isoformat(), "event_type": r.event_type,
             "count": r.count, "message": r.message}
            for r in rows
        ]
    finally:
        db.close()


@app.post("/region_stats", dependencies=[Depends(require_api_key)])
def bump_region_stat(stat: RegionStatIn):
    """NANG CAP Phase 3 (tuy chon, mac dinh TAT phia camera - xem
    demographics_engine.py): +1 vao BO DEM tong hop (ngay, gio, khu_vuc)
    hien tai. KHONG nhan/luu track_id hay bat ky thong tin ca nhan nao -
    dung nguyen tac "chi luu du lieu tong hop" da thong nhat."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        date_str = now.strftime("%Y-%m-%d")
        row = (
            db.query(RegionStat)
            .filter(RegionStat.date == date_str, RegionStat.hour == now.hour, RegionStat.region == stat.region)
            .first()
        )
        if row is None:
            row = RegionStat(date=date_str, hour=now.hour, region=stat.region, count=0)
            db.add(row)
        row.count += 1
        db.commit()
        db.refresh(row)
        return {"saved": True, "date": row.date, "hour": row.hour, "region": row.region, "count": row.count}
    finally:
        db.close()


@app.get("/stats/region")
def region_stats():
    db = SessionLocal()
    try:
        rows = db.query(RegionStat).all()
        return [{"date": r.date, "hour": r.hour, "region": r.region, "count": r.count} for r in rows]
    finally:
        db.close()


@app.get("/stats/occupancy")
def occupancy_stats():
    """So nguoi dang co mat THOI GIAN THUC - camera_in.py va camera_out.py
    goi lien tuc de hien thi CUNG 1 con so tren ca 2 man hinh."""
    db = SessionLocal()
    try:
        state = _get_state(db)
        return {"current_count": state.current_count}
    finally:
        db.close()


@app.get("/stats/current")
def current_stats():
    """Tong hop nhanh: dung cho dashboard/kiem tra du lieu da ghi nhan chua."""
    db = SessionLocal()
    try:
        state = _get_state(db)
        latest_snapshot = db.query(OccupancySnapshot).order_by(OccupancySnapshot.id.desc()).first()
        total_visitors = db.query(VisitEvent).count()

        genders = {}
        ages = []
        for row in db.query(VisitEvent).all():
            if row.gender:
                genders[row.gender] = genders.get(row.gender, 0) + 1
            if row.age is not None:
                ages.append(row.age)

        return {
            "current_count": state.current_count,
            "current_status": latest_snapshot.status if latest_snapshot else "OK",
            "total_visitors_logged": total_visitors,
            "gender_breakdown": genders,
            "average_age": round(sum(ages) / len(ages), 1) if ages else None,
        }
    finally:
        db.close()


@app.get("/visit_events")
def list_visit_events(limit: int = 50, gender: Optional[str] = None, age_range: Optional[str] = None):
    """Danh sach HO SO NHAN KHAU HOC da ghi nhan - dung de xem/xuat du
    lieu phuc vu marketing/bao cao. NANG CAP (Admin Web): them 2 tham so
    loc tuy chon gender/age_range (dung boi trang "Lich su luot khach")."""
    db = SessionLocal()
    try:
        query = db.query(VisitEvent)
        if gender:
            query = query.filter(VisitEvent.gender == gender)
        if age_range:
            query = query.filter(VisitEvent.age_range == age_range)
        rows = query.order_by(VisitEvent.id.desc()).limit(limit).all()
        return [
            {"id": r.id, "track_id": r.track_id, "timestamp": r.timestamp.isoformat(),
             "age": r.age, "age_range": r.age_range, "gender": r.gender}
            for r in rows
        ]
    finally:
        db.close()


@app.get("/config")
def get_config():
    """NANG CAP (Admin Web): xem cau hinh he thong hien tai. Endpoint CONG
    KHAI (khong can key) de camera_in.py/camera_out.py doc duoc moi khi
    khoi dong/dinh ky ma khong can quan ly them 1 key nua."""
    db = SessionLocal()
    try:
        cfg = _get_config(db)
        return {
            "alert_threshold": cfg.alert_threshold,
            "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
        }
    finally:
        db.close()


@app.put("/config", dependencies=[Depends(require_admin)])
def update_config(payload: ConfigIn):
    """NANG CAP (Admin Web): doi nguong canh bao TU XA. Can header
    'X-Admin-Key' khop voi ADMIN_API_KEY neu bien nay duoc set phia
    server (xem giai thich o dau file)."""
    if payload.alert_threshold < 1:
        raise HTTPException(status_code=400, detail="alert_threshold phai >= 1.")
    db = SessionLocal()
    try:
        cfg = _get_config(db)
        cfg.alert_threshold = payload.alert_threshold
        db.commit()
        db.refresh(cfg)
        return {
            "alert_threshold": cfg.alert_threshold,
            "updated_at": cfg.updated_at.isoformat() if cfg.updated_at else None,
        }
    finally:
        db.close()
