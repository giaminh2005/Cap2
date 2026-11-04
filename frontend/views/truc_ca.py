"""
frontend/views/truc_ca.py  —  SKELETON
---------------------------------------
Phu trach: HOAN      Chuc nang: F2.4 Ghi nhan xu ly su co (FR-07) · PB-08
API dung: GET /incidents, POST /incidents/{id}/ack   (routers/alerts.py)

Muc tieu (AC-04.1, AC-04.2): nguoi truc xac nhan da xu ly su co bang
<= 2 thao tac; Trung tam biet su co mat bao lau de xu ly.
"""

import pandas as pd
import streamlit as st

from common import api_get, api_post, page_header, todo_box

page_header("🚨", "Nguoi truc kiem soat ve", "Truc ca & su co",
            "Danh sach canh bao dang mo va xac nhan da xu ly ngay tai cho.")

todo_box("Hoan", [
    "Backend: them bang IncidentAck trong routers/alerts.py, luu that khi bam Xac nhan",
    "Chi hien su co CHUA xu ly o tren, da xu ly o bang ben duoi (co cot thoi gian xu ly)",
    "Tu lam moi trang moi 5 giay (st.fragment(run_every=5) hoac st_autorefresh)",
    "Xoa khung 'Viec can lam' nay khi xong",
])

incidents, err = api_get("/incidents", params={"limit": 50})
if err:
    st.error(err)
    st.stop()

if not incidents:
    st.success("Khong co su co nao. Chay 'python tools/seed_demo_data.py' de tao du lieu mau.")
    st.stop()

open_items = [i for i in incidents if not i.get("acknowledged")]
st.markdown(f"**{len(open_items)} su co dang cho xu ly**")

for item in open_items[:10]:
    with st.container(border=True):
        c1, c2 = st.columns([4, 1])
        c1.markdown(f"**{item['event_type']}** · {item.get('count') or '-'} nguoi · {item['timestamp'][:19]}")
        c1.caption(item.get("message") or "")
        if c2.button("Xac nhan da xu ly", key=f"ack_{item['id']}"):
            res, err = api_post(f"/incidents/{item['id']}/ack", {})
            st.toast("Da ghi nhan" if not err else err)

st.markdown("**Toan bo su co gan day**")
st.dataframe(pd.DataFrame(incidents), use_container_width=True, hide_index=True)
