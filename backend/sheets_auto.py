"""
backend/sheets_auto.py  —  Tu dong dong bo Google Sheets moi toi (sau bao cao ngay)
===================================================================================
Dung chung cau hinh voi trang web "Google Sheets" (thu muc config/ o goc du an):
    config/google_sheets.json            {"sheet_id": "...", "auto": true}
    config/google_service_account.json   tep khoa service account
Bien moi truong GOOGLE_SHEETS_ID / GOOGLE_SHEETS_CREDENTIALS_FILE duoc uu tien neu co.
Backend goi lai API cua chinh no (SMARTCAU_SELF_URL, mac dinh http://127.0.0.1:8000).
"""

import json
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CONF_DIR = os.path.join(ROOT, "config")
CONF_FILE = os.path.join(CONF_DIR, "google_sheets.json")
KEY_FILE = os.path.join(CONF_DIR, "google_service_account.json")
SELF_URL = os.environ.get("SMARTCAU_SELF_URL", "http://127.0.0.1:8000")


def load_conf() -> dict:
    conf = {}
    if os.path.exists(CONF_FILE):
        try:
            conf = json.load(open(CONF_FILE, encoding="utf-8"))
        except (OSError, ValueError):
            conf = {}
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID") or conf.get("sheet_id", "")
    creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE") or (KEY_FILE if os.path.exists(KEY_FILE) else "")
    return {"sheet_id": sheet_id, "creds": creds, "auto": conf.get("auto", True),
            "configured": bool(sheet_id and creds and os.path.exists(creds))}


def sync_now() -> str:
    """Dong bo 1 lan. Tra ve cau tom tat ket qua (khong nem loi)."""
    c = load_conf()
    if not c["configured"]:
        return "chưa cấu hình"
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import google_sheets_sync
        res = google_sheets_sync.sync_all(api_base=SELF_URL, sheet_id=c["sheet_id"], creds_path=c["creds"])
        return f"đã đồng bộ {res.get('visit_events_synced', 0)} lượt khách"
    except ImportError as e:
        return f"thiếu thư viện ({e}); chạy: pip install gspread google-auth"
    except Exception as e:   # mang, quyen chia se, API chua bat...
        return f"lỗi: {str(e)[:160]}"


def auto_sync_after_report() -> str:
    c = load_conf()
    if not (c["configured"] and c["auto"]):
        return ""
    return sync_now()
