"""
frontend/views/cau_hinh.py
--------------------------
Phu trach: KHANH      Chuc nang: F6.2 Cau hinh nguong canh bao (FR-13) · PB-11
"""
# Ghi chu: Trang da chay. Viec cua Khanh: hien them muc Vang/Do suy ra tu nguong (15 / 20 nguoi theo BRULE).

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from common import (ADMIN_API_KEY, AGE_ORDER, API_BASE, GENDER_LABEL_VI, GENDER_VALUE_FROM_VI,
                    STATUS_META, _HAS_PLOTLY, api_get, api_put, page_header, render_metric,
                    render_status_metric)

if _HAS_PLOTLY:
    import plotly.express as px


def page_cau_hinh():
    page_header(
        "⚙️", "Giu nhip di san", "Cau hinh he thong",
        "Dieu chinh nguong canh bao suc chua de van hanh an toan, khong can sua ma nguon.",
    )

    if not ADMIN_API_KEY:
        st.warning(
            "Chua set ADMIN_API_KEY o may dang chay trang admin nay - backend dang CHO PHEP moi "
            "request sua cau hinh (khong khoa). Chi nen de vay khi dang phat trien/demo noi bo.",
            icon="⚠️",
        )

    cfg, err = api_get("/config")
    if err:
        st.error(err)
        return

    col_left, col_right = st.columns([1, 1.4])
    with col_left:
        with st.container(border=True):
            st.markdown("**Nguong canh bao hien tai**")
            st.markdown(
                f'<div class="custom-metric-value" style="font-size:2.6rem;">{cfg["alert_threshold"]} '
                f'<span class="custom-metric-sub">nguoi</span></div>',
                unsafe_allow_html=True,
            )
            st.caption(f"Cap nhat lan cuoi: {cfg.get('updated_at') or 'chua ro'}")

    with col_right:
        with st.container(border=True):
            st.markdown("**Doi nguong canh bao**")
            st.caption("Ap dung ngay lap tuc cho ca 2 camera (vao/ra) - khong can sua code hay restart.")
            new_threshold = st.number_input(
                "So nguoi toi da cho phep cung luc tren cau",
                min_value=1, max_value=1000, value=int(cfg["alert_threshold"]), step=1,
            )
            if st.button("\U0001F4BE Luu cau hinh"):
                result, err = api_put("/config", {"alert_threshold": int(new_threshold)})
                if err:
                    st.error(err)
                else:
                    st.success(f"Da cap nhat nguong canh bao: {result['alert_threshold']}")


page_cau_hinh()
