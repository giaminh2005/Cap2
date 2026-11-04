"""
frontend/views/tong_quan.py  —  MODULE M6 · F5.1 Dashboard truc tiep (FR-10, AC-06.1)
Phu trach: KHANH.
So nguoi hien tai, muc canh bao, dien bien 60 phut, su co dang mo, 3 bo dem
tach rieng (tren cau / luot vao hom nay / luot mat tien). Tu cap nhat 3 giay.
"""

import pandas as pd
import streamlit as st

from common import (COLORS, GENDER_VI, HAS_PLOTLY, STATUS_META, alert_box, badge, capacity_bar, fmt_duration,
                    fmt_int, fmt_time, kpi, kpi_row, page_header, safe_get, status_badge, style_fig, to_local)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("🏯", "Tổng quan", "Tình hình Chùa Cầu theo thời gian thực · tự cập nhật mỗi 3 giây")


@st.fragment(run_every=3)
def live():
    cur = safe_get("/stats/current")
    cfg = safe_get("/config")
    if cur is None or cfg is None:
        return
    count, maximum = cur["current_count"], cfg["alert_threshold"]
    status = cur["current_status"]
    meta = STATUS_META.get(status, STATUS_META["OK"])

    if status == "CRITICAL":
        alert_box(f"⛔ QUÁ TẢI: {count} người trên cầu (tối đa {maximum}). Tạm dừng cho khách lên cầu và xử lý sự cố.")
    elif status in ("WARNING", "ALERT"):
        alert_box(f"▲ Cầu sắp đầy: {count}/{maximum} người. Điều tiết khách đi chậm, không dừng lại trên cầu.", "warn")
    if not cfg["is_open_now"]:
        alert_box(f"Ngoài giờ hoạt động ({cfg['open_time']}–{cfg['close_time']}). Cảnh báo Vàng tạm không gửi tin nhắn.", "info")

    kpi_row([
        kpi("Đang trên cầu", f"{count}<span style='font-size:1rem;color:var(--muted)'> / {maximum}</span>",
            status_badge(status), meta["tone"]),
        kpi("Lượt vào cầu hôm nay", fmt_int(cur["entries_today"]), "đếm bởi 2 camera chân cầu", "primary"),
        kpi("Lượt qua mặt tiền", fmt_int(cur["facade_today"]), "đi ngang, không lên cầu", "info"),
        kpi("Sự cố đang mở", fmt_int(cur["open_incidents"]),
            "cần xác nhận ở trang Trực ca" if cur["open_incidents"] else "không có sự cố",
            "danger" if cur["open_incidents"] else "ok"),
    ])
    capacity_bar(count, maximum)
    if cur["status_stale"]:
        st.caption("Chưa nhận được mức cảnh báo từ camera 1 trong 30 giây qua — kiểm tra trang Camera.")
    else:
        st.caption(f"Cập nhật lúc {fmt_time(cur['last_update'], '%H:%M:%S')} · Vàng từ {cfg['warning_threshold']} người, "
                   f"Đỏ khi vượt {maximum} người liên tục 15 giây")

    left, right = st.columns([2, 1])
    with left, st.container(border=True):
        st.markdown("**Diễn biến số người trên cầu · 60 phút gần nhất**")
        hist = safe_get("/stats/occupancy/history", {"minutes": 60}) or []
        if not hist:
            st.info("Chưa có dữ liệu. Biểu đồ sẽ hiện khi camera chân cầu 1 chạy.")
        elif HAS_PLOTLY:
            df = pd.DataFrame(hist)
            df["time"] = df["timestamp"].map(to_local)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df["time"], y=df["count"], mode="lines", line=dict(color=COLORS["primary"], width=2.5),
                                     fill="tozeroy", fillcolor="rgba(142,42,31,.10)", name="Số người"))
            fig.add_hline(y=maximum, line=dict(color=COLORS["danger"], dash="dash"), annotation_text=f"Tối đa {maximum}")
            fig.add_hline(y=cfg["warning_threshold"], line=dict(color=COLORS["warn"], dash="dot"),
                          annotation_text=f"Vàng {cfg['warning_threshold']}")
            st.plotly_chart(style_fig(fig, 300, legend=False), width="stretch")
        else:
            st.line_chart(pd.DataFrame(hist).set_index("timestamp")["count"])

    with right:
        with st.container(border=True):
            st.markdown("**Sự cố đang mở**")
            incidents = safe_get("/incidents", {"status": "open"}) or []
            if not incidents:
                st.markdown(badge("✓ Không có sự cố", "ok"), unsafe_allow_html=True)
            for i in incidents:
                st.markdown(f'<div class="sc-incident"><b>Sự cố #{i["id"]}</b> · cao nhất {i["peak_count"]} người<br>'
                            f'<span style="color:var(--muted);font-size:.85rem">Từ {fmt_time(i["opened_at"], "%H:%M:%S")} · '
                            f'{fmt_duration(i["duration_seconds"])} · '
                            f'{"đã xác nhận bởi " + i["acked_by"] if i["acknowledged"] else "chưa xác nhận"}</span></div>',
                            unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**Camera chân cầu**")
            for c in safe_get("/bridge/cameras") or []:
                tone = "ok" if c["online"] else "danger"
                txt = f"Camera {c['camera_id']} · {'hoạt động · ' + str(c['fps']) + ' khung/giây' if c['online'] else 'mất tín hiệu'}"
                st.markdown(badge(("● " if c["online"] else "■ ") + txt, tone), unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("**Khách vào hôm nay theo giới tính**")
            g = cur.get("gender_today") or {}
            if g:
                st.markdown(" ".join(badge(f"{GENDER_VI.get(k, k)}: {v}", "info") for k, v in g.items()),
                            unsafe_allow_html=True)
            else:
                st.caption("Chưa có hồ sơ nhận diện hôm nay.")


live()
