"""
telegram_alert.py
-------------------
Gui canh bao qua Telegram Bot - ban thay the DON GIAN HON NHIEU cho phan
"n8n + Zalo OA" trong ke hoach goc. Khong can Docker, khong can tai khoan
doanh nghiep Zalo OA, chi can 1 tai khoan Telegram ca nhan.

=== CACH TAO BOT TELEGRAM (lam 1 LAN, khoang 2-3 phut) ===

1. Mo app Telegram (dien thoai hoac web.telegram.org), tim kiem tai khoan
   "BotFather" (co dau tick xanh chinh chu).
2. Nhan tin nhan /newbot cho BotFather, lam theo huong dan dat ten bot.
3. BotFather se tra ve 1 dong dang:
       Use this token to access the HTTP API:
       123456789:ABCdefGhIJKlmNoPQRstuVwxyz
   -> Day la TELEGRAM_BOT_TOKEN cua ban, luu lai.
4. Tim bot vua tao (theo username no vua dat, vi du @SmartCauAI_bot),
   nhan Start hoac nhan mot tin nhan bat ky cho no (BUOC NAY BAT BUOC,
   neu khong bot khong gui duoc tin cho ban).
5. Mo trinh duyet, truy cap (thay TOKEN that vao):
       https://api.telegram.org/bot<TOKEN_CUA_BAN>/getUpdates
   Tim doan co dang "chat":{"id": XXXXXXXXX, ...} trong ket qua JSON
   -> So XXXXXXXXX do la TELEGRAM_CHAT_ID cua ban.

=== CACH DUNG ===

Set 2 bien moi truong nay TRUOC KHI chay script camera, vi du trong
Terminal (macOS/Linux):
    export TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
    export TELEGRAM_CHAT_ID="987654321"
    python3 webcam_tracking_demo.py

Neu KHONG set 2 bien nay, chuong trinh VAN CHAY BINH THUONG, chi la se
IN CANH BAO RA MAN HINH thay vi gui Telegram that (khong bi loi/crash) -
tien cho luc dang phat trien/test chua can canh bao that.

Test rieng file nay (sau khi da set 2 bien moi truong o tren):
    python3 telegram_alert.py
"""

import os
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# NANG CAP Phase 4 - "tin hieu buzzer": du an demo nay KHONG co phan cung
# coi/den bao that, nen ham duoi day la 1 CHO MOC (placeholder) de sau nay
# noi voi phan cung that (vd 1 relay/coi noi qua Raspberry Pi, ESP32...).
# Mac dinh chi in ra man hinh (kem ky tu chuong '\a' - mot so Terminal se
# phat tieng "beep" ngan). Neu set bien moi truong SMARTCAU_BUZZER_WEBHOOK
# (vd dia chi 1 thiet bi IoT trong mang noi bo nhan lenh qua HTTP), ham se
# THEM goi POST toi dia chi do (best-effort, khong lam crash chuong trinh
# neu thiet bi khong phan hoi).
BUZZER_WEBHOOK = os.environ.get("SMARTCAU_BUZZER_WEBHOOK", "")


def trigger_buzzer_signal(message: str = "QUA TAI") -> None:
    """Kich hoat "tin hieu buzzer" canh bao tai cho (local). Xem ghi chu
    o tren ve gioi han/huong mo rong phan cung that."""
    print(f"\a[BUZZER] {message}")
    if not BUZZER_WEBHOOK:
        return
    try:
        requests.post(BUZZER_WEBHOOK, json={"signal": "buzzer_on", "message": message}, timeout=2)
    except Exception as e:
        print(f"[BUZZER] Khong goi duoc webhook ({BUZZER_WEBHOOK}): {e}")


def send_telegram_alert(message: str) -> bool:
    """Gui 1 tin nhan canh bao qua Telegram. Tra ve True neu gui thanh cong."""
    if not TOKEN or not CHAT_ID:
        print(f"[Telegram - CHUA CAU HINH, chi in ra man hinh thay the] {message}")
        return False
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        resp = requests.post(url, json={"chat_id": CHAT_ID, "text": message}, timeout=5)
        if resp.status_code == 200:
            print(f"[Telegram] Da gui canh bao thanh cong.")
            return True
        print(f"[Telegram] Gui that bai (ma loi {resp.status_code}): {resp.text}")
        return False
    except Exception as e:
        print(f"[Telegram] Loi khi gui: {e}")
        return False


if __name__ == "__main__":
    ok = send_telegram_alert("Day la tin nhan TEST tu he thong SmartCau AI.")
    if ok:
        print("Test thanh cong - kiem tra Telegram cua ban.")
    else:
        print("Chua gui duoc - kiem tra lai TOKEN/CHAT_ID hoac xem huong dan o dau file nay.")
