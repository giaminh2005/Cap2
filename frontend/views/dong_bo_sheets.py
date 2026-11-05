"""
frontend/views/dong_bo_sheets.py  —  Tien ich: dong bo Google Sheets (ngoai BFD)
Phu trach: MINH.
Cau hinh ngay tren trang (khong can bien moi truong): Sheet ID + tep khoa
service account luu o thu muc config/ (da .gitignore, KHONG dua len GitHub).
Bien moi truong GOOGLE_SHEETS_ID / GOOGLE_SHEETS_CREDENTIALS_FILE van duoc uu tien neu co.
"""

import json
import os
import re
import sys

import streamlit as st

from common import API_BASE, alert_box, badge, page_header, section

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
CONF_DIR = os.path.join(ROOT, "config")
CONF_FILE = os.path.join(CONF_DIR, "google_sheets.json")
KEY_FILE = os.path.join(CONF_DIR, "google_service_account.json")

page_header("Hệ thống · Chia sẻ dữ liệu", "Google Sheets",
            "Gửi lịch sử lượt khách và số liệu tổng hợp sang một bảng tính Google để chia sẻ với giảng viên và đơn vị quản lý.")


def load_conf():
    sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    creds = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")
    if not sheet_id and os.path.exists(CONF_FILE):
        sheet_id = json.load(open(CONF_FILE, encoding="utf-8")).get("sheet_id", "")
    if not creds and os.path.exists(KEY_FILE):
        creds = KEY_FILE
    email = ""
    if creds and os.path.exists(creds):
        try:
            email = json.load(open(creds, encoding="utf-8")).get("client_email", "")
        except (ValueError, OSError):
            pass
    return sheet_id, creds, email


def parse_sheet_id(text: str) -> str:
    m = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", text or "")
    return m.group(1) if m else (text or "").strip()


sheet_id, creds, email = load_conf()

section("Cấu hình")
with st.form("gs"):
    link = st.text_input("Đường link hoặc ID của Google Sheet", value=sheet_id,
                         placeholder="https://docs.google.com/spreadsheets/d/1AbC.../edit")
    key = st.file_uploader("Tệp khóa service account (.json)", type=["json"])
    if st.form_submit_button("Lưu cấu hình", type="primary"):
        os.makedirs(CONF_DIR, exist_ok=True)
        sid = parse_sheet_id(link)
        if not sid:
            st.error("Hãy dán đường link Google Sheet.")
        else:
            if key is not None:
                try:
                    data = json.loads(key.getvalue().decode("utf-8"))
                    if data.get("type") != "service_account" or "client_email" not in data:
                        raise ValueError("không phải tệp khóa service account")
                    with open(KEY_FILE, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                except ValueError as e:
                    st.error(f"Tệp khóa không hợp lệ: {e}")
                    st.stop()
            old = json.load(open(CONF_FILE, encoding="utf-8")) if os.path.exists(CONF_FILE) else {}
            with open(CONF_FILE, "w", encoding="utf-8") as f:
                json.dump({**old, "sheet_id": sid}, f)
            st.success("Đã lưu cấu hình.")
            st.rerun()

if email:
    st.markdown(f"Email service account: `{email}`  " + badge("Nhớ chia sẻ Sheet cho email này, quyền Editor", "warn"),
                unsafe_allow_html=True)

section("Đồng bộ")
_auto_conf = json.load(open(CONF_FILE, encoding="utf-8")) if os.path.exists(CONF_FILE) else {}
auto = st.toggle("Tự đồng bộ mỗi tối sau khi lập báo cáo ngày", value=_auto_conf.get("auto", True), key="gs_auto")
if auto != _auto_conf.get("auto", True):
    os.makedirs(CONF_DIR, exist_ok=True)
    _auto_conf["auto"] = auto
    with open(CONF_FILE, "w", encoding="utf-8") as f:
        json.dump(_auto_conf, f)
    st.toast("Đã bật tự đồng bộ." if auto else "Đã tắt tự đồng bộ.", icon=":material/schedule:")
if not (sheet_id and creds):
    alert_box("Chưa đủ cấu hình: cần cả đường link Google Sheet và tệp khóa.", "info")
    st.stop()
st.markdown(f"Bảng tính: [mở Google Sheet](https://docs.google.com/spreadsheets/d/{sheet_id}/edit)")
if st.button("Đồng bộ ngay", type="primary"):
    try:
        import google_sheets_sync
    except ImportError as e:
        st.error(f"Thiếu thư viện: {e}. Chạy: pip install gspread google-auth")
        st.stop()
    with st.spinner("Đang đồng bộ..."):
        try:
            res = google_sheets_sync.sync_all(api_base=API_BASE, sheet_id=sheet_id, creds_path=creds)
            st.success(f"Đồng bộ thành công lúc {res['last_sync']}: {res['visit_events_synced']} lượt khách. "
                       "Trang tính LuotKhach và TongQuan đã được cập nhật.")
        except Exception as e:
            msg = str(e)
            if "PERMISSION_DENIED" in msg or "403" in msg:
                msg = f"Không có quyền ghi. Hãy chia sẻ Sheet cho {email} với quyền Editor. ({e})"
            elif "SERVICE_DISABLED" in msg or "has not been used" in msg:
                msg = f"Chưa bật Google Sheets API hoặc Google Drive API trong dự án Google Cloud. ({e})"
            st.error(f"Đồng bộ thất bại: {msg}")
