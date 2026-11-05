"""
backend/notify.py  —  F2.3 Gui thong bao cho nguoi truc / quan ly (FR-06, FR-13)
================================================================================
Camera chi ghi su kien (POST /system_events). Backend quyet dinh gui tin
nhan toi DANH SACH NGUOI NHAN trong CSDL (trang "Nguoi nhan canh bao").

- Kenh telegram: token bot dat o trang "Nguoi nhan canh bao" (luu CSDL) hoac bien
  moi truong TELEGRAM_BOT_TOKEN (uu tien bien moi truong); address = chat_id.
- Chua co nguoi nhan nao -> dung TELEGRAM_CHAT_ID (cach cu) neu co.
- Kenh zalo / sms / email: chua ho tro trong MVP (BRD Bang 27), chi ghi log.
- Gui trong luong rieng -> camera khong phai cho mang.
"""

import os
import threading
from typing import List

import requests

ENV_TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
_db_token = ""
NO_TOKEN = "Chưa kết nối bot Telegram (trang Người nhận cảnh báo → Kết nối Telegram)."


def set_db_token(token: str):
    global _db_token
    _db_token = (token or "").strip()


def telegram_token() -> str:
    return ENV_TELEGRAM_TOKEN or _db_token


def token_source() -> str:
    return "env" if ENV_TELEGRAM_TOKEN else ("db" if _db_token else "")


def telegram_api(method: str, token: str = None, **params):
    """Goi Telegram Bot API, tra ve (ok, du_lieu_hoac_loi)."""
    token = token or telegram_token()
    if not token:
        return False, NO_TOKEN
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=params,
                          timeout=10 + int(params.get("timeout", 0)))   # getUpdates cho toi `timeout` giay
        d = r.json()
    except (requests.RequestException, ValueError) as e:
        return False, f"Không kết nối được Telegram: {e}"
    if not d.get("ok"):
        return False, d.get("description", f"Telegram lỗi {r.status_code}")
    return True, d["result"]


WEB_URL = os.environ.get("SMARTCAU_WEB_URL", "").rstrip("/")   # vd http://192.168.1.10:8501 -> them nut mo web


def keyboard(buttons):
    """buttons: list cac hang, moi hang list (text, callback_data | url). Tra ve reply_markup hoac None."""
    if not buttons:
        return None
    rows = []
    for row in buttons:
        rows.append([{"text": t, ("url" if str(v).startswith("http") else "callback_data"): v} for t, v in row])
    return {"inline_keyboard": rows}


def _send_telegram(chat_id: str, text: str, buttons=None) -> str:
    """Gui tin dinh dang HTML (in dam, bieu tuong...). Loi dinh dang -> gui lai dang chu thuong."""
    params = {"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    markup = keyboard(buttons)
    if markup:
        params["reply_markup"] = markup
    ok, res = telegram_api("sendMessage", **params)
    if not ok and "parse" in str(res).lower():
        params.pop("parse_mode")
        ok, res = telegram_api("sendMessage", **params)
    return "ok" if ok else res


def deliver(recipients: List[dict], text: str, buttons=None) -> List[dict]:
    """Gui ngay (dong bo) toi danh sach {name, channel, address}. Tra ve ket qua tung nguoi."""
    targets = list(recipients)
    if not targets and TELEGRAM_CHAT_ID:
        targets = [{"name": "TELEGRAM_CHAT_ID", "channel": "telegram", "address": TELEGRAM_CHAT_ID}]
    results = []
    for r in targets:
        if r["channel"] == "telegram":
            status = _send_telegram(r["address"], text, buttons)
        else:
            status = f"Kênh {r['channel']} chưa hỗ trợ trong MVP."
        results.append({"name": r["name"], "channel": r["channel"], "status": status})
        if status != "ok":
            print(f"[notify] {r['name']}: {status}")
    return results


def deliver_async(recipients: List[dict], text: str, buttons=None):
    threading.Thread(target=deliver, args=(list(recipients), text, buttons), daemon=True).start()


def deliver_document(recipients: List[dict], filename: str, content: bytes, caption: str = "") -> List[dict]:
    """Gui tep (vd PDF bao cao ngay) qua Telegram sendDocument."""
    targets = [r for r in recipients if r["channel"] == "telegram"]
    if not targets and not recipients and TELEGRAM_CHAT_ID:
        targets = [{"name": "TELEGRAM_CHAT_ID", "channel": "telegram", "address": TELEGRAM_CHAT_ID}]
    results = []
    for r in targets:
        if not telegram_token():
            status = NO_TOKEN
        else:
            try:
                resp = requests.post(f"https://api.telegram.org/bot{telegram_token()}/sendDocument",
                                     data={"chat_id": r["address"], "caption": caption, "parse_mode": "HTML"},
                                     files={"document": (filename, content, "application/pdf")}, timeout=20)
                status = "ok" if resp.status_code == 200 else f"Telegram lỗi {resp.status_code}"
            except requests.RequestException as e:
                status = f"Không gửi được tệp: {e}"
        results.append({"name": r["name"], "channel": "telegram", "status": status})
    return results
