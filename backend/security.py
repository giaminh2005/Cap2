"""
backend/security.py  (MODULE M2 - Nen tang backend, phu trach: Minh)
----------------------------------------------------------------------
Xac thuc API don gian, giu NGUYEN logic cua api_server.py cu:

- SMARTCAU_API_KEY : key cho camera GHI du lieu (header X-API-Key)
- ADMIN_API_KEY    : key cho admin DOI cau hinh (header X-Admin-Key)

Khong set bien moi truong nao -> khong khoa (mac dinh demo noi bo).
"""

import os
from typing import Optional

from fastapi import Header, HTTPException

API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")


def require_api_key(x_api_key: Optional[str] = Header(default=None)):
    """Dung cho endpoint GHI du lieu tu camera."""
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Thieu hoac sai X-API-Key.")


def require_admin(x_admin_key: Optional[str] = Header(default=None)):
    """Dung cho endpoint admin doi cau hinh he thong."""
    if not ADMIN_API_KEY:
        return
    if x_admin_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Thieu hoac sai X-Admin-Key.")
