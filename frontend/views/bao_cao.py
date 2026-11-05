"""
frontend/views/bao_cao.py  —  MODULE M4 · F5.2, F5.3 Lap va xuat bao cao (FR-11, AC-07.1, KPI O1/O4/O5/O8, Sprint 0 F7)
Phu trach: HOAN.
Bao cao ngay / tuan / thang tu du lieu that, chi so KPI, bieu do nhiet gio x thu,
xuat Excel + PDF, danh sach bao cao ngay TU DONG lap sau gio dong cua.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from backend.report_export import (ORG_NAME, ORG_PARENT, PDF_DEFAULTS, SECTIONS, period_label, report_tables, to_excel,
                                   to_pdf)
from common import (C, HAS_PLOTLY, ApiError, current_user, insight_list, api_get_bytes, api_post, empty, fmt_duration,
                    fmt_int, fmt_pct, fmt_time, has_role, kpi, kpi_row, local_today, page_header, safe_get, section,
                    style_fig)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Phân tích · Báo cáo", "Báo cáo định kỳ",
            "Lượng khách, chỉ số an toàn và cơ cấu khách theo ngày, tuần, tháng, năm hoặc khoảng thời gian tùy chọn. "
            "Xuất PDF theo thể thức văn bản hành chính, có biểu đồ minh họa.")

PERIODS = {"Ngày": "day", "Tuần": "week", "Tháng": "month", "Năm": "year", "Tùy chọn": "custom"}
today = local_today()
c1, c2 = st.columns([1.6, 2])
period_vi = c1.segmented_control("Kỳ báo cáo", list(PERIODS), default="Tháng", selection_mode="single") or "Tháng"
period = PERIODS[period_vi]
params = {"period": period}
with c2:
    if period == "day":
        params["date"] = st.date_input("Ngày", value=today, max_value=today, format="DD/MM/YYYY").isoformat()
    elif period == "week":
        params["date"] = st.date_input("Ngày cuối tuần (7 ngày tính đến ngày này)", value=today, max_value=today,
                                       format="DD/MM/YYYY").isoformat()
    elif period == "month":
        m1, m2 = st.columns(2)
        month = m1.selectbox("Tháng", list(range(1, 13)), index=today.month - 1, format_func=lambda m: f"Tháng {m:02d}")
        year = m2.selectbox("Năm", list(range(today.year, today.year - 6, -1)))
        params["date"] = f"{year}-{month:02d}-01"
    elif period == "year":
        year = st.selectbox("Năm", list(range(today.year, today.year - 6, -1)))
        params["date"] = f"{year}-01-01"
    else:
        rng = st.date_input("Từ ngày – đến ngày", value=(today - timedelta(days=29), today), max_value=today,
                            format="DD/MM/YYYY")
        if not isinstance(rng, (tuple, list)) or len(rng) != 2:
            st.info("Chọn ngày bắt đầu và ngày kết thúc.")
            st.stop()
        params.update(date_from=rng[0].isoformat(), date_to=rng[1].isoformat())
day = date.fromisoformat(params.get("date") or params.get("date_to"))

r = safe_get("/reports/summary", params)
if r is None:
    st.stop()

# ---------------------------------------------------------------- xuat bao cao
with st.container(border=True):
    st.markdown(f'<div class="sc-eyebrow">Xuất báo cáo · {period_label(r)}</div>', unsafe_allow_html=True)
    with st.expander("Tùy chỉnh nội dung báo cáo PDF", expanded=False):
        sec = st.multiselect("Các mục đưa vào báo cáo", list(SECTIONS), default=list(SECTIONS),
                             format_func=lambda k: SECTIONS[k])
        charts = st.toggle("Kèm biểu đồ minh họa", value=True)
        o1, o2, o3 = st.columns(3)
        report_no = o1.text_input("Số báo cáo", placeholder="vd 15")
        prepared_by = o2.text_input("Người lập báo cáo", value=(current_user() or {}).get("full_name", ""))
        approver = o3.text_input("Thủ trưởng đơn vị (ký)", placeholder="Họ và tên")
        o4, o5 = st.columns(2)
        org_parent = o4.text_input("Cơ quan chủ quản", value=ORG_PARENT.replace("\n", " "))
        org_name = o5.text_input("Đơn vị lập báo cáo", value=ORG_NAME.replace("\n", " "))
        recipients = st.text_area("Nơi nhận", value=PDF_DEFAULTS["recipients"], height=90)
        notes = st.text_area("Kiến nghị, đề xuất thêm (mỗi dòng một ý)", height=90)
    opts = {"sections": sec, "charts": charts, "report_no": report_no, "prepared_by": prepared_by,
            "approver": approver, "recipients": recipients, "notes": notes,
            "org_parent": org_parent, "org_name": org_name}
    name = f"bao_cao_{period}_{r['date_from']}_{r['date_to']}"
    b1, b2, b3 = st.columns([1, 1, 2])
    if b1.button("Lập báo cáo PDF", type="primary", icon=":material/picture_as_pdf:", width="stretch"):
        with st.spinner("Đang lập báo cáo và vẽ biểu đồ..."):
            try:
                st.session_state["pdf_bytes"] = (name, to_pdf(r, opts))
            except ImportError as e:
                st.error(f"Thiếu thư viện: {e}. Chạy: pip install fpdf2 matplotlib")
    b2.download_button("Xuất Excel", data=to_excel(r), width="stretch", icon=":material/table_view:",
                       file_name=f"{name}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    got = st.session_state.get("pdf_bytes")
    if got and got[0] == name:
        b3.download_button("Tải PDF vừa lập", data=got[1], file_name=f"{name}.pdf", mime="application/pdf",
                           icon=":material/download:", width="stretch")

kpi_row([
    kpi("Lượt vào cầu", fmt_int(r["total_entries"]),
        (f"kỳ trước {fmt_int(r['previous']['total_entries'])}" if r.get("previous") else period_label(r)), "primary"),
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

section("Chỉ số an toàn")
k = r["kpis"]
o4, o5 = k["o4_handled_within_3min_pct"], k["o5_false_alarm_pct"]
kpi_row([
    kpi("Phút vượt sức chứa", f"{fmt_int(k['o1_minutes_over'])}<small> phút</small>",
        f"{k['o1_minutes_per_day']} phút/ngày có hơn {k['capacity']} người", "danger" if k["o1_minutes_over"] else "ok"),
    kpi("Xử lý trong 3 phút", fmt_pct(o4), f"{k['o4_real_incidents']} sự cố thật · mục tiêu ≥ 90%",
        "" if o4 is None else "ok" if o4 >= 90 else "warn"),
    kpi("Cảnh báo sai", fmt_pct(o5), f"{k['o5_false_alarms']} sự cố báo sai · mục tiêu ≤ 5%",
        "" if o5 is None else "ok" if o5 <= 5 else "warn"),
    kpi("Chênh lệch vé", fmt_pct(k["o8_gap_rate_pct"]), "lượt vào so với cuống vé", "info"),
])

if HAS_PLOTLY:
    left, right = st.columns([2, 1], gap="large")
    with left:
        if period == "day":
            section("Lượt vào theo khung 15 phút")
            df = pd.DataFrame(r["by_15min"])
            x, y = (df["slot"], df["entries"]) if not df.empty else ([], [])
        elif period == "year" or len(r["by_day"]) > 62:
            section("Lượt vào theo tháng")
            df = pd.DataFrame(r["by_month"])
            x, y = df["month"].map(lambda m: f"T{m[5:7]}/{m[:4]}"), df["entries"]
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

section("Báo cáo tuần", "tự gửi sáng thứ Hai · tuần trước so với tuần trước nữa")
w1, w2, _w = st.columns([1, 1, 2])
try:
    w1.download_button("Tải PDF tuần vừa qua", data=api_get_bytes("/reports/weekly/pdf"), file_name="bao_cao_tuan.pdf",
                       mime="application/pdf", icon=":material/download:", width="stretch")
except ApiError as err:
    w1.caption(str(err))
if has_role("admin", "quan_ly") and w2.button("Gửi báo cáo tuần ngay", icon=":material/send:", width="stretch"):
    try:
        res = api_post("/reports/weekly/send")
        st.success(f"Tuần {res['date_from'][8:]}/{res['date_from'][5:7]} – {res['date_to'][8:]}/{res['date_to'][5:7]}: "
                   f"{fmt_int(res['total_entries'])} lượt (tuần trước {fmt_int(res['prev_total_entries'])}). "
                   f"Đã gửi {res['sent_ok']} tin cho {res['recipients']} người nhận.")
    except ApiError as err:
        st.error(str(err))

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
