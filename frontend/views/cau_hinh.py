"""
frontend/views/cau_hinh.py  —  MODULE M7 · F6.2 Cau hinh nguong + khung gio (FR-13, BRULE-01, BRULE-07)
Phu trach: KHANH.
"""

from datetime import time

import pandas as pd
import streamlit as st

from common import ApiError, api_put, fmt_time, kpi, kpi_row, note, page_header, safe_get

page_header("⚙️", "Ngưỡng & giờ hoạt động", "Chỉ quản trị viên được thay đổi · mọi thay đổi đều được ghi nhật ký")

cfg = safe_get("/config")
if cfg is None:
    st.stop()

kpi_row([
    kpi("Sức chứa tối đa", f"{cfg['alert_threshold']} người", "Đỏ khi vượt liên tục 15 giây", "danger"),
    kpi("Ngưỡng Vàng", f"{cfg['warning_threshold']} người", "= 75% sức chứa", "warn"),
    kpi("Giờ hoạt động", f"{cfg['open_time']}–{cfg['close_time']}", "Đang mở cửa" if cfg["is_open_now"] else "Ngoài giờ",
        "ok" if cfg["is_open_now"] else "muted"),
])
st.caption(f"Cập nhật lần cuối: {fmt_time(cfg['updated_at'])}" + (f" bởi {cfg['updated_by']}" if cfg["updated_by"] else ""))


def _t(s):
    h, m = s.split(":")
    return time(int(h), int(m))


with st.form("cfg"):
    c1, c2, c3 = st.columns(3)
    cap = c1.number_input("Sức chứa tối đa trên cầu (người)", 1, 500, int(cfg["alert_threshold"]),
                          help="Quy định năm 2019: mỗi lượt không quá 20 người (BRULE-01)")
    open_t = c2.time_input("Giờ mở cửa", _t(cfg["open_time"]), step=900)
    close_t = c3.time_input("Giờ đóng cửa", _t(cfg["close_time"]), step=900)
    st.caption(f"Với sức chứa {cap}: Vàng từ {min(cap, max(1, round(cap * 0.75)))} người, Đỏ khi trên {cap} người liên tục 15 giây. "
               "Camera áp dụng ngưỡng mới trong vòng 15 giây.")
    if st.form_submit_button("Lưu thay đổi", type="primary"):
        try:
            api_put("/config", {"alert_threshold": int(cap), "open_time": open_t.strftime("%H:%M"),
                                "close_time": close_t.strftime("%H:%M")})
            st.success("Đã lưu cấu hình.")
            st.rerun()
        except ApiError as e:
            st.error(str(e))

note("Ngoài giờ hoạt động hệ thống không gửi tin nhắn cảnh báo Vàng và đoàn khách; "
     "cảnh báo Đỏ và mất tín hiệu camera vẫn luôn được gửi.")

st.markdown("#### Nhật ký thay đổi")
log = safe_get("/audit", {"limit": 300}) or []
if log:
    st.dataframe(pd.DataFrame([{"Thời gian": fmt_time(e["timestamp"]), "Người thực hiện": e["username"],
                                "Thao tác": e["action"], "Chi tiết": e["detail"]} for e in log]),
                 hide_index=True, width="stretch", height=360)
else:
    st.caption("Chưa có thay đổi nào.")
