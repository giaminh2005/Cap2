"""
frontend/views/doi_chieu_ve.py  —  SKELETON
--------------------------------------------
Phu trach: HOAN      Chuc nang: F4.1 Ghi nhan so ve theo gio, F4.2 Tinh ty le
                                chenh lech (FR-14) · PB-12 (US-10)
API dung: POST /tickets, GET /tickets/reconciliation?date=   (routers/tickets.py)
F4.3 doi chieu khach quoc te: NGOAI MVP (BRD Bang 27) - khong lam.
"""

from datetime import date

import pandas as pd
import streamlit as st

from common import api_get, api_post, mock_notice, page_header, render_metric, todo_box

page_header("🎫", "Can bo quan ly ve", "Doi chieu luot vao cau voi so ve",
            "Nhap so cuong ve thu theo gio, xem ty le chenh lech de danh gia that thoat ve.")

todo_box("Hoan", [
    "Backend: bang TicketCount + tinh chenh lech that trong routers/tickets.py",
    "Lam cuoi Sprint 5 (do uu tien Could) - neu tre, giu ban mock de demo",
])

day = st.date_input("Ngay doi chieu", value=date.today())

with st.form("nhap_ve"):
    c1, c2 = st.columns(2)
    hour = c1.number_input("Gio", min_value=0, max_value=23, value=9)
    tickets = c2.number_input("So cuong ve thu", min_value=0, value=0)
    if st.form_submit_button("Luu"):
        res, err = api_post("/tickets", {"date": day.isoformat(), "hour": int(hour), "ticket_count": int(tickets)})
        st.toast(err or "Da gui (backend hien chua luu that)")

data, err = api_get("/tickets/reconciliation", params={"date": day.isoformat()})
if err:
    st.error(err)
    st.stop()
mock_notice(data)

st.markdown(
    f"""<div class="hoian-kpi-row">
        {render_metric("Luot vao dem duoc", data['entries_counted'])}
        {render_metric("So ve thu", data['tickets_sold'])}
        {render_metric("Chenh lech", data['gap'])}
        {render_metric("Ty le chenh lech", data['gap_rate_pct'], "%")}
    </div>""",
    unsafe_allow_html=True,
)
st.dataframe(pd.DataFrame(data["by_hour"]), use_container_width=True, hide_index=True)
