"""
frontend/views/bang_led.py  —  MODULE M3 · F2.2 Tin hieu tai cho (FR-05, AC-03.1, FR-17)
Phu trach: HOAN.
Nhung trang LED toan man hinh (backend/led_display/, mascot Linh Than + phong nen dong).
Tren may dat o dau cau: mo truc tiep http://<may-chu>:8000/led/ bang Chrome/Edge, nhan F11.
"""

import streamlit as st
import streamlit.components.v1 as components

from common import API_BASE, note, page_header

page_header("Vận hành · Tín hiệu tại chỗ", "Bảng LED tại chỗ",
            "Màn hình đặt tại đầu cầu: Linh Thân chào khách, nhắc đi chậm và mời khách chờ khi cầu đầy. "
            "Màu, số liệu và câu cảnh báo đổi ngay khi mức cảnh báo thay đổi.")

led_url = f"{API_BASE}/led/"
c1, c2, c3 = st.columns([1.2, 1.2, 3])
c1.link_button("Mở toàn màn hình", led_url, type="primary", width="stretch")
c2.link_button("Mở kèm bảng debug", f"{led_url}?debug=1", width="stretch")
components.iframe(led_url, height=620)

note("Trên máy đặt ở đầu cầu: mở <code>" + led_url + "</code> bằng Chrome hoặc Edge rồi nhấn <b>F11</b>. "
     "Nếu máy LED khác máy chủ, thay <code>127.0.0.1</code> bằng địa chỉ IP của máy chủ. "
     "Thêm <code>?scene=3</code> để khóa một cảnh, <code>?debug=1</code> (hoặc phím <b>D</b>) để mở bảng giả lập "
     "Xanh / Vàng / Đỏ khi trình diễn. Đồng hồ và lịch đổi cảnh ngày/đêm theo giờ Việt Nam của máy chủ.")
