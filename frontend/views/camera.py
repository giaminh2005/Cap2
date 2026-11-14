"""
frontend/views/camera.py  —  MODULE M1 · F1.1 Nguon hinh & hinh truc tiep (FR-01, NFR-03)
Phu trach: MINH.
Moi chan cau 1 the: hinh truc tiep (luong MJPEG tu backend /bridge/stream/<id>, camera gui len khi chay
camera_bridge.py khong co --no-stream), trang thai nhip tim (> 30 giay khong thay -> mat tin hieu) va thong so.
Trang thai tu cap nhat moi 5 giay; the <img> giu nguyen nen luong hinh khong bi ngat.
Chi quan ly / quan tri xem duoc hinh (token dang nhap gan tren URL luong hinh).
Cach chay camera: docs/CAMERA_NGOAI.md, docs/GHI_CHU_GIAO_DIEN.md.
"""

from urllib.parse import quote

import streamlit as st

from common import badge, fmt_time, page_header, public_api_base, safe_get

page_header("Hệ thống · Nguồn hình", "Camera",
            "Hình ảnh trực tiếp và trạng thái hai camera chân cầu. Trạng thái tự cập nhật mỗi 5 giây.")

BASE = public_api_base()
TOKEN = quote(st.session_state.get("token") or "")
CAM_ICON = ('<svg viewBox="0 0 24 24" fill="none" stroke="#776B5F" stroke-width="1.5" stroke-linecap="round" '
            'stroke-linejoin="round"><path d="M15 10l5-3v10l-5-3"/><rect x="3" y="6" width="12" height="12" rx="1"/>'
            '<path d="M3 3l18 18"/></svg>')

view = st.segmented_control("Hiển thị", ["Song song", "Chân cầu 1", "Chân cầu 2"], default="Song song",
                            label_visibility="collapsed", key="cam_view")
shown = [1, 2] if view in (None, "Song song") else [1 if view == "Chân cầu 1" else 2]


def stream_url(cid: int) -> str:
    return f"{BASE}/bridge/stream/{cid}?t={TOKEN}"


def status(c: dict):
    if c["online"]:
        return badge(f"Đang hoạt động · {c['fps']} khung hình/giây", "ok")
    if c.get("last_seen"):
        return badge(f"Mất tín hiệu từ {fmt_time(c['last_seen'], '%H:%M:%S %d/%m')}", "danger")
    return badge("Chưa từng kết nối", "muted")


def video(c: dict) -> str:
    cid = c["camera_id"]
    if c.get("has_stream"):
        return (f'<div class="sc-live"><span class="tag">Trực tiếp</span>'
                f'<span class="full"><a href="{stream_url(cid)}" target="_blank">Mở toàn màn hình ↗</a></span>'
                f'<img src="{stream_url(cid)}" alt="Hình trực tiếp camera {cid}"></div>')
    if c["online"]:
        text, sub = "Camera đang chạy nhưng không gửi hình lên web", "Camera được bật với tùy chọn không phát hình"
    elif c.get("last_seen"):
        text, sub = "Không nhận được hình", f"Lần cuối thấy camera lúc {fmt_time(c['last_seen'], '%H:%M:%S %d/%m')}"
    else:
        text, sub = "Chưa có hình", "Camera chân cầu này chưa kết nối với máy chủ"
    return f'<div class="sc-live off">{CAM_ICON}<div class="t">{text}</div><div class="m">{sub}</div></div>'


def specs(c: dict, wide: bool = False) -> str:
    rows = [
        ("Máy chạy camera", c.get("machine") or "–"),
        ("Nguồn hình", c.get("source") or "–"),
        ("Vạch kẻ", c.get("line") or "–"),
        ("Gửi mức cảnh báo", "Có" if c.get("sends_alerts") else "Không"),
        ("Nhận diện giới tính, tuổi", "Bật" if c.get("demographics") else "Tắt"),
        ("Hình trực tiếp", "Đang phát" if c.get("has_stream") else "Không có"),
        ("Chạy từ", fmt_time(c.get("started_at"), "%H:%M %d/%m/%Y") if c.get("started_at") else "–"),
    ]
    cells = "".join(f'<span class="k">{k}</span><span class="v">{v}</span>' for k, v in rows)
    return f'<div class="sc-specs{" wide" if wide else ""}">{cells}</div>'


@st.fragment(run_every=5)
def board():
    rows = safe_get("/bridge/cameras")
    if rows is None:
        return
    by_id = {c["camera_id"]: c for c in rows}
    for col, cid in zip(st.columns(len(shown), gap="medium"), shown):
        c = by_id.get(cid, {"camera_id": cid, "online": False})
        with col, st.container(border=True):
            st.markdown(f'<div class="sc-eyebrow">Chân cầu {cid}</div>'
                        f'<div class="sc-title" style="font-size:1.7rem">Camera {cid}</div>{status(c)}',
                        unsafe_allow_html=True)
            st.markdown(video(c), unsafe_allow_html=True)
            st.markdown(specs(c, wide=len(shown) == 1), unsafe_allow_html=True)   # 1 camera: thong so 2 cot


board()
