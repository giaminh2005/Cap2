"""
backend/notify.py  —  F2.3 Gui thong bao cho nguoi truc / quan ly (FR-06, FR-13)
================================================================================
Camera chi ghi su kien (POST /system_events). Backend quyet dinh gui tin
nhan toi DANH SACH NGUOI NHAN trong CSDL (trang "Nguoi nhan canh bao").

- Kenh telegram: can bien moi truong TELEGRAM_BOT_TOKEN; address = chat_id.
- Chua co nguoi nhan nao -> dung TELEGRAM_CHAT_ID (cach cu) neu co.
- Kenh zalo / sms / email: chua ho tro trong MVP (BRD Bang 27), chi ghi log.
- Gui trong luong rieng -> camera khong phai cho mang.
"""

import os
import threading
from typing import List

import requests

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")


def _send_telegram(chat_id: str, text: str) -> str:
    if not TELEGRAM_BOT_TOKEN:
        return "Chưa cấu hình TELEGRAM_BOT_TOKEN trên máy chạy backend."
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                          json={"chat_id": chat_id, "text": text}, timeout=8)
        if r.status_code == 200:
            return "ok"
        return f"Telegram trả về lỗi {r.status_code}: {r.text[:120]}"
    except requests.RequestException as e:
        return f"Không gửi được Telegram: {e}"


def deliver(recipients: List[dict], text: str) -> List[dict]:
    """Gui ngay (dong bo) toi danh sach {name, channel, address}. Tra ve ket qua tung nguoi."""
    targets = list(recipients)
    if not targets and TELEGRAM_CHAT_ID:
        targets = [{"name": "TELEGRAM_CHAT_ID", "channel": "telegram", "address": TELEGRAM_CHAT_ID}]
    results = []
    for r in targets:
        if r["channel"] == "telegram":
            status = _send_telegram(r["address"], text)
        else:
            status = f"Kênh {r['channel']} chưa hỗ trợ trong MVP."
        results.append({"name": r["name"], "channel": r["channel"], "status": status})
        if status != "ok":
            print(f"[notify] {r['name']}: {status}")
    return results


def deliver_async(recipients: List[dict], text: str):
    threading.Thread(target=deliver, args=(list(recipients), text), daemon=True).start()
