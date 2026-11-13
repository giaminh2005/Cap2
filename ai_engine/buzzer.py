"""
buzzer.py  —  Tin hieu canh bao tai cho khi QUA TAI (canh bao Do)
==================================================================
Camera chan cau 1 goi trigger_buzzer_signal() ngay khi vao muc Do: keu "bip" o may camera
va, neu dat bien SMARTCAU_BUZZER_WEBHOOK, goi URL do (vd module ESP32 / relay bat coi, den).
Tin nhan Telegram do backend gui (backend/notify.py), khong gui o day.
"""

import os

import requests

BUZZER_WEBHOOK = os.environ.get("SMARTCAU_BUZZER_WEBHOOK", "")


def trigger_buzzer_signal(message: str = "QUA TAI") -> None:
    print(f"\a[BUZZER] {message}")
    if not BUZZER_WEBHOOK:
        return
    try:
        requests.post(BUZZER_WEBHOOK, json={"signal": "buzzer_on", "message": message}, timeout=2)
    except requests.RequestException as e:
        print(f"[BUZZER] Khong goi duoc webhook ({BUZZER_WEBHOOK}): {e}")
