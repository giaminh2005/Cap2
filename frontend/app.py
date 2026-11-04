"""
frontend/app.py  —  Giao dien web SmartCau AI (Streamlit, nhieu trang)
=======================================================================
Thay cho admin_web/app.py cu (1 file 780 dong). Gio moi trang la 1 file
rieng trong frontend/views/ -> 3 nguoi sua 3 file khac nhau, khong dung
nhau tren GitHub. File nay CHI lo: cau hinh trang, dang nhap, menu.

CHAY (tu THU MUC GOC du an, sau khi backend da chay):
    streamlit run frontend/app.py

Bang phan cong trang (xem docs/PHAN_CONG.md):
    Van hanh   : Tong quan (Khanh) · Truc ca (Hoan) · Bang LED (Hoan) · Luot qua cau (Minh)
    Phan tich  : Co cau khach (Hoan) · Lich su (Khanh) · Bao cao (Hoan) · Doi chieu ve (Hoan)
    Quan tri   : Nguong canh bao (Khanh) · Nguoi nhan canh bao (Khanh) ·
                 Quyen rieng tu (Khanh) · Google Sheets (Minh)

Can Streamlit >= 1.40 (dung st.navigation).
"""

import streamlit as st

st.set_page_config(
    page_title="SmartCau AI",
    page_icon="\U0001FAD4",
    layout="wide",
    initial_sidebar_state="expanded",
)

from common import API_BASE, api_is_up, apply_custom_theme, login_gate  # noqa: E402

if not login_gate():
    st.stop()

apply_custom_theme()

with st.sidebar:
    st.markdown(
        """
        <div class="hoian-brand">
            <div class="hoian-brand-title">\U0001FAD4 SmartCau AI</div>
            <div class="hoian-brand-subtitle">TRAM QUAN LY &middot; DI SAN HOI AN</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    online = api_is_up()
    dot_color = "var(--hoian-moss)" if online else "var(--hoian-red)"
    status_text = "Da ket noi backend" if online else "Khong ket noi duoc backend"
    st.markdown(
        f'<div style="font-size:.78rem; color:var(--hoian-muted); margin-bottom:10px;">'
        f'<span class="hoian-side-dot" style="background:{dot_color};"></span>{status_text}</div>',
        unsafe_allow_html=True,
    )

pages = {
    "Van hanh": [
        st.Page("views/tong_quan.py", title="Tong quan", icon="🏯", default=True),
        st.Page("views/truc_ca.py", title="Truc ca & su co", icon="🚨"),
        st.Page("views/bang_led.py", title="Bang LED tai cho", icon="🪧"),
        st.Page("views/luot_qua_cau.py", title="Luot qua cau", icon="🌉"),
    ],
    "Phan tich": [
        st.Page("views/co_cau_khach.py", title="Co cau khach", icon="👥"),
        st.Page("views/lich_su.py", title="Lich su luot khach", icon="🏮"),
        st.Page("views/bao_cao.py", title="Bao cao dinh ky", icon="📊"),
        st.Page("views/doi_chieu_ve.py", title="Doi chieu ve", icon="🎫"),
    ],
    "Quan tri": [
        st.Page("views/cau_hinh.py", title="Nguong canh bao", icon="⚙️"),
        st.Page("views/nguoi_nhan.py", title="Nguoi nhan canh bao", icon="📨"),
        st.Page("views/quyen_rieng_tu.py", title="Quyen rieng tu", icon="🛡️"),
        st.Page("views/dong_bo_sheets.py", title="Google Sheets", icon="☁️"),
    ],
}

nav = st.navigation(pages)

with st.sidebar:
    if st.button("\U0001F6AA Dang xuat", use_container_width=True):
        st.session_state["authenticated"] = False
        st.rerun()
    st.markdown(
        f"""
        <div class="hoian-sidebar-note">
            <strong>HOI AN &middot; VIET NAM</strong><br/>
            API: {API_BASE}<br/>
            Nhom 50: Khanh &middot; Hoan &middot; Minh
        </div>
        """,
        unsafe_allow_html=True,
    )

nav.run()
