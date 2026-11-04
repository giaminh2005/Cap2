"""
frontend/views/bao_cao.py  —  MODULE M4 · F5.2, F5.3 Lap va xuat bao cao (FR-11, AC-07.1)
Phu trach: HOAN.
Bao cao ngay / tuan / thang tu du lieu that; xuat Excel va PDF.
"""

import pandas as pd
import streamlit as st

from common import (COLORS, HAS_PLOTLY, fmt_duration, fmt_int, kpi, kpi_row, local_today, page_header,
                    safe_get, style_fig)
from report_export import report_tables, to_excel, to_pdf

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("📊", "Báo cáo định kỳ", "Lượng khách, cơ cấu khách và sự cố theo ngày, tuần, tháng · xuất PDF và Excel")

PERIODS = {"Ngày": "day", "Tuần (7 ngày)": "week", "Tháng (30 ngày)": "month"}
with st.container(border=True):
    c1, c2 = st.columns(2)
    period_vi = c1.radio("Kỳ báo cáo", list(PERIODS), horizontal=True)
    day = c2.date_input("Ngày cuối kỳ", value=local_today(), format="DD/MM/YYYY")
period = PERIODS[period_vi]

r = safe_get("/reports/summary", {"period": period, "date": day.isoformat()})
if r is None:
    st.stop()

kpi_row([
    kpi("Lượt vào cầu", fmt_int(r["total_entries"]), f"{r['date_from'][8:]}/{r['date_from'][5:7]} → {r['date_to'][8:]}/{r['date_to'][5:7]}", "primary"),
    kpi("Lượt qua mặt tiền", fmt_int(r["facade_passes"]), "không lên cầu", "info"),
    kpi("Đông nhất trên cầu", fmt_int(r["peak_count"]), "người cùng lúc", "warn"),
    kpi("Sự cố quá tải", fmt_int(r["incidents"]), f"phản hồi TB {fmt_duration(r['avg_handle_seconds'])}",
        "danger" if r["incidents"] else "ok"),
])

c1, c2 = st.columns(2)
c1.download_button("⬇️ Xuất Excel", data=to_excel(r), type="primary", width="stretch",
                   file_name=f"bao_cao_{period}_{r['date_to']}.xlsx",
                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
try:
    c2.download_button("⬇️ Xuất PDF", data=to_pdf(r), width="stretch",
                       file_name=f"bao_cao_{period}_{r['date_to']}.pdf", mime="application/pdf")
except ImportError:
    c2.warning("Cần cài fpdf2 để xuất PDF: pip install fpdf2")

if HAS_PLOTLY:
    left, right = st.columns([2, 1])
    with left, st.container(border=True):
        if period == "day":
            st.markdown("**Lượt vào theo khung 15 phút**")
            df = pd.DataFrame(r["by_15min"])
            x, y = (df["slot"], df["entries"]) if not df.empty else ([], [])
        else:
            st.markdown("**Lượt vào theo ngày**")
            df = pd.DataFrame(r["by_day"])
            x, y = df["date"].map(lambda s: f"{s[8:]}/{s[5:7]}"), df["entries"]
        fig = go.Figure(go.Bar(x=x, y=y, marker_color=COLORS["primary"]))
        fig.update_layout(bargap=0.25)
        fig.update_yaxes(rangemode="tozero")
        st.plotly_chart(style_fig(fig, 300, legend=False), width="stretch")
    with right, st.container(border=True):
        st.markdown("**Theo 4 khung giờ**")
        s = pd.DataFrame(r["time_slots"])
        fig = go.Figure(go.Bar(x=s["entries"], y=s["slot"], orientation="h", marker_color=COLORS["ochre"]))
        fig.update_layout(yaxis=dict(autorange="reversed"))
        fig.update_xaxes(rangemode="tozero")
        st.plotly_chart(style_fig(fig, 300, legend=False), width="stretch")

tables = report_tables(r)
t1, t2 = st.columns(2)
with t1:
    st.markdown("**Tổng quan**")
    st.dataframe(tables["Tổng quan"].astype(str), hide_index=True, width="stretch")
with t2:
    st.markdown("**Cơ cấu khách**")
    st.dataframe(tables["Cơ cấu khách"].astype(str), hide_index=True, width="stretch")
    st.caption("Trong nước / nước ngoài là ước lượng của mô hình AI, không phải quốc tịch.")
