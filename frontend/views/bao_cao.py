"""
frontend/views/bao_cao.py  —  MODULE M4 · F5.2, F5.3 Lap va xuat bao cao (FR-11, AC-07.1, KPI O1/O4/O5/O8, Sprint 0 F7)
Phu trach: HOAN.
Bao cao ngay / tuan / thang tu du lieu that, chi so KPI, bieu do nhiet gio x thu,
xuat Excel + PDF, danh sach bao cao ngay TU DONG lap sau gio dong cua.
"""

from datetime import timedelta

import pandas as pd
import streamlit as st

from backend.report_export import report_tables, to_excel, to_pdf
from common import (C, HAS_PLOTLY, ApiError, insight_list, api_get_bytes, api_post, empty, fmt_duration, fmt_int, fmt_pct,
                    fmt_time, has_role, kpi, kpi_row, local_today, note, page_header, safe_get, section, style_fig)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Phân tích · Báo cáo", "Báo cáo định kỳ",
            "Lượng khách, chỉ số an toàn và cơ cấu khách theo ngày, tuần, tháng. Báo cáo ngày được hệ thống "
            "tự lập và gửi sau giờ đóng cửa.")

PERIODS = {"Ngày": "day", "Tuần · 7 ngày": "week", "Tháng · 30 ngày": "month"}
c1, c2, c3 = st.columns([1.4, 1, 1.6])
period_vi = c1.segmented_control("Kỳ báo cáo", list(PERIODS), default="Ngày", selection_mode="single") or "Ngày"
day = c2.date_input("Ngày cuối kỳ", value=local_today(), format="DD/MM/YYYY")
period = PERIODS[period_vi]

r = safe_get("/reports/summary", {"period": period, "date": day.isoformat()})
if r is None:
    st.stop()
