"""
frontend/views/tong_quan.py
---------------------------
Phu trach: KHANH      Chuc nang: F5.1 Hien thi so lieu truc tiep (FR-10) · PB-05
"""
# Ghi chu: Trang da chay. Viec cua Khanh: them bieu do so nguoi theo thoi gian (GET /stats/occupancy/history),
#   them 5 su co gan nhat (GET /incidents), tu dong lam moi moi 5 giay.

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from common import (ADMIN_API_KEY, AGE_ORDER, API_BASE, GENDER_LABEL_VI, GENDER_VALUE_FROM_VI,
                    STATUS_META, _HAS_PLOTLY, api_get, api_put, page_header, render_metric,
                    render_status_metric)

if _HAS_PLOTLY:
    import plotly.express as px


def page_tong_quan():
    page_header(
        "\U0001F3EF", "Di san Hoi An", "Tong quan van hanh",
        "Giam sat suc chua Chua Cau theo thoi gian thuc de bao ve di tich va an toan du khach.",
    )

    stats, err1 = api_get("/stats/current")
    cfg, err2 = api_get("/config")
    if err1 or err2:
        st.error(err1 or err2)
        return

    threshold = cfg["alert_threshold"]
    count = stats["current_count"]
    ratio = count / threshold if threshold else 0
    status = stats.get("current_status", "OK")
    meta = STATUS_META.get(status, STATUS_META["OK"])
    avg_age = stats["average_age"]
    avg_age_display = f"{avg_age}" if avg_age is not None else "N/A"
    total_display = f'{stats["total_visitors_logged"]:,}'.replace(",", ".")

    st.markdown(
        f"""
        <div class="hoian-kpi-row">
            {render_metric("\U0001F465 Dang co mat", count, f"/ {threshold} nguoi")}
            {render_status_metric("✨ Trang thai", status)}
            {render_metric("\U0001F4DC Tong luot da ghi nhan", total_display)}
            {render_metric("\U0001F382 Tuoi trung binh", avg_age_display)}
        </div>
        """,
        unsafe_allow_html=True,
    )

    bar_color = {
        "ok": "var(--hoian-moss)", "warn": "var(--hoian-ochre)",
        "alert": "var(--hoian-red)", "critical": "var(--hoian-red-dark)",
    }[meta["badge"]]
    width_pct = min(100, round(ratio * 100))
    st.markdown(
        f"""
        <div class="hoian-progress-wrap">
            <div class="hoian-progress-top">
                <span>Suc chua di tich</span><span>{count}/{threshold} ({width_pct}%)</span>
            </div>
            <div class="hoian-progress-track">
                <div class="hoian-progress-fill" style="width:{width_pct}%; background:{bar_color};"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if status in ("ALERT", "CRITICAL"):
        st.error(f"{meta['icon']} {meta['label']}: {count}/{threshold} nguoi dang tren cau.")
    elif status == "WARNING":
        st.warning(f"{meta['icon']} {meta['label']}: {count}/{threshold} nguoi dang tren cau.")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        with st.container(border=True):
            st.markdown("**\U0001F6BB Phan bo gioi tinh** (cac luot da ghi nhan)")
            genders = stats.get("gender_breakdown") or {}
            if genders:
                df_gender = pd.DataFrame({
                    "Gioi tinh": [GENDER_LABEL_VI.get(k, k) for k in genders.keys()],
                    "So luot": list(genders.values()),
                })
                if _HAS_PLOTLY:
                    fig = px.pie(
                        df_gender, names="Gioi tinh", values="So luot", hole=0.5,
                        color="Gioi tinh",
                        color_discrete_map={"Nam": "#344B3B", "Nu": "#7A3028"},
                    )
                    fig.update_traces(textinfo="label+percent", textfont_size=13)
                    fig.update_layout(
                        showlegend=False, margin=dict(t=10, b=10, l=10, r=10), height=280,
                        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Be Vietnam Pro", color="#563B2D"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.bar_chart(df_gender.set_index("Gioi tinh"))
            else:
                st.info("Chua co du lieu gioi tinh nao duoc ghi nhan.")

    with col_chart2:
        with st.container(border=True):
            st.markdown("**\U0001F382 Phan bo do tuoi** (cac luot da ghi nhan)")
            events, err = api_get("/visit_events", params={"limit": 2000})
            if err:
                st.caption("Khong tai duoc du lieu do tuoi.")
            else:
                ages = [e.get("age_range") or "Khong ro" for e in (events or [])]
                if ages:
                    counts = pd.Series(ages).value_counts()
                    ordered = [a for a in AGE_ORDER if a in counts.index]
                    ordered += [a for a in counts.index if a not in AGE_ORDER]
                    df_age = pd.DataFrame({"Khoang tuoi": ordered, "So luot": [counts[a] for a in ordered]})
                    if _HAS_PLOTLY:
                        fig2 = px.bar(df_age, x="Khoang tuoi", y="So luot", color_discrete_sequence=["#B77A2B"])
                        fig2.update_layout(
                            margin=dict(t=10, b=10, l=10, r=10), height=280,
                            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(family="Be Vietnam Pro", color="#563B2D"),
                            xaxis_title=None, yaxis_title=None,
                        )
                        st.plotly_chart(fig2, use_container_width=True)
                    else:
                        st.bar_chart(df_age.set_index("Khoang tuoi"))
                else:
                    st.info("Chua co du lieu do tuoi nao duoc ghi nhan.")


page_tong_quan()
