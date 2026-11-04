"""
frontend/views/dong_bo_sheets.py
--------------------------------
Phu trach: MINH      Chuc nang: Tien ich - dong bo Google Sheets (ngoai BFD)
"""
# Ghi chu: Trang da chay, tuy chon.

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from common import (ADMIN_API_KEY, AGE_ORDER, API_BASE, GENDER_LABEL_VI, GENDER_VALUE_FROM_VI,
                    STATUS_META, _HAS_PLOTLY, api_get, api_put, page_header, render_metric,
                    render_status_metric)

if _HAS_PLOTLY:
    import plotly.express as px


def page_dong_bo_sheets():
    page_header(
        "☁️", "Ket noi du lieu", "Dong bo Google Sheets",
        "Gui du lieu van hanh sang Google Sheets de chia se bao cao voi giang vien va ban quan ly.",
    )
    st.markdown(
        "Tinh nang TUY CHON - gui du lieu lich su luot khach va so lieu occupancy tu database "
        "sang 1 Google Sheet that, de chia se/bao cao ma khong can mo truc tiep trang admin nay. "
        "Xem huong dan cau hinh Google Cloud chi tiet trong file `tools/google_sheets_sync.py`."
    )

    sheet_id = os.environ.get("GOOGLE_SHEETS_ID", "")
    creds_path = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_FILE", "")

    with st.container(border=True):
        if not sheet_id or not creds_path:
            st.info(
                "Chua cau hinh GOOGLE_SHEETS_ID / GOOGLE_SHEETS_CREDENTIALS_FILE "
                "(2 bien moi truong) - tinh nang nay se khong hoat dong cho den khi ban cau hinh.",
                icon="ℹ️",
            )
            return

        col1, col2 = st.columns(2)
        col1.markdown(f"**Sheet ID:** `{sheet_id}`")
        col2.markdown(f"[\U0001F517 Mo Google Sheet](https://docs.google.com/spreadsheets/d/{sheet_id}/edit)")
        st.caption(f"File key: {creds_path}")

        if st.button("\U0001F504 Dong bo ngay"):
            try:
                import google_sheets_sync  # noqa: import tai thoi diem dung
            except ImportError as e:
                st.error(
                    f"Chua cai du thu vien cho Google Sheets: {e}. "
                    "Chay: pip install gspread google-auth"
                )
                return

            with st.spinner("Dang dong bo..."):
                try:
                    result = google_sheets_sync.sync_all(
                        api_base=API_BASE, sheet_id=sheet_id, creds_path=creds_path,
                    )
                    st.success(
                        f"Dong bo thanh cong luc {result['last_sync']}: "
                        f"{result['visit_events_synced']} luot khach."
                    )
                except Exception as e:
                    st.error(f"Dong bo that bai: {e}")


page_dong_bo_sheets()
