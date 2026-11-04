"""
backend/security.py  (MODULE M2 - Nen tang backend, phu trach: Minh)
----------------------------------------------------------------------
Xac thuc (NFR-04, FR-12):

- Camera GHI du lieu: header X-API-Key = SMARTCAU_API_KEY (khong set -> mo,
  dung cho mang noi bo).
- Nguoi dung web: dang nhap /auth/login -> token, gui lai qua header
  "Authorization: Bearer <token>". Mat khau luu dang bam PBKDF2-SHA256.
- 3 vai tro: admin (Quan tri vien), quan_ly (Quan ly), nguoi_truc (Nguoi truc).
- X-Admin-Key = ADMIN_API_KEY (neu set) duoc coi nhu admin - dung cho script.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuthToken, User

API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
_ITER = 200_000


def hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), _ITER).hex()
    return f"pbkdf2_sha256${_ITER}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iters, salt, digest = stored.split("$")
        calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode(), int(iters)).hex()
        return hmac.compare_digest(calc, digest)
    except (ValueError, AttributeError):
        return False


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Endpoint GHI du lieu tu camera."""
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Thiếu hoặc sai X-API-Key.")


class Principal:
    def __init__(self, username: str, role: str, full_name: str = "", user_id: Optional[int] = None):
        self.username, self.role, self.full_name, self.user_id = username, role, full_name, user_id

    @property
    def display(self) -> str:
        return self.full_name or self.username


def current_principal(authorization: Optional[str] = Header(default=None),
                      x_admin_key: Optional[str] = Header(default=None),
                      db: Session = Depends(get_db)) -> Principal:
    if ADMIN_API_KEY and x_admin_key == ADMIN_API_KEY:
        return Principal("api-admin", "admin", "Script quản trị")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Bạn cần đăng nhập.")
    token = authorization.split(" ", 1)[1].strip()
    tok = db.query(AuthToken).filter(AuthToken.token == token).first()
    if tok is None or tok.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Phiên đăng nhập đã hết hạn, vui lòng đăng nhập lại.")
    user = db.query(User).filter(User.id == tok.user_id).first()
    if user is None or not user.active:
        raise HTTPException(status_code=401, detail="Tài khoản đã bị khóa.")
    return Principal(user.username, user.role, user.full_name, user.id)


def require_roles(*roles):
    """Dependency: chi cho cac vai tro trong `roles` (rong = moi nguoi da dang nhap)."""
    def _dep(p: Principal = Depends(current_principal)) -> Principal:
        if roles and p.role not in roles:
            raise HTTPException(status_code=403, detail="Vai trò của bạn không được dùng chức năng này.")
        return p
    return _dep


require_admin = require_roles("admin")
require_staff = require_roles()                      # moi tai khoan da dang nhap
require_manager = require_roles("admin", "quan_ly")
