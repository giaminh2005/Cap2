"""
frontend/views/bang_led.py  —  MODULE M3 · F2.2 Tin hieu tai cho (FR-05, AC-03.1, FR-17)
Phu trach: HOAN.
Nhung 2 trang LED toan man hinh (backend/led_display/) — moi dau cau 1 man hinh:
    dau cau 1: Linh Than don khach, Linh Khuyen ra ngan khi Do
    dau cau 2: Linh Khuyen don khach, Linh Than ra ngan khi Do
Tren may dat o dau cau: mo http://<may-chu>:8000/led/?dau=1 (hoac ?dau=2) bang Chrome/Edge, nhan F11.
"""

import streamlit as st
import streamlit.components.v1 as components

_iframe = getattr(st, "iframe", None) or components.iframe   # Streamlit moi: st.iframe

from common import page_header, public_api_base

page_header("Vận hành · Tín hiệu tại chỗ", "Bảng LED hai đầu cầu",
            "Mỗi đầu cầu một màn hình. Linh Thân và Linh Khuyển chào khách, nhắc đi chậm và mời khách chờ khi cầu đầy. "
            "Màu, số liệu và câu cảnh báo đổi ngay khi mức cảnh báo thay đổi, cả hai màn hình dùng chung số liệu.")

base = f"{public_api_base()}/led/"
SCREENS = {
    1: ("Đầu cầu 1", "Linh Thân đón khách · Linh Khuyển ra ngăn khi Đỏ"),
    2: ("Đầu cầu 2", "Linh Khuyển đón khách · Linh Thân ra ngăn khi Đỏ"),
}

view = st.segmented_control("Hiển thị", ["Song song", "Đầu cầu 1", "Đầu cầu 2"], default="Song song",
                            label_visibility="collapsed")
shown = [1, 2] if view in (None, "Song song") else [1 if view == "Đầu cầu 1" else 2]

cols = st.columns(len(shown))
for col, n in zip(cols, shown):
    title, sub = SCREENS[n]
    url = f"{base}?dau={n}"
    with col:
        st.markdown(f"**{title}** · <span style='opacity:.7'>{sub}</span>", unsafe_allow_html=True)
        b1, b2 = st.columns(2)
        b1.link_button("Mở toàn màn hình", url, type="primary", width="stretch")
        b2.link_button("Mở kèm bảng debug", f"{url}&debug=1", width="stretch")
        _iframe(url, height=330 if len(shown) == 2 else 620)

st.link_button("Mở trang xem song song 2 màn hình", f"{base}hai-man-hinh.html")

