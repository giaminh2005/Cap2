"""
backend/routers/accounts.py  —  MODULE M2 · F6.1 Quan ly tai khoan
===================================================================
Phu trach: MINH.   Yeu cau: FR-12, NFR-04, BRULE-07

    POST /auth/login             {username, password} -> {token, username, full_name, role, ...}
    POST /auth/logout
    GET  /auth/me
    POST /auth/change_password   {old_password, new_password}
    GET  /users                  (admin)
    POST /users                  (admin) {username, full_name, password, role}
    PUT  /users/{id}             (admin) {full_name?, role?, active?, password?}
    GET  /audit                  (admin, quan_ly) nhat ky thay doi

Lan dau khoi dong (chua co tai khoan nao) tu tao: admin / admin123 va BAT
BUOC doi mat khau sau lan dang nhap dau.
"""

import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ROLES, AuditLog, AuthToken, User, log_audit
from ..security import Principal, hash_password, require_admin, require_manager, require_staff, verify_password
from ..timeutil import iso

router = APIRouter(tags=["F6.1 - Tai khoan"])
TOKEN_HOURS = 12


class LoginIn(BaseModel):
    username: str
    password: str


class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str


class UserIn(BaseModel):
    username: str
    full_name: str = ""
    password: str
    role: str = "nguoi_truc"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    active: Optional[bool] = None
    password: Optional[str] = None


def ensure_default_admin(db: Session):
    if db.query(User).count() == 0:
        db.add(User(username="admin", full_name="Quản trị viên", password_hash=hash_password("admin123"),
                    role="admin", must_change_password=True))
        db.commit()
        print("[accounts] Da tao tai khoan mac dinh admin / admin123 - hay doi mat khau ngay.")


def _user_json(u: User) -> dict:
    return {"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role,
            "role_label": ROLES.get(u.role, u.role), "active": u.active,
            "must_change_password": u.must_change_password,
            "created_at": iso(u.created_at), "last_login": iso(u.last_login)}


def _check_password(pw: str):
    if len(pw) < 6:
        raise HTTPException(status_code=400, detail="Mật khẩu phải có ít nhất 6 ký tự.")


@router.post("/auth/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    ensure_default_admin(db)
    u = db.query(User).filter(User.username == payload.username.strip()).first()
    if u is None or not verify_password(payload.password, u.password_hash):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu.")
    if not u.active:
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa. Liên hệ quản trị viên.")
    token = secrets.token_urlsafe(32)
    now = datetime.utcnow()
    db.add(AuthToken(token=token, user_id=u.id, created_at=now, expires_at=now + timedelta(hours=TOKEN_HOURS)))
    db.query(AuthToken).filter(AuthToken.expires_at < now).delete()
    u.last_login = now
    db.commit()
    return {"token": token, **_user_json(u)}


@router.post("/auth/logout")
def logout(authorization: Optional[str] = Header(default=None), db: Session = Depends(get_db)):
    if authorization and authorization.lower().startswith("bearer "):
        db.query(AuthToken).filter(AuthToken.token == authorization.split(" ", 1)[1].strip()).delete()
        db.commit()
    return {"ok": True}


@router.get("/auth/me")
def me(p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == p.user_id).first() if p.user_id else None
    return _user_json(u) if u else {"username": p.username, "full_name": p.full_name, "role": p.role}


@router.post("/auth/change_password")
def change_password(payload: ChangePasswordIn, p: Principal = Depends(require_staff),
                    db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == p.user_id).first()
    if u is None or not verify_password(payload.old_password, u.password_hash):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng.")
    _check_password(payload.new_password)
    if payload.new_password == payload.old_password:
        raise HTTPException(status_code=400, detail="Mật khẩu mới phải khác mật khẩu cũ.")
    u.password_hash = hash_password(payload.new_password)
    u.must_change_password = False
    log_audit(db, u.username, "Đổi mật khẩu", "")
    db.commit()
    return {"ok": True}


@router.get("/users")
def list_users(p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    return [_user_json(u) for u in db.query(User).order_by(User.id).all()]


@router.post("/users")
def create_user(payload: UserIn, p: Principal = Depends(require_admin), db: Session = Depends(get_db)):
    username = payload.username.strip()
    if not username or " " in username:
        raise HTTPException(status_code=400, detail="Tên đăng nhập không được để trống hoặc chứa dấu cách.")
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại.")
    _check_password(payload.password)
    u = User(username=username, full_name=payload.full_name.strip(), role=payload.role,
             password_hash=hash_password(payload.password), must_change_password=True)
    db.add(u)
    log_audit(db, p.username, "Tạo tài khoản", f"{username} ({ROLES[payload.role]})")
    db.commit()
    db.refresh(u)
    return _user_json(u)


@router.put("/users/{user_id}")
def update_user(user_id: int, payload: UserUpdate, p: Principal = Depends(require_admin),
                db: Session = Depends(get_db)):
    u = db.query(User).filter(User.id == user_id).first()
    if u is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản.")
    changes = []
    removing_admin = (payload.role is not None and payload.role != "admin") or payload.active is False
    if u.role == "admin" and removing_admin:
        others = db.query(User).filter(User.role == "admin", User.active.is_(True), User.id != u.id).count()
        if others == 0:
            raise HTTPException(status_code=400, detail="Phải còn ít nhất 1 quản trị viên đang hoạt động.")
    if payload.full_name is not None:
        u.full_name = payload.full_name.strip()
        changes.append("họ tên")
    if payload.role is not None:
        if payload.role not in ROLES:
            raise HTTPException(status_code=400, detail="Vai trò không hợp lệ.")
        changes.append(f"vai trò → {ROLES[payload.role]}")
        u.role = payload.role
    if payload.active is not None:
        u.active = payload.active
        changes.append("mở khóa" if payload.active else "khóa")
        if not payload.active:
            db.query(AuthToken).filter(AuthToken.user_id == u.id).delete()
    if payload.password:
        _check_password(payload.password)
        u.password_hash = hash_password(payload.password)
        u.must_change_password = True
        changes.append("đặt lại mật khẩu")
    log_audit(db, p.username, "Sửa tài khoản", f"{u.username}: {', '.join(changes) or 'không đổi'}")
    db.commit()
    db.refresh(u)
    return _user_json(u)


@router.get("/audit")
def audit_log(limit: int = 200, p: Principal = Depends(require_manager), db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
    return [{"id": r.id, "timestamp": iso(r.timestamp), "username": r.username,
             "action": r.action, "detail": r.detail} for r in rows]
