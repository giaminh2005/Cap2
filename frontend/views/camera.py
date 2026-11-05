"""
frontend/views/camera.py  —  MODULE M1 · F1.1 Thiet lap nguon hinh (FR-01, NFR-03)
Phu trach: MINH.
Trang thai 2 camera chan cau (nhip tim moi 5 giay; > 30 giay khong thay ->
mat tin hieu), nguon hinh, toc do xu ly, vach ke dang dung. Cach chay camera: docs/GHI_CHU_GIAO_DIEN.md.
"""

import streamlit as st

from common import badge, fmt_time, page_header, safe_get

page_header("Hệ thống · Nguồn hình", "Camera", "Trạng thái hai camera chân cầu, tự cập nhật mỗi 5 giây.")


@st.fragment(run_every=5)
def cams():
    rows = safe_get("/bridge/cameras")
    if rows is None:
        return
    cols = st.columns(2)
    for col, c in zip(cols, rows):
        with col, st.container(border=True):
            st.markdown(f'<div class="sc-eyebrow">Chân cầu {c["camera_id"]}</div>'
                        f'<div class="sc-title" style="font-size:1.7rem">Camera {c["camera_id"]}</div>', unsafe_allow_html=True)
            if c["online"]:
                st.markdown(badge(f"Đang hoạt động · {c['fps']} khung hình/giây", "ok"), unsafe_allow_html=True)
            elif c["last_seen"]:
                st.markdown(badge(f"Mất tín hiệu từ {fmt_time(c['last_seen'], '%H:%M:%S %d/%m')}", "danger"),
                            unsafe_allow_html=True)
            else:
                st.markdown(badge("Chưa từng kết nối", "muted"), unsafe_allow_html=True)
            st.markdown(f"""
- **Máy chạy camera:** {c.get('machine') or '–'}
- **Nguồn hình:** `{c['source'] or '–'}`
- **Vạch kẻ:** {c['line'] or '–'}
- **Gửi mức cảnh báo:** {'Có' if c['sends_alerts'] else 'Không'}
- **Nhận diện giới tính / tuổi / nguồn khách:** {'Bật' if c['demographics'] else 'Tắt'}
- **Chạy từ:** {fmt_time(c['started_at'], '%H:%M %d/%m/%Y')}
""")


cams()
