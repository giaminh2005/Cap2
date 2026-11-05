"""
frontend/views/nguoi_nhan.py  —  MODULE M7 · F6.3 Nguoi nhan canh bao + ket noi Telegram (FR-13, FR-06)
Phu trach: KHANH.
"""

import streamlit as st

from common import (ApiError, api_delete, api_get, api_post, api_put, badge, empty, page_header, safe_get,
                    section)

page_header("Hệ thống · Thông báo", "Người nhận cảnh báo",
            "Kết nối bot Telegram và quản lý danh sách người trực, cán bộ quản lý nhận cảnh báo và báo cáo ngày.")

# --------------------------------------------------------------- 1. ket noi bot
section("1 · Kết nối bot Telegram")
st_tg = safe_get("/telegram/status") or {}
if st_tg.get("connected"):
    bot = st_tg["bot"]
    c1, c2 = st.columns([3, 1])
    c1.markdown(badge(f"Đã kết nối · @{bot['username']}", "ok") +
                f"&nbsp; <span style='color:var(--muted);font-size:.88rem'>{bot['name']} · "
                f"{'token lấy từ biến môi trường TELEGRAM_BOT_TOKEN' if st_tg['source'] == 'env' else 'token lưu trong hệ thống'}"
                "</span>", unsafe_allow_html=True)
    if st_tg["source"] == "db" and c2.button("Ngắt kết nối", width="stretch"):
        api_delete("/telegram/token")
        st.rerun()
else:
    if st_tg.get("error"):
        st.error(f"Token hiện tại không dùng được: {st_tg['error']}")
    with st.form("tg_token"):
        token = st.text_input("Token của bot", type="password", placeholder="7012345678:AAH3k...",
                              help="Lấy từ @BotFather trên Telegram (lệnh /newbot)")
        if st.form_submit_button("Kết nối", type="primary"):
            try:
                r = api_put("/telegram/token", {"token": token})
                st.success(f"Đã kết nối bot @{r['bot']['username']}.")
                st.rerun()
            except ApiError as e:
                st.error(str(e))

# --------------------------------------------------------------- 2. tim chat_id
section("2 · Thêm người nhận từ Telegram")
if st_tg.get("connected"):
    st.caption(f"Người nhận nhắn một tin cho @{st_tg['bot']['username']} rồi bấm Tìm.")
    if st.button("Tìm người vừa nhắn cho bot"):
        try:
            st.session_state["tg_chats"] = api_get("/telegram/chats")
        except ApiError as e:
            st.error(str(e))
    chats = st.session_state.get("tg_chats")
    if chats is not None:
        if not chats:
            empty("Chưa thấy ai nhắn cho bot. Hãy nhắn một tin cho bot rồi bấm Tìm lại.")
        for ch in chats:
            a, b, c = st.columns([3, 1.4, 1])
            a.markdown(f"**{ch['name']}** <span style='color:var(--muted);font-size:.85rem'>· "
                       f"{'nhóm' if ch['type'] in ('group', 'supergroup') else 'cá nhân'} · chat_id {ch['chat_id']}</span>",
                       unsafe_allow_html=True)
            label = b.text_input("Tên hiển thị", value=ch["name"], key=f"n{ch['chat_id']}", label_visibility="collapsed")
            if ch["added"]:
                c.markdown(badge("Đã thêm", "ok"), unsafe_allow_html=True)
            elif c.button("Thêm", key=f"add{ch['chat_id']}", type="primary", width="stretch"):
                try:
                    api_post("/recipients", {"name": label, "channel": "telegram", "address": ch["chat_id"]})
                    ch["added"] = True
                    st.rerun()
                except ApiError as e:
                    st.error(str(e))
else:
    empty("Kết nối bot ở bước 1 trước.")

# --------------------------------------------------------------- 3. danh sach
section("3 · Danh sách người nhận", "mỗi người chọn loại tin muốn nhận")
rows = safe_get("/recipients") or []
meta = safe_get("/recipients/topics") or {"topics": {}, "presets": {}}
TOPICS, PRESETS = meta["topics"], meta["presets"]
if not rows:
    empty("Chưa có người nhận nào.")
for r in rows:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        c1.markdown(f"**{r['name']}**  \n<span style='color:var(--muted);font-size:.86rem'>{r['channel_label']} · "
                    f"{r['address']}</span>", unsafe_allow_html=True)
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
        if TOPICS:
            p1, p2 = st.columns([1, 3])
            preset = p1.selectbox("Mẫu", ["Chọn mẫu nhanh…"] + list(PRESETS), key=f"pr{r['id']}", label_visibility="collapsed")
            default = PRESETS[preset] if preset in PRESETS else r.get("topics") or list(TOPICS)
            chosen = p2.multiselect("Nhận các loại tin", list(TOPICS), default=default, key=f"tp{r['id']}_{preset}",
                                    format_func=lambda t: TOPICS[t], label_visibility="collapsed",
                                    placeholder="Không nhận tin tự động nào")
            if sorted(chosen) != sorted(r.get("topics") or []):
                if st.button("Lưu loại tin", key=f"sv{r['id']}", type="primary"):
                    api_put(f"/recipients/{r['id']}", {"topics": chosen})
                    st.toast(f"Đã lưu loại tin cho {r['name']}.", icon=":material/check_circle:")
                    st.rerun()

with st.expander("Thêm người nhận bằng tay"):
    with st.form("add", clear_on_submit=True):
        c1, c2 = st.columns([2, 2])
        name = c1.text_input("Họ tên / vai trò", placeholder="vd: Người trực đầu cầu Bắc")
        address = c2.text_input("Telegram chat_id", placeholder="vd 123456789 hoặc -100123... (nhóm)")
        if st.form_submit_button("Thêm", type="primary"):
            try:
                api_post("/recipients", {"name": name, "channel": "telegram", "address": address})
                st.success(f"Đã thêm {name}.")
            except ApiError as e:
                st.error(str(e))

