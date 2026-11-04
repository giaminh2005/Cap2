"""
frontend/views/nguoi_nhan.py  —  MODULE M7 · F6.3 Nguoi nhan canh bao (FR-13, FR-06)
Phu trach: KHANH.
"""

import streamlit as st

from common import ApiError, api_delete, api_post, api_put, badge, note, page_header, safe_get

page_header("Hệ thống · Thông báo", "Người nhận cảnh báo", "Người trực và cán bộ quản lý nhận tin nhắn cảnh báo và báo cáo ngày.")

CHANNELS = {"Telegram": "telegram", "Zalo OA (chưa hỗ trợ)": "zalo", "SMS (chưa hỗ trợ)": "sms",
            "Email (chưa hỗ trợ)": "email"}

with st.form("add", clear_on_submit=True):
    st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Thêm người nhận</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1.2, 2])
    name = c1.text_input("Họ tên / vai trò", placeholder="vd: Người trực đầu cầu Bắc")
    channel = c2.selectbox("Kênh", list(CHANNELS))
    address = c3.text_input("Địa chỉ nhận", placeholder="Telegram chat_id, vd 123456789")
    if st.form_submit_button("Thêm", type="primary"):
        try:
            api_post("/recipients", {"name": name, "channel": CHANNELS[channel], "address": address})
            st.success(f"Đã thêm {name}.")
        except ApiError as e:
            st.error(str(e))

rows = safe_get("/recipients") or []
if not rows:
    st.info("Chưa có người nhận nào. Nếu máy chủ có biến TELEGRAM_CHAT_ID, cảnh báo sẽ gửi tới chat đó.")
for r in rows:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 1.2, 1, 1])
        c1.markdown(f"**{r['name']}**  \n{r['channel_label']} · `{r['address']}`")
        c1.markdown(badge("Đang nhận" if r["active"] else "Tạm tắt", "ok" if r["active"] else "muted"),
                    unsafe_allow_html=True)
        if c2.button("Tắt" if r["active"] else "Bật", key=f"t{r['id']}", width="stretch"):
            api_put(f"/recipients/{r['id']}", {"active": not r["active"]})
            st.rerun()
        if c3.button("Gửi thử", key=f"s{r['id']}", width="stretch"):
            try:
                res = api_post(f"/recipients/{r['id']}/test")
                (st.success if res["status"] == "ok" else st.warning)(
                    "Đã gửi tin nhắn thử." if res["status"] == "ok" else res["status"])
            except ApiError as e:
                st.error(str(e))
        if c4.button("Xóa", key=f"d{r['id']}", width="stretch"):
            api_delete(f"/recipients/{r['id']}")
            st.rerun()

note("<b>Cách lấy Telegram chat_id:</b> tạo bot bằng @BotFather, đặt token vào biến môi trường "
     "<code>TELEGRAM_BOT_TOKEN</code> trên máy chạy backend. Người nhận nhắn bất kỳ tin nào cho bot, rồi mở "
     "<code>https://api.telegram.org/bot&lt;token&gt;/getUpdates</code> để xem <code>chat.id</code>. "
     "Tin nhắn được gửi khi: cảnh báo Vàng, cảnh báo Đỏ (nhắc lại tối đa 1 lần mỗi 3 phút), đoàn khách lớn, "
     "mất tín hiệu camera và khi sự cố đóng.")
