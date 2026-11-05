"""
frontend/views/tong_quan.py  —  MODULE M6 · F5.1 Dashboard truc tiep (FR-10, AC-06.1, NFR-01, FR-17)
Phu trach: KHANH.
So do cau truc tiep, muc canh bao, xu huong 5 phut, du kien bao lau day cau,
thoi gian cho (FR-17), dien bien 60 phut, du bao luot vao trong ngay, nhan dinh
tu dong, su co dang mo, trang thai camera. Phan truc tiep tu cap nhat 2 giay.
"""

import pandas as pd
import streamlit as st

from common import (C, GENDER_VI, HAS_PLOTLY, STATUS_META, alert_box, badge, bridge_svg, empty, fmt_duration,
                    fmt_int, fmt_time, insight_list, kpi, kpi_row, page_header, safe_get, section, status_badge,
                    style_fig, to_local)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Vận hành · Thời gian thực", "Tổng quan",
            "Tình hình Chùa Cầu lúc này, xu hướng vài phút tới và dự báo trong ngày. Phần trực tiếp tự cập nhật mỗi 2 giây.")


@st.fragment(run_every=2)
def live():
    cur = safe_get("/stats/current")
    cfg = safe_get("/config")
    lv = safe_get("/insights/live")
    if cur is None or cfg is None or lv is None:
        return
    count, maximum = cur["current_count"], cfg["alert_threshold"]
    status = cur["current_status"]
    tone = STATUS_META.get(status, STATUS_META["OK"])["tone"]

    if status == "CRITICAL":
        alert_box(f"<b>QUÁ TẢI</b> &nbsp;·&nbsp; {count} người trên cầu, vượt sức chứa {maximum}. "
                  "Tạm dừng cho khách lên cầu và xác nhận xử lý ở trang Trực ca."
                  + (f" Thời gian chờ dự kiến: <b>{lv['wait_label']}</b>." if lv["wait_label"] else ""))
    elif status in ("WARNING", "ALERT"):
        alert_box(f"<b>CẦU SẮP ĐẦY</b> &nbsp;·&nbsp; {count}/{maximum} người. Nhắc khách đi chậm, không dừng lại trên cầu.", "warn")
    elif lv["minutes_to_full"] is not None and lv["minutes_to_full"] <= 5:
        alert_box(f"<b>DỰ BÁO</b> &nbsp;·&nbsp; Với tốc độ hiện tại, cầu sẽ chạm sức chứa sau khoảng "
                  f"{lv['minutes_to_full']:.0f} phút. Cân nhắc điều tiết sớm.", "warn")
    if not cfg["is_open_now"]:
        alert_box(f"Ngoài giờ hoạt động ({cfg['open_time']}–{cfg['close_time']}). Cảnh báo Vàng tạm không gửi tin nhắn.", "info")

    left, right = st.columns([1.45, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown('<div class="sc-eyebrow">Trên cầu lúc này</div>', unsafe_allow_html=True)
            st.markdown(bridge_svg(count, maximum, status, lv["in_per_min"], lv["out_per_min"]), unsafe_allow_html=True)
            st.markdown(status_badge(status) + "&nbsp; " +
                        badge(f"Xu hướng 5 phút: {lv['trend']} ({lv['net_per_min']:+.1f}/phút)".replace(".", ","),
                              "warn" if lv["trend"] == "tăng" else "ok" if lv["trend"] == "giảm" else "muted"),
                        unsafe_allow_html=True)
    with right:
        to_full = lv["minutes_to_full"]
        kpi_row([kpi("Đang trên cầu", f"{count}<small> / {maximum}</small>",
                     f"Vàng từ {cfg['warning_threshold']} · Đỏ khi vượt {maximum} liên tục 15 giây", tone)])
        kpi_row([
            kpi("Đầy cầu sau", "–" if to_full is None else f"{to_full:.0f}<small> phút</small>",
                "nếu giữ tốc độ hiện tại" if to_full is not None else "khách không tăng",
                "warn" if to_full is not None and to_full <= 10 else ""),
            kpi("Thời gian chờ", lv["wait_label"] or "Không chờ", "khi cầu đầy",
                "danger" if lv["wait_label"] else "ok"),
        ])
    st.caption(("Chưa nhận được mức cảnh báo từ camera chân cầu 1 trong 30 giây qua." if cur["status_stale"] else
                f"Cập nhật {fmt_time(cur['last_update'], '%H:%M:%S')}"))

    kpi_row([
        kpi("Lượt vào cầu hôm nay", fmt_int(cur["entries_today"]),
            f"{'+' if (lv['today_vs_usual'] or 1) >= 1 else ''}{round(((lv['today_vs_usual'] or 1) - 1) * 100)}% so với ngày thường"
            if lv["today_vs_usual"] else "hai camera chân cầu", "primary"),
        kpi("Dự kiến cả ngày", fmt_int((cur["entries_today"] or 0) + (lv["expected_rest_of_day"] or 0))
            if lv["expected_rest_of_day"] is not None else "–",
            f"cao điểm còn lại {lv['expected_peak']['hour']}h" if lv["expected_peak"] else "cần ≥ 1 tuần dữ liệu", "info"),
        kpi("Lượt qua mặt tiền", fmt_int(cur["facade_today"]), "đi ngang, không lên cầu", "info"),
        kpi("Sự cố đang mở", fmt_int(cur["open_incidents"]),
            "cần xác nhận xử lý" if cur["open_incidents"] else "không có sự cố",
            "danger" if cur["open_incidents"] else "ok"),
    ])

    c1, c2 = st.columns([2.1, 1], gap="large")
    with c1:
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
            fig.add_hline(y=maximum, line=dict(color=C["danger"], dash="dash", width=1), annotation_position="top left",
                          annotation_text=f"Sức chứa {maximum}", annotation_font_color=C["danger"])
            fig.add_hline(y=cfg["warning_threshold"], line=dict(color=C["gold"], dash="dot", width=1),
                          annotation_position="bottom left", annotation_text=f"Vàng {cfg['warning_threshold']}",
                          annotation_font_color=C["gold"])
            fig.update_xaxes(tickformat="%H:%M")
            st.plotly_chart(style_fig(fig, 280, legend=False), width="stretch", key="occ")
    with c2:
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
        g = cur.get("gender_today") or {}
        if g:
            st.markdown('<div class="sc-eyebrow" style="margin-top:14px">Khách vào hôm nay</div>' +
                        " ".join(badge(f"{GENDER_VI.get(k, k)} {v}", "muted") for k, v in g.items()), unsafe_allow_html=True)


live()


@st.fragment(run_every=60)
def outlook():
    lv = safe_get("/insights/live")
    ins = safe_get("/insights/summary")
    if lv is None or ins is None:
        return
    c1, c2 = st.columns([2.1, 1], gap="large")
    with c1:
        section("Lượt vào theo giờ hôm nay", "thực tế, ngày thường và dự báo")
        if not lv["forecast"]:
            empty("Cần ít nhất một tuần dữ liệu cùng thứ để dự báo.")
        elif HAS_PLOTLY:
            f = pd.DataFrame(lv["forecast"])
            f = f[(f["hour"] >= 6) & (f["hour"] <= 23)]
            now_h = int(lv["now"][11:13])
            fut = f[f["hour"] >= now_h]
            fig = go.Figure()
            fig.add_bar(x=f["hour"], y=f["actual"], name="Hôm nay", marker_color=C["oxblood"],
                        hovertemplate="%{x}h · %{y} lượt<extra>Hôm nay</extra>")
            fig.add_scatter(x=f["hour"], y=f["usual"], name=f"Trung bình {lv['history_days']} tuần, cùng thứ",
                            mode="lines", line=dict(color=C["stone"], width=1.5, dash="dot"),
                            hovertemplate="%{x}h · %{y} lượt<extra>Ngày thường</extra>")
            fig.add_scatter(x=fut["hour"], y=fut["expected"], name="Dự báo", mode="lines+markers",
                            line=dict(color=C["gold"], width=2), marker=dict(size=5),
                            hovertemplate="%{x}h · khoảng %{y} lượt<extra>Dự báo</extra>")
            if 6 <= now_h <= 23:
                fig.add_vline(x=now_h - 0.5 + int(lv["now"][14:16]) / 60, line=dict(color=C["muted"], width=1, dash="dash"),
                              annotation_text="bây giờ", annotation_font_color=C["muted"])
            fig.update_xaxes(dtick=1, ticksuffix="h")
            st.plotly_chart(style_fig(fig, 300), width="stretch", key="fc")
    with c2:
        section("Nhận định tự động")
        insight_list(ins["items"])


outlook()
