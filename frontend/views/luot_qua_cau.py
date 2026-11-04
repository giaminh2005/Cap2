"""
frontend/views/luot_qua_cau.py
------------------------------
Phu trach: MINH      Chuc nang: F1.2, F1.3, F5.1 (FR-02, FR-03, FR-10)
API dung: GET /bridge/state, GET /bridge/stats   (routers/bridge.py)

So khach dang tren cau tu 2 camera chan cau (onbridge = num1 + num2), luot
qua cau trong ngay (dem) va thong ke theo gio / ngay / thang / nam /
khoang thoi gian tuy chon.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from common import _HAS_PLOTLY, api_get, page_header, render_metric

if _HAS_PLOTLY:
    import plotly.express as px

page_header("🌉", "2 camera chan cau", "Luot qua cau",
            "So khach dang tren cau va so luot vao cau theo thoi gian.")


@st.fragment(run_every=2)
def live_state():
    s, err = api_get("/bridge/state")
    if err:
        st.error(err)
        return
    st.markdown(
        f"""
        <div class="hoian-kpi-row" style="grid-template-columns: repeat(4, 1fr); margin-bottom:16px;">
            {render_metric("🧍 Dang tren cau (onbridge)", s["onbridge"])}
            {render_metric("📷 Camera 1 (num1)", s["num1"])}
            {render_metric("📷 Camera 2 (num2)", s["num2"])}
            {render_metric("🎟️ Luot vao hom nay (dem)", s["dem"], f"· {s['date']}")}
        </div>
        """,
        unsafe_allow_html=True,
    )


live_state()

GROUPS = {"Theo gio": "hour", "Theo ngay": "day", "Theo thang": "month", "Theo nam": "year"}
today = date.today()

with st.container(border=True):
    c1, c2 = st.columns([1, 2])
    group_vi = c1.selectbox("Gom nhom", list(GROUPS))
    group = GROUPS[group_vi]
    default_from = {"hour": today, "day": today - timedelta(days=29),
                    "month": today.replace(month=1, day=1), "year": today.replace(year=today.year - 4, month=1, day=1)}[group]
    picked = c2.date_input("Khoang thoi gian", value=(default_from, today), format="DD/MM/YYYY")

if not isinstance(picked, (tuple, list)) or len(picked) != 2:
    st.info("Chon ngay bat dau va ngay ket thuc.")
    st.stop()

data, err = api_get("/bridge/stats", params={"group": group, "date_from": picked[0].isoformat(),
                                             "date_to": picked[1].isoformat()})
if err:
    st.error(err)
    st.stop()

st.markdown(
    f"""
    <div class="hoian-kpi-row" style="grid-template-columns: repeat(2, 1fr); margin:12px 0 16px 0;">
        {render_metric("Tong luot VAO cau", f"{data['total_entries']:,}".replace(",", "."))}
        {render_metric("Tong luot RA", f"{data['total_exits']:,}".replace(",", "."))}
    </div>
    """,
    unsafe_allow_html=True,
)

if not data["rows"]:
    st.info("Chua co luot qua cau nao trong khoang thoi gian nay.")
    st.stop()

df = pd.DataFrame(data["rows"]).rename(columns={
    "period": "Thoi gian", "entries": "Luot vao", "exits": "Luot ra",
    "entries_cam1": "Vao o camera 1", "entries_cam2": "Vao o camera 2",
})

if _HAS_PLOTLY:
    fig = px.bar(df, x="Thoi gian", y=["Vao o camera 1", "Vao o camera 2"],
                 labels={"value": "Luot vao", "variable": ""}, barmode="stack")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), legend_title_text="")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.bar_chart(df.set_index("Thoi gian")[["Vao o camera 1", "Vao o camera 2"]])

st.dataframe(df, use_container_width=True, hide_index=True)
st.download_button("⬇️ Xuat CSV", data=df.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"luot_qua_cau_{group}_{picked[0]}_{picked[1]}.csv", mime="text/csv")
