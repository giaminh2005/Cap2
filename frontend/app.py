"""
frontend/app.py  —  Giao dien web SmartCau AI (Streamlit, nhieu trang)
=======================================================================
CHAY (tu THU MUC GOC du an, sau khi backend da chay):
    streamlit run frontend/app.py

Dang nhap bang tai khoan trong CSDL (lan dau: admin / admin123). Menu hien
theo vai tro (FR-12):
    Nguoi truc : Tong quan, Truc ca & su co, Bang LED, Luot qua cau, Doi chieu ve
    Quan ly    : + Co cau khach, Lich su, Bao cao, Camera, Quyen rieng tu
    Quan tri   : + Cau hinh, Nguoi nhan canh bao, Tai khoan, Google Sheets

Bang phan cong trang (docs/PHAN_CONG.md):
    M1 Minh  : luot_qua_cau, camera         M2 Minh  : app, common, tai_khoan
    M3 Hoan  : truc_ca, bang_led            M4 Hoan  : co_cau_khach, bao_cao
    M5 Hoan  : doi_chieu_ve                 M6 Khanh : tong_quan, lich_su
    M7 Khanh : cau_hinh, nguoi_nhan, quyen_rieng_tu
"""

import streamlit as st

st.set_page_config(page_title="SmartCau · Chùa Cầu Hội An", page_icon=":material/temple_buddhist:", layout="wide",
                   initial_sidebar_state="expanded")

from common import (ROLE_VI, alert_watcher, api_is_up, apply_theme, change_password_form,  # noqa: E402
                    current_user, login_page, logout, restore_session)

if not restore_session():
    login_page()
    st.stop()

apply_theme()
user = current_user()
role = user["role"]

if user.get("must_change_password"):
    from common import page_header
    page_header("Bảo mật tài khoản", "Đổi mật khẩu", "Mật khẩu mới phải có ít nhất 6 ký tự.")
    change_password_form(forced=True)
    if st.button("Đăng xuất"):
        logout()
    st.stop()

ALL, MANAGER, ADMIN = ("admin", "quan_ly", "nguoi_truc"), ("admin", "quan_ly"), ("admin",)
PAGES = [
    ("Vận hành", "views/tong_quan.py", "Tổng quan", ":material/space_dashboard:", ALL),
    ("Vận hành", "views/truc_ca.py", "Trực ca & sự cố", ":material/notifications_active:", ALL),
    ("Vận hành", "views/bang_led.py", "Bảng LED tại chỗ", ":material/traffic:", ALL),
    ("Vận hành", "views/luot_qua_cau.py", "Lượt qua cầu", ":material/swap_horiz:", ALL),
    ("Vận hành", "views/doi_chieu_ve.py", "Đối chiếu vé", ":material/confirmation_number:", ALL),
    ("Phân tích", "views/co_cau_khach.py", "Cơ cấu khách", ":material/groups:", MANAGER),
    ("Phân tích", "views/lich_su.py", "Lịch sử lượt khách", ":material/history:", MANAGER),
    ("Phân tích", "views/bao_cao.py", "Báo cáo định kỳ", ":material/insert_chart:", MANAGER),
    ("Hệ thống", "views/camera.py", "Camera", ":material/videocam:", MANAGER),
    ("Hệ thống", "views/cau_hinh.py", "Ngưỡng & giờ hoạt động", ":material/tune:", ADMIN),
    ("Hệ thống", "views/nguoi_nhan.py", "Người nhận cảnh báo", ":material/forward_to_inbox:", ADMIN),
    ("Hệ thống", "views/tai_khoan.py", "Tài khoản", ":material/manage_accounts:", ADMIN),
    ("Hệ thống", "views/quyen_rieng_tu.py", "Quyền riêng tư", ":material/shield:", MANAGER),
    ("Hệ thống", "views/dong_bo_sheets.py", "Google Sheets", ":material/table_view:", ADMIN),
]

nav = {}
first = True
for group, path, title, icon, roles in PAGES:
    if role in roles:
        nav.setdefault(group, []).append(st.Page(path, title=title, icon=icon, default=first))
        first = False
import os  # noqa: E402

st.logo(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.svg"), size="large")
page = st.navigation(nav, expanded=True)

with st.sidebar:
    online = api_is_up()
    st.markdown(f'<div class="sc-user"><div style="font-weight:500">{user.get("full_name") or user["username"]}</div>'
                f'<div class="role">{ROLE_VI.get(role, role)} · @{user["username"]}</div>'
                f'<div class="role" style="margin-top:6px"><span class="dot" style="background:'
                f'{"#7FB08A" if online else "#D9826F"}"></span>{"Đã kết nối máy chủ" if online else "Mất kết nối máy chủ"}</div></div>',
                unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1.popover("Mật khẩu", width="stretch"):
        change_password_form()
    if c2.button("Đăng xuất", width="stretch"):
        logout()
    alert_watcher()          # thong bao noi khi co su co moi, o bat ky trang nao

page.run()
