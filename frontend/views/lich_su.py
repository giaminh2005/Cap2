"""
frontend/views/lich_su.py
-------------------------
Phu trach: KHANH      Chuc nang: F3.2 / F5.1 Tra cuu ho so luot khach (FR-09, FR-10)
"""
# Ghi chu: Trang da chay - chi can kiem tra lai khi UAT.

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from common import (ADMIN_API_KEY, AGE_ORDER, API_BASE, GENDER_LABEL_VI, GENDER_VALUE_FROM_VI,
                    STATUS_META, _HAS_PLOTLY, api_get, api_put, page_header, render_metric,
                    render_status_metric)

if _HAS_PLOTLY:
    import plotly.express as px


def page_lich_su():
    page_header(
        "\U0001F3EE", "Dau chan du khach", "Lich su luot khach",
        "Tra cuu, loc va xuat du lieu nhan khau hoc da ghi nhan qua camera AI.",
    )

    with st.container(border=True):
        col_a, col_b, col_c = st.columns(3)
        limit = col_a.number_input("So dong toi da", min_value=10, max_value=5000, value=200, step=10)
        gender_filter_vi = col_b.selectbox("Loc theo gioi tinh", ["(Tat ca)", "Nam", "Nu"])
        age_filter = col_c.text_input("Loc theo khoang tuoi (vd 25-34, de trong = tat ca)")

        params = {"limit": int(limit)}
        if gender_filter_vi != "(Tat ca)":
            params["gender"] = GENDER_VALUE_FROM_VI.get(gender_filter_vi, gender_filter_vi)
        if age_filter.strip():
            params["age_range"] = age_filter.strip()

    data, err = api_get("/visit_events", params=params)
    if err:
        st.error(err)
        return

    if not data:
        st.info("Chua co luot khach nao duoc ghi nhan (hoac khong co ket qua khop bo loc).")
        return

    df = pd.DataFrame(data)
    df_display = df.copy()
    if "gender" in df_display.columns:
        df_display["gender"] = df_display["gender"].map(lambda g: GENDER_LABEL_VI.get(g, g))
    if "timestamp" in df_display.columns:
        try:
            df_display["timestamp"] = pd.to_datetime(df_display["timestamp"]).dt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            pass  # neu dinh dang thoi gian la gi khac thuong, giu nguyen chuoi goc thay vi lam vo trang
    df_display = df_display.rename(columns={
        "id": "ID", "track_id": "Ma theo doi", "timestamp": "Thoi gian",
        "age": "Tuoi (uoc tinh)", "age_range": "Khoang tuoi", "gender": "Gioi tinh",
    })

    filter_label = "Khong co"
    if gender_filter_vi != "(Tat ca)" or age_filter.strip():
        filter_label = gender_filter_vi if gender_filter_vi != "(Tat ca)" else ""
        if age_filter.strip():
            filter_label = f"{filter_label}, {age_filter.strip()}" if filter_label else age_filter.strip()

    st.markdown(
        f"""
        <div class="hoian-kpi-row" style="grid-template-columns: repeat(2, 1fr); margin-bottom:16px;">
            {render_metric("\U0001F4CA So dong dang hien thi", f"{len(df):,}".replace(",", "."))}
            {render_metric("\U0001F50D Bo loc dang ap dung", filter_label)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.dataframe(df_display, use_container_width=True, hide_index=True, height=440)

    csv_bytes = df_display.to_csv(index=False).encode("utf-8-sig")  # utf-8-sig de Excel mo tieng Viet khong bi loi font
    st.download_button(
        "⬇️ Xuat CSV",
        data=csv_bytes,
        file_name=f"luot_khach_chua_cau_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )


page_lich_su()
