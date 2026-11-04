"""
frontend/views/luot_qua_cau.py  —  MODULE M1 · F1.2, F1.3 (FR-02, FR-03)
Phu trach: MINH.
onbridge = num1 + num2 tu 2 camera chan cau, luot vao trong ngay (dem) va
thong ke theo gio / ngay / thang / nam / khoang thoi gian tuy chon.
"""

from datetime import timedelta

import pandas as pd
import streamlit as st

from common import (section, COLORS, HAS_PLOTLY, ApiError, api_post, fmt_int, has_role, kpi, kpi_row, local_today,
                    note, page_header, safe_get, style_fig)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Vận hành · Hai camera chân cầu", "Lượt qua cầu", "Số khách đang trên cầu tính từ hai camera chân cầu, và lượt vào cầu theo giờ, ngày, tháng, năm.")


@st.fragment(run_every=2)
def live_state():
    s = safe_get("/bridge/state")
    if s is None:
        return
    kpi_row([
        kpi("Đang trên cầu (onbridge)", fmt_int(s["onbridge"]), "= num1 + num2", "primary"),
        kpi("Camera 1 (num1)", fmt_int(s["num1"]), "vào − ra ở chân cầu 1", "info"),
        kpi("Camera 2 (num2)", fmt_int(s["num2"]), "vào − ra ở chân cầu 2", "info"),
        kpi("Lượt vào hôm nay (dem)", fmt_int(s["dem"]), f"ngày {s['date'][8:]}/{s['date'][5:7]}/{s['date'][:4]}", "ok"),
    ])


live_state()
note("Khách đi qua vạch về phía cầu: <b>num += 1, dem += 1</b>. Đi qua vạch ra ngoài: <b>num −= 1</b>. "
     "Khi onbridge về 0 (hoặc âm do camera bỏ sót), hệ thống đặt lại num1 = num2 = 0. "
     "<b>dem</b> tự về 0 lúc 0 giờ mỗi ngày.")

if has_role("admin", "quan_ly"):
    with st.expander("Đặt lại số người trên cầu (khi đếm tay thấy lệch)"):
        c1, c2 = st.columns([2, 1])
        also_dem = c1.checkbox("Đặt lại cả lượt vào hôm nay")
        if c2.button("Đặt lại về 0", type="primary"):
            try:
                api_post("/bridge/reset", params={"reset_dem": also_dem})
                st.success("Đã đặt lại.")
            except ApiError as e:
                st.error(str(e))

section("Thống kê lượt vào cầu")
GROUPS = {"Theo giờ": "hour", "Theo ngày": "day", "Theo tháng": "month", "Theo năm": "year"}
today = local_today()
with st.container(border=True):
    c1, c2 = st.columns([1, 2])
    group_vi = c1.selectbox("Gom nhóm", list(GROUPS), index=1)
    group = GROUPS[group_vi]
    default_from = {"hour": today, "day": today - timedelta(days=29), "month": today.replace(month=1, day=1),
                    "year": today.replace(year=today.year - 4, month=1, day=1)}[group]
    picked = c2.date_input("Khoảng thời gian", value=(default_from, today), format="DD/MM/YYYY", key=f"range_{group}")

if not isinstance(picked, (tuple, list)) or len(picked) != 2:
    st.info("Chọn ngày bắt đầu và ngày kết thúc.")
    st.stop()

data = safe_get("/bridge/stats", {"group": group, "date_from": picked[0].isoformat(), "date_to": picked[1].isoformat()})
if data is None:
    st.stop()

days = (picked[1] - picked[0]).days + 1
kpi_row([
    kpi("Tổng lượt vào cầu", fmt_int(data["total_entries"]), f"{days} ngày", "primary"),
    kpi("Tổng lượt ra", fmt_int(data["total_exits"]), "", "info"),
    kpi("Trung bình mỗi ngày", fmt_int(round(data["total_entries"] / days)), "lượt vào", "ok"),
])

if not data["rows"]:
    st.info("Chưa có lượt qua cầu nào trong khoảng thời gian này.")
    st.stop()


def label(period: str) -> str:
    if group == "hour":
        return f"{period[11:13]}h {period[8:10]}/{period[5:7]}"
    if group == "day":
        return f"{period[8:10]}/{period[5:7]}/{period[:4]}"
    if group == "month":
        return f"Tháng {period[5:7]}/{period[:4]}"
    return f"Năm {period}"


df = pd.DataFrame(data["rows"])
df["Thời gian"] = df["period"].map(label)
with st.container(border=True):
    if HAS_PLOTLY:
        fig = go.Figure()
        fig.add_bar(x=df["Thời gian"], y=df["entries_cam1"], name="Vào ở chân cầu 1", marker_color=COLORS["primary"])
        fig.add_bar(x=df["Thời gian"], y=df["entries_cam2"], name="Vào ở chân cầu 2", marker_color=COLORS["ochre"])
        fig.update_layout(barmode="stack")
        st.plotly_chart(style_fig(fig, 340), width="stretch")
    else:
        st.bar_chart(df.set_index("Thời gian")[["entries_cam1", "entries_cam2"]])

table = df[["Thời gian", "entries", "exits", "entries_cam1", "entries_cam2"]].rename(columns={
    "entries": "Lượt vào", "exits": "Lượt ra", "entries_cam1": "Vào ở chân cầu 1", "entries_cam2": "Vào ở chân cầu 2"})
st.dataframe(table, width="stretch", hide_index=True)
st.download_button("Xuất CSV", data=table.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"luot_qua_cau_{group}_{picked[0]}_{picked[1]}.csv", mime="text/csv")
