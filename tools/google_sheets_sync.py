"""
google_sheets_sync.py
------------------------
Dong bo du lieu tu backend (backend/) sang 1 Google Sheet THAT, de
chia se/bao cao cho giang vien hoac ban quan ly ma khong can mo trang
admin web - ho chi can mo link Google Sheet binh thuong.

Co the goi tu:
  - Nut "Dong bo ngay" trong frontend/app.py (trang Dong bo Google Sheets).
  - Dong lenh (standalone), xem main() o cuoi file - tien neu muon dat
    lich dong bo tu dong (vd cron moi 15 phut).

=== CACH TAO SERVICE ACCOUNT (lam 1 LAN, khoang 5-7 phut) ===

1. Mo https://console.cloud.google.com/ , tao 1 project moi (hoac dung
   project co san).
2. Vao "APIs & Services" > "Library", bat 2 API:
     - Google Sheets API
     - Google Drive API
3. Vao "APIs & Services" > "Credentials" > "Create Credentials" >
   "Service account". Dat ten bat ky (vd "smartcau-sheets-sync"), bo qua
   cac buoc phan quyen (khong bat buoc).
4. Sau khi tao xong, vao service account vua tao > tab "Keys" > "Add Key"
   > "Create new key" > chon JSON > tai file .json ve may.
   -> Day la CREDS_PATH se dung ben duoi - GIU KIN file nay (khong commit
      len Git/public), vi ai co file nay cung dang nhap duoc service
      account.
5. Mo file .json vua tai, tim dong "client_email" (dang
   "ten@ten-project.iam.gserviceaccount.com").
6. Tao 1 Google Sheet moi (hoac dung sheet co san), nhan nut "Share"
   (Chia se), dan CHINH XAC email o buoc 5 vao, cap quyen "Editor".
   (BUOC NAY BAT BUOC - thieu buoc nay se bi loi "permission denied"
   khi dong bo).
7. Lay SHEET_ID tu URL cua Google Sheet, vi du:
       https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit
       SHEET_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz" (doan giua "/d/" va "/edit")

=== CACH DUNG ===

Set 2 bien moi truong (hoac nhap truc tiep trong trang admin web):
    export GOOGLE_SHEETS_ID="1AbCdEfGhIjKlMnOpQrStUvWxYz"
    export GOOGLE_SHEETS_CREDENTIALS_FILE="/duong/dan/toi/service_account.json"

Chay thu (dong bo 1 lan, can backend/ dang chay o terminal khac):
    python3 google_sheets_sync.py

Cai dat (chay tren may ban, co Internet):
    pip install gspread google-auth requests

LUU Y VE DU LIEU: moi lan dong bo se GHI DE TOAN BO 2 trang tinh
("LuotKhach", "TongQuan") bang du lieu moi nhat lay tu API (khong dong bo
kieu "chi them dong moi") - don gian va an toan hon cho quy mo du lieu PoC
(vai tram - vai nghin dong). Neu sau nay du lieu lon hon nhieu (hang chuc
nghin dong/ngay), nen doi sang dong bo "chi them dong moi" (dua vao id da
dong bo lan truoc) de tranh ghi lai toan bo moi lan - ngoai pham vi PoC
hoc ky nay.
"""

import argparse
import os
from datetime import datetime

import requests

try:
    import gspread
    from google.oauth2.service_account import Credentials
    _DEPS_OK = True
except ImportError as e:
    _DEPS_OK = False
    _IMPORT_ERR = e

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

VISIT_EVENTS_HEADER = ["ID", "Ma theo doi", "Thoi gian (UTC)", "Tuoi", "Nhom tuoi", "Gioi tinh", "Nguon khach", "Camera"]


