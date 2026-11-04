"""
frontend/views/bao_cao.py  —  SKELETON
---------------------------------------
Phu trach: HOAN      Chuc nang: F5.2 Lap bao cao dinh ky, F5.3 Xuat bao cao
                                (FR-11) · PB-10 (US-07, can bo thong ke)
API dung: GET /reports/summary?period=day|week|month&date=   (routers/reports.py)
"""

from datetime import date

import pandas as pd
import streamlit as st

from common import api_get, mock_notice, page_header, render_metric, todo_box

page_header("📊", "Can bo thong ke", "Bao cao dinh ky",
            "Bao cao luong khach ngay / tuan / thang tu dong, xuat file de nop Trung tam.")

todo_box("Hoan", [
    "Backend: thay mock trong routers/reports.py bang truy van that",
    "Them bieu do luot vao theo ngay, so lan canh bao Vang/Do, thoi gian xu ly trung binh",
    "Nut xuat CSV (da co) + xuat Excel neu kip",
])

c1, c2 = st.columns(2)
period_label = c1.selectbox("Ky bao cao", ["Ngay", "Tuan", "Thang"])
period = {"Ngay": "day", "Tuan": "week", "Thang": "month"}[period_label]
day = c2.date_input("Tinh den ngay", value=date.today())

data, err = api_get("/reports/summary", params={"period": period, "date": day.isoformat()})
if err:
    st.error(err)
    st.stop()
mock_notice(data)

st.markdown(
    f"""<div class="hoian-kpi-row">
        {render_metric("Tong luot vao", f"{data['total_entries']:,}".replace(",", "."))}
        {render_metric("Gio cao diem", f"{data['peak_hour']}h", f"{data['peak_count']} nguoi")}
        {render_metric("Canh bao Do", data['alerts'].get('CRITICAL_ALERT', 0))}
        {render_metric("Xu ly TB", data['avg_handle_seconds'], "giay")}
    </div>""",
    unsafe_allow_html=True,
)

df_day = pd.DataFrame(data["by_day"])
st.line_chart(df_day.set_index("date"))
st.download_button(
    "⬇️ Xuat CSV",
    data=df_day.to_csv(index=False).encode("utf-8-sig"),
    file_name=f"bao_cao_{period}_{day.isoformat()}.csv",
    mime="text/csv",
)
