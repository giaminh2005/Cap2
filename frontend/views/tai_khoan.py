"""
frontend/views/tai_khoan.py  —  MODULE M2 · F6.1 Quan ly tai khoan (FR-12, NFR-04)
Phu trach: MINH.
"""

import streamlit as st

from common import ROLE_VI, ApiError, api_post, api_put, badge, current_user, fmt_time, note, page_header, safe_get

page_header("👤", "Tài khoản", "Tạo, khóa và phân quyền tài khoản theo 3 vai trò")

ROLE_FROM_VI = {v: k for k, v in ROLE_VI.items()}

with st.form("new", clear_on_submit=True):
    st.markdown("**Tạo tài khoản mới**")
    c1, c2, c3, c4 = st.columns(4)
    username = c1.text_input("Tên đăng nhập", placeholder="vd: truc_bac")
    full_name = c2.text_input("Họ tên")
    password = c3.text_input("Mật khẩu tạm (≥ 6 ký tự)", type="password")
    role = c4.selectbox("Vai trò", list(ROLE_FROM_VI), index=2)
    if st.form_submit_button("Tạo tài khoản", type="primary"):
        try:
            api_post("/users", {"username": username, "full_name": full_name, "password": password,
                                "role": ROLE_FROM_VI[role]})
            st.success(f"Đã tạo {username}. Người dùng sẽ phải đổi mật khẩu ở lần đăng nhập đầu.")
        except ApiError as e:
            st.error(str(e))

me = current_user()
for u in safe_get("/users") or []:
    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2.4, 1.4, 1, 1.4])
        c1.markdown(f"**{u['full_name'] or u['username']}** · @{u['username']}"
                    f"{' (bạn)' if u['username'] == me['username'] else ''}  \n"
                    f"<span style='color:var(--muted);font-size:.85rem'>Đăng nhập gần nhất: "
                    f"{fmt_time(u['last_login'], '%H:%M %d/%m/%Y')}</span>", unsafe_allow_html=True)
        c1.markdown(badge(u["role_label"], "info") + " " +
                    badge("Hoạt động" if u["active"] else "Đã khóa", "ok" if u["active"] else "danger"),
                    unsafe_allow_html=True)
        new_role = c2.selectbox("Vai trò", list(ROLE_FROM_VI), index=list(ROLE_FROM_VI).index(u["role_label"]),
                                key=f"r{u['id']}", label_visibility="collapsed")
        if ROLE_FROM_VI[new_role] != u["role"]:
            try:
                api_put(f"/users/{u['id']}", {"role": ROLE_FROM_VI[new_role]})
                st.rerun()
            except ApiError as e:
                st.error(str(e))
        if c3.button("Mở khóa" if not u["active"] else "Khóa", key=f"a{u['id']}", width="stretch"):
            try:
                api_put(f"/users/{u['id']}", {"active": not u["active"]})
                st.rerun()
            except ApiError as e:
                st.error(str(e))
        with c4.popover("Đặt lại mật khẩu", width="stretch"):
            pw = st.text_input("Mật khẩu tạm mới", type="password", key=f"p{u['id']}")
            if st.button("Lưu", key=f"ps{u['id']}"):
                try:
                    api_put(f"/users/{u['id']}", {"password": pw})
                    st.success("Đã đặt lại. Người dùng phải đổi mật khẩu khi đăng nhập.")
                except ApiError as e:
                    st.error(str(e))

note("<b>Quản trị viên:</b> toàn quyền. <b>Quản lý:</b> xem vận hành, phân tích, báo cáo, camera. "
     "<b>Người trực:</b> tổng quan, trực ca, bảng LED, lượt qua cầu, đối chiếu vé — không vào được trang cấu hình. "
     "Mật khẩu được lưu dạng băm, khóa tài khoản sẽ đăng xuất người đó ngay.")
