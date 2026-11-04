"""
frontend/views/dong_bo_sheets.py  —  Tien ich: dong bo Google Sheets (ngoai BFD)
Phu trach: MINH.
"""

import os
import sys

import streamlit as st

from common import API_BASE, note, page_header

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools"))

page_header("Hệ thống · Chia sẻ dữ liệu", "Google Sheets", "Gửi lịch sử lượt khách và số liệu tổng hợp sang Google Sheets để chia sẻ báo cáo.")

sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "")
creds_path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")

if not sheet_id or not creds_path:
    st.info("Chưa cấu hình. Đặt 2 biến môi trường **GOOGLE_SHEETS_ID** và **GOOGLE_SHEETS_CREDENTIALS_FILE** "
            "trước khi chạy giao diện. Hướng dẫn tạo khóa Google Cloud nằm trong `tools/google_sheets_sync.py`.")
    st.stop()

with st.container(border=True):
    st.markdown(f"**Sheet:** [{sheet_id}](https://docs.google.com/spreadsheets/d/{sheet_id}/edit)")
    st.caption(f"Tệp khóa: {creds_path}")
    if st.button("Đồng bộ ngay", type="primary"):
        try:
            import google_sheets_sync
        except ImportError as e:
            st.error(f"Thiếu thư viện: {e}. Chạy: pip install gspread google-auth")
            st.stop()
        with st.spinner("Đang đồng bộ..."):
            try:
                res = google_sheets_sync.sync_all(api_base=API_BASE, sheet_id=sheet_id, creds_path=creds_path)
                st.success(f"Đồng bộ thành công lúc {res['last_sync']}: {res['visit_events_synced']} lượt khách.")
            except Exception as e:
                st.error(f"Đồng bộ thất bại: {e}")

note("Chỉ dữ liệu đếm và nhãn ước lượng được gửi đi, không có hình ảnh.")
