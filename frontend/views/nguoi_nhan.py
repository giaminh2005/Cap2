"""
frontend/views/nguoi_nhan.py  —  SKELETON
------------------------------------------
Phu trach: KHANH     Chuc nang: F6.3 Quan ly nguoi nhan canh bao (FR-13) · PB-11
API dung: GET/POST /recipients, DELETE /recipients/{id}   (routers/admin.py)
"""

import pandas as pd
import streamlit as st

from common import api_delete, api_get, api_post, mock_notice, page_header, todo_box

page_header("📨", "Quan tri vien", "Nguoi nhan canh bao",
            "Danh sach nguoi truc / quan ly nhan tin nhan khi cau sap day hoac qua tai.")

todo_box("Khanh", [
    "Backend: them bang Recipient trong routers/admin.py de khong mat du lieu khi tat server",
    "Kiem tra them/xoa hoat dong, ghi vao kich ban UAT (AC-09.2)",
])

data, err = api_get("/recipients")
if err:
    st.error(err)
    st.stop()
mock_notice(data)

items = data.get("items", [])
st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)

with st.form("them_nguoi_nhan"):
    st.markdown("**Them nguoi nhan**")
    c1, c2, c3 = st.columns([2, 1, 2])
    name = c1.text_input("Ho ten / vai tro")
    channel = c2.selectbox("Kenh", ["telegram", "zalo", "sms", "email"])
    address = c3.text_input("Chat ID / so dien thoai / email")
    if st.form_submit_button("Them"):
        if not name or not address:
            st.warning("Can nhap ho ten va dia chi nhan.")
        else:
            res, err = api_post("/recipients", {"name": name, "channel": channel, "address": address}, admin=True)
            st.toast(err or "Da them")
            st.rerun()

if items:
    to_delete = st.selectbox("Xoa nguoi nhan", [f"{i['id']} - {i['name']}" for i in items])
    if st.button("Xoa"):
        rid = int(to_delete.split(" - ")[0])
        res, err = api_delete(f"/recipients/{rid}")
        st.toast(err or "Da xoa")
        st.rerun()