def _get_or_create_worksheet(spreadsheet, title: str, rows: int = 1000, cols: int = 10):
    try:
        return spreadsheet.worksheet(title)
    except Exception:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def _authorize(creds_path: str):
    if not _DEPS_OK:
        raise RuntimeError(
            "Thieu thu vien gspread/google-auth. Chay:\n"
            "    pip install gspread google-auth\n"
            f"(Loi import goc: {_IMPORT_ERR})"
        )
    if not os.path.isfile(creds_path):
        raise FileNotFoundError(
            f"Khong tim thay file credentials: {creds_path}\n"
            "Xem huong dan tao service account o dau file nay."
        )
    creds = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(creds)


def sync_all(api_base: str, sheet_id: str, creds_path: str, limit: int = 5000) -> dict:
    """Ham chinh: dong bo CA 2 trang tinh (LuotKhach + TongQuan) tu du
    lieu hien co trong backend (goi qua API, khong doc truc tiep file
    .db - de dam bao luon la du lieu da qua logic/validate cua
    backend/). Tra ve 1 dict tom tat ket qua (dung de hien thi
    thong bao thanh cong tren frontend/app.py)."""
    gc = _authorize(creds_path)
    spreadsheet = gc.open_by_key(sheet_id)

    # --- 1. Trang "LuotKhach": toan bo ho so nhan khau hoc da ghi nhan ---
    resp = requests.get(f"{api_base}/visit_events", params={"limit": limit}, timeout=10)
    resp.raise_for_status()
    visit_events = resp.json()

    ws_events = _get_or_create_worksheet(spreadsheet, "LuotKhach")
    ws_events.clear()
    rows = [VISIT_EVENTS_HEADER] + [
        [e["id"], e["track_id"], e["timestamp"], e["age"], e["age_range"], e["gender"],
         e.get("origin"), e.get("camera_id")]
        for e in visit_events
    ]
    ws_events.update(rows)

    # --- 2. Trang "TongQuan": so lieu tong hop thoi diem dong bo ---
    resp2 = requests.get(f"{api_base}/stats/current", timeout=10)
    resp2.raise_for_status()
    stats = resp2.json()

    sync_time = datetime.now().isoformat(timespec="seconds")
    summary_rows = [
        ["Chi so", "Gia tri"],
        ["Thoi diem dong bo", sync_time],
        ["Dang co mat tren cau", stats["current_count"]],
        ["Trang thai", stats["current_status"]],
        ["Luot vao cau hom nay", stats["entries_today"]],
        ["Luot qua mat tien hom nay", stats["facade_today"]],
        ["Ho so khach hom nay", stats["profiles_today"]],
        ["Su co dang mo", stats["open_incidents"]],
    ]
    for gender, count in (stats.get("gender_today") or {}).items():
        summary_rows.append([f"So luot - {gender}", count])

    ws_summary = _get_or_create_worksheet(spreadsheet, "TongQuan")
    ws_summary.clear()
    ws_summary.update(summary_rows)

    return {
        "visit_events_synced": len(visit_events),
        "last_sync": sync_time,
        "sheet_url": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit",
    }


def main():
    parser = argparse.ArgumentParser(description="Dong bo du lieu SmartCau AI sang Google Sheets.")
    parser.add_argument("--api", default=os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000"))
    parser.add_argument("--sheet-id", default=os.environ.get("GOOGLE_SHEETS_ID", ""))
    parser.add_argument("--creds", default=os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", ""))
    args = parser.parse_args()

    if not args.sheet_id or not args.creds:
        print("Thieu --sheet-id/--creds (hoac bien moi truong GOOGLE_SHEETS_ID/GOOGLE_SHEETS_CREDENTIALS_FILE).")
        print("Xem huong dan cau hinh o dau file nay.")
        return

    result = sync_all(api_base=args.api, sheet_id=args.sheet_id, creds_path=args.creds)
    print(f"Da dong bo {result['visit_events_synced']} luot khach luc {result['last_sync']}.")
    print(f"Xem tai: {result['sheet_url']}")


if __name__ == "__main__":
    main()