with c3:
    st.markdown('<div style="height:28px"></div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    b1.download_button("Xuất Excel", data=to_excel(r), type="primary", width="stretch",
                       file_name=f"bao_cao_{period}_{r['date_to']}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    try:
        b2.download_button("Xuất PDF", data=to_pdf(r), width="stretch",
                           file_name=f"bao_cao_{period}_{r['date_to']}.pdf", mime="application/pdf")
    except ImportError:
        b2.caption("Cần cài fpdf2 để xuất PDF.")

kpi_row([
    kpi("Lượt vào cầu", fmt_int(r["total_entries"]),
        f"{r['date_from'][8:]}/{r['date_from'][5:7]} – {r['date_to'][8:]}/{r['date_to'][5:7]}/{r['date_to'][:4]}", "primary"),
    kpi("Lượt qua mặt tiền", fmt_int(r["facade_passes"]), "không lên cầu", "info"),
    kpi("Đông nhất cùng lúc", f"{fmt_int(r['peak_count'])}<small> người</small>",
        f"giờ nhiều khách nhất {r['peak_hour']}h" if r["peak_hour"] is not None else "", "warn"),
    kpi("Sự cố quá tải", fmt_int(r["incidents"]), f"phản hồi trung bình {fmt_duration(r['avg_handle_seconds'])}",
        "danger" if r["incidents"] else "ok"),
])

ins = safe_get("/insights/summary")
if ins:
    with st.expander("Nhận định tự động hôm nay", expanded=True):
        insight_list(ins["items"])

section("Chỉ số an toàn", "theo bộ KPI Sprint 0")
k = r["kpis"]
o4, o5 = k["o4_handled_within_3min_pct"], k["o5_false_alarm_pct"]
kpi_row([
    kpi("O1 · Phút vượt sức chứa", f"{fmt_int(k['o1_minutes_over'])}<small> phút</small>",
        f"{k['o1_minutes_per_day']} phút/ngày có hơn {k['capacity']} người", "danger" if k["o1_minutes_over"] else "ok"),
    kpi("O4 · Xử lý trong 3 phút", fmt_pct(o4), f"{k['o4_real_incidents']} sự cố thật · mục tiêu ≥ 90%",
        "" if o4 is None else "ok" if o4 >= 90 else "warn"),
    kpi("O5 · Cảnh báo sai", fmt_pct(o5), f"{k['o5_false_alarms']} sự cố báo sai · mục tiêu ≤ 5%",
        "" if o5 is None else "ok" if o5 <= 5 else "warn"),
    kpi("O8 · Chênh lệch vé", fmt_pct(k["o8_gap_rate_pct"]), "lượt vào so với cuống vé", "info"),
])
note("O1 tính số phút có ít nhất một lần đo vượt sức chứa. O4 và O5 tính trên sự cố cảnh báo Đỏ; "
     "người trực đánh dấu báo sai ở trang Trực ca & sự cố. O8 chỉ tính những ngày đã nhập số cuống vé.")

if HAS_PLOTLY:
    left, right = st.columns([2, 1], gap="large")
    with left:
        if period == "day":
            section("Lượt vào theo khung 15 phút")
            df = pd.DataFrame(r["by_15min"])
            x, y = (df["slot"], df["entries"]) if not df.empty else ([], [])
        else:
            section("Lượt vào theo ngày")
            df = pd.DataFrame(r["by_day"])
            x, y = df["date"].map(lambda s: f"{s[8:]}/{s[5:7]}"), df["entries"]
        if len(x):
            fig = go.Figure(go.Bar(x=x, y=y, marker_color=C["oxblood"], hovertemplate="%{x} · %{y} lượt<extra></extra>"))
            fig.update_yaxes(rangemode="tozero")
            st.plotly_chart(style_fig(fig, 290, legend=False), width="stretch")
        else:
            empty("Chưa có lượt vào nào trong kỳ.")
    with right:
        section("Bốn khung giờ")
        s = pd.DataFrame(r["time_slots"])
        fig = go.Figure(go.Bar(x=s["entries"], y=s["slot"], orientation="h", marker_color=C["gold"],
                               hovertemplate="%{y} · %{x} lượt<extra></extra>"))
        fig.update_layout(yaxis=dict(autorange="reversed"))
        fig.update_xaxes(rangemode="tozero")
        st.plotly_chart(style_fig(fig, 290, legend=False), width="stretch")

    section("Biểu đồ nhiệt theo giờ và thứ", "trung bình lượt vào mỗi ngày")
    weeks = st.select_slider("Khoảng thời gian", options=[4, 8, 12, 26, 52], value=8,
                             format_func=lambda w: f"{w} tuần gần nhất", label_visibility="collapsed")
    hm = safe_get("/reports/heatmap", {"date_from": (day - timedelta(days=7 * weeks - 1)).isoformat(),
                                        "date_to": day.isoformat()})
    if hm:
        hours = list(range(6, 24))
        z = [[row[h] for h in hours] for row in hm["avg_per_day"]]
        fig = go.Figure(go.Heatmap(
            z=z, x=[f"{h}h" for h in hours], y=hm["weekdays"], xgap=2, ygap=2,
            colorscale=[[0, "#F7F1E6"], [0.35, "#E2C48A"], [0.7, "#B0603A"], [1, "#6E1D13"]],
            hovertemplate="%{y} · %{x}<br>trung bình %{z} lượt<extra></extra>", colorbar=dict(thickness=10, outlinewidth=0)))
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(style_fig(fig, 320, legend=False), width="stretch")
        st.caption(f"Từ {hm['date_from'][8:]}/{hm['date_from'][5:7]} đến {hm['date_to'][8:]}/{hm['date_to'][5:7]}/{hm['date_to'][:4]} · "
                   "ô càng đậm là khung giờ càng đông, dùng để bố trí người soát vé và điều tiết.")

section("Bảng tổng hợp")
tables = report_tables(r)
t1, t2 = st.columns(2, gap="large")
t1.dataframe(tables["Tổng quan"].astype(str), hide_index=True, width="stretch", height=390)
t2.dataframe(tables["Cơ cấu khách"].astype(str), hide_index=True, width="stretch", height=390)
st.caption("Trong nước / nước ngoài là ước lượng của mô hình AI, không phải quốc tịch.")

section("Báo cáo ngày tự động", "lập và gửi sau giờ đóng cửa")
daily = safe_get("/reports/daily") or []
if not daily:
    empty("Chưa có báo cáo ngày nào. Hệ thống sẽ tự lập sau giờ đóng cửa hôm nay.")
for d in daily[:14]:
    a, b, c, e = st.columns([1.3, 2.8, 1, 1])
    a.markdown(f"**{d['date'][8:]}/{d['date'][5:7]}/{d['date'][:4]}**")
    b.markdown(f"<span style='color:var(--muted);font-size:.88rem'>{fmt_int(d['total_entries'])} lượt vào · "
               f"{d['incidents']} sự cố · lập lúc {fmt_time(d['created_at'], '%H:%M %d/%m')} · "
               f"{d['delivery'] or 'đang gửi'}</span>", unsafe_allow_html=True)
    try:
        c.download_button("Tải PDF", data=api_get_bytes(f"/reports/daily/{d['date']}/pdf"), key=f"pdf{d['date']}",
                          file_name=f"bao_cao_ngay_{d['date']}.pdf", mime="application/pdf", width="stretch")
    except ApiError as err:
        c.caption(str(err))
    if has_role("admin", "quan_ly") and e.button("Gửi lại", key=f"rs{d['date']}", width="stretch"):
        try:
            res = api_post(f"/reports/daily/{d['date']}/send")
            st.success(res["delivery"])
        except ApiError as err:
            st.error(str(err))
