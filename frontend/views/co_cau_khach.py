"""
frontend/views/co_cau_khach.py  —  MODULE M4 · F3.3 Tong hop co cau khach (FR-09, BRULE-06)
Phu trach: HOAN.
Ty le gioi tinh, nhom tuoi, trong nuoc / nuoc ngoai theo khoang ngay va theo
gio. Luot "Khong xac dinh" (do tin cay < 75%) dem rieng, khong vao ty le.
"""

from datetime import timedelta

import pandas as pd
import streamlit as st

from common import (AGE_ORDER, COLORS, HAS_PLOTLY, fmt_int, kpi, kpi_row, local_today, page_header,
                    safe_get, style_fig)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Phân tích · Du khách", "Cơ cấu khách", "Giới tính, nhóm tuổi và tỷ lệ khách trong nước/châu Á và quốc tế của khách vào cầu.")

today = local_today()
picked = st.date_input("Khoảng thời gian", value=(today - timedelta(days=6), today), format="DD/MM/YYYY")
if not isinstance(picked, (tuple, list)) or len(picked) != 2:
    st.info("Chọn ngày bắt đầu và ngày kết thúc.")
    st.stop()

d = safe_get("/stats/demographics", {"date_from": picked[0].isoformat(), "date_to": picked[1].isoformat()})
if d is None:
    st.stop()

ident = d["identified"]


def pct(n):
    return f"{n / ident * 100:.0f}%" if ident else "–"


kpi_row([
    kpi("Lượt khách có hồ sơ", fmt_int(d["total"]), "khách vào cầu", "primary"),
    kpi("Đã nhận diện", fmt_int(ident), f"{d['total'] and round(ident / d['total'] * 100)}% tổng số", "ok"),
    kpi("Không xác định", fmt_int(d["unknown"]), "độ tin cậy < 75%, không tính vào tỷ lệ", "muted"),
    kpi("Nữ / Nam", f"{pct(d['gender']['Woman'])} / {pct(d['gender']['Man'])}", "", "info"),
])

if not d["total"]:
    st.info("Chưa có hồ sơ khách nào trong khoảng thời gian này.")
    st.stop()


def donut(labels, values, colors, title):
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=.58, marker=dict(colors=colors),
                           textinfo="percent", sort=False))
    style_fig(fig, 300)
    fig.update_layout(legend=dict(orientation="h", y=-0.08, yanchor="top", x=0.5, xanchor="center"),
                      margin=dict(l=8, r=8, t=8, b=8))
    return fig


if HAS_PLOTLY:
    c1, c2, c3 = st.columns(3)
    with c1, st.container(border=True):
        st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Giới tính</div>', unsafe_allow_html=True)
        st.plotly_chart(donut(["Nữ", "Nam"], [d["gender"]["Woman"], d["gender"]["Man"]],
                              [COLORS["primary"], COLORS["blue"]], "Giới tính"), width="stretch")
    with c2, st.container(border=True):
        st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Trong nước/châu Á · Quốc tế · ước lượng</div>', unsafe_allow_html=True)
        o = d["origin"]
        unknown_origin = ident - o["Trong nuoc"] - o["Nuoc ngoai"]
        st.plotly_chart(donut(["Trong nước/châu Á", "Quốc tế", "Chưa rõ"], [o["Trong nuoc"], o["Nuoc ngoai"], unknown_origin],
                              [COLORS["moss"], COLORS["ochre"], "#CFC6BA"], "Nguồn khách"),
                        width="stretch")
    with c3, st.container(border=True):
        st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Nhóm tuổi</div>', unsafe_allow_html=True)
        ages = [a for a in AGE_ORDER if d["age_range"].get(a)]
        fig = go.Figure(go.Bar(x=[d["age_range"][a] for a in ages], y=ages, orientation="h",
                               marker_color=COLORS["ochre"]))
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(style_fig(fig, 300, legend=False), width="stretch")

    with st.container(border=True):
        st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Theo giờ trong ngày · gộp các ngày đã chọn</div>', unsafe_allow_html=True)
        h = pd.DataFrame(d["by_hour"])
        if not h.empty:
            h["Giờ"] = h["hour"].map(lambda x: f"{x:02d}h")
            fig = go.Figure()
            fig.add_bar(x=h["Giờ"], y=h["Woman"], name="Nữ", marker_color=COLORS["primary"])
            fig.add_bar(x=h["Giờ"], y=h["Man"], name="Nam", marker_color=COLORS["blue"])
            fig.add_bar(x=h["Giờ"], y=h["unknown"], name="Không xác định", marker_color="#CFC6BA")
            fig.update_layout(barmode="stack")
            st.plotly_chart(style_fig(fig, 320), width="stretch")
else:
    st.bar_chart(pd.Series(d["gender"]))

