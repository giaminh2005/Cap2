"""
frontend/views/tong_quan.py  —  MODULE M6 · F5.1 Dashboard truc tiep (FR-10, AC-06.1, NFR-01)
Phu trach: KHANH.
So nguoi hien tai, muc canh bao, dien bien 60 phut, su co dang mo, 3 bo dem
tach rieng (tren cau / luot vao hom nay / luot mat tien). Tu cap nhat 2 giay.
"""

import pandas as pd
import streamlit as st

from common import (C, GENDER_VI, HAS_PLOTLY, STATUS_META, alert_box, badge, capacity_bar, empty, fmt_duration,
                    fmt_int, fmt_time, kpi, kpi_row, page_header, safe_get, section, status_badge, style_fig, to_local)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Vận hành · Thời gian thực", "Tổng quan", "Tình hình Chùa Cầu lúc này. Số liệu tự cập nhật mỗi 2 giây.")


@st.fragment(run_every=2)
def live():
    cur = safe_get("/stats/current")
    cfg = safe_get("/config")
    if cur is None or cfg is None:
        return
    count, maximum = cur["current_count"], cfg["alert_threshold"]
    status = cur["current_status"]
    tone = STATUS_META.get(status, STATUS_META["OK"])["tone"]

    if status == "CRITICAL":
        alert_box(f"<b>QUÁ TẢI</b> &nbsp;·&nbsp; {count} người trên cầu, vượt sức chứa {maximum}. "
                  "Tạm dừng cho khách lên cầu và xác nhận xử lý ở trang Trực ca.")
    elif status in ("WARNING", "ALERT"):
        alert_box(f"<b>CẦU SẮP ĐẦY</b> &nbsp;·&nbsp; {count}/{maximum} người. Nhắc khách đi chậm, không dừng lại trên cầu.", "warn")
    if not cfg["is_open_now"]:
        alert_box(f"Ngoài giờ hoạt động ({cfg['open_time']}–{cfg['close_time']}). Cảnh báo Vàng tạm không gửi tin nhắn.", "info")

    kpi_row([
        kpi("Đang trên cầu", f"{count}<small> / {maximum}</small>", status_badge(status), tone),
        kpi("Lượt vào cầu hôm nay", fmt_int(cur["entries_today"]), "hai camera chân cầu", "primary"),
        kpi("Lượt qua mặt tiền", fmt_int(cur["facade_today"]), "đi ngang, không lên cầu", "info"),
        kpi("Sự cố đang mở", fmt_int(cur["open_incidents"]),
            "cần xác nhận xử lý" if cur["open_incidents"] else "không có sự cố",
            "danger" if cur["open_incidents"] else "ok"),
    ])
    capacity_bar(count, maximum, cfg["warning_threshold"])
    st.caption(("Chưa nhận được mức cảnh báo từ camera chân cầu 1 trong 30 giây qua." if cur["status_stale"] else
                f"Cập nhật {fmt_time(cur['last_update'], '%H:%M:%S')}") +
               f" · Vàng từ {cfg['warning_threshold']} người · Đỏ khi vượt {maximum} người liên tục 15 giây")

    left, right = st.columns([2.1, 1], gap="large")
    with left:
        section("Diễn biến số người trên cầu", "60 phút gần nhất")
        hist = safe_get("/stats/occupancy/history", {"minutes": 60}) or []
        if not hist:
            empty("Chưa có dữ liệu. Biểu đồ sẽ hiện khi camera chân cầu 1 hoạt động.")
        elif HAS_PLOTLY:
            df = pd.DataFrame(hist)
            df["time"] = df["timestamp"].map(to_local)
            fig = go.Figure(go.Scatter(x=df["time"], y=df["count"], mode="lines", line=dict(color=C["oxblood"], width=1.8),
                                       fill="tozeroy", fillcolor="rgba(125,35,24,.07)", name="Số người",
                                       hovertemplate="%{x|%H:%M:%S} · %{y} người<extra></extra>"))
            fig.add_hline(y=maximum, line=dict(color=C["danger"], dash="dash", width=1),
                          annotation_text=f"Sức chứa {maximum}", annotation_position="top left", annotation_font_color=C["danger"])
            fig.add_hline(y=cfg["warning_threshold"], line=dict(color=C["gold"], dash="dot", width=1),
                          annotation_text=f"Vàng {cfg['warning_threshold']}", annotation_position="bottom left", annotation_font_color=C["gold"])
            fig.update_xaxes(tickformat="%H:%M")
            st.plotly_chart(style_fig(fig, 300, legend=False), width="stretch")

    with right:
        section("Sự cố đang mở")
        incidents = safe_get("/incidents", {"status": "open"}) or []
        if not incidents:
            empty("Không có sự cố.")
        for i in incidents:
            st.markdown(f'<div class="sc-item danger"><div class="t">Sự cố #{i["id"]} · cao nhất {i["peak_count"]} người</div>'
                        f'<div class="m">Từ {fmt_time(i["opened_at"], "%H:%M:%S")} · {fmt_duration(i["duration_seconds"])} · '
                        f'{"xác nhận bởi " + i["acked_by"] if i["acknowledged"] else "chưa xác nhận"}</div></div>',
                        unsafe_allow_html=True)
        section("Camera chân cầu")
        for c in safe_get("/bridge/cameras") or []:
            st.markdown(f'<div class="sc-item"><div class="t">Camera {c["camera_id"]}</div><div class="m">' +
                        (badge(f"Hoạt động · {c['fps']} khung/giây", "ok") if c["online"] else badge("Mất tín hiệu", "danger"))
                        + "</div></div>", unsafe_allow_html=True)
        section("Khách vào hôm nay")
        g = cur.get("gender_today") or {}
        if g:
            st.markdown(" ".join(badge(f"{GENDER_VI.get(k, k)} {v}", "muted") for k, v in g.items()), unsafe_allow_html=True)
        else:
            empty("Chưa có hồ sơ nhận diện.")


live()
