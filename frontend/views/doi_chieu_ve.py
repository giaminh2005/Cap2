"""
frontend/views/doi_chieu_ve.py  —  MODULE M5 · F4.1, F4.2 (FR-14, BRULE-08)
Phu trach: HOAN.
Nhap so cuong ve thu tai Chua Cau (theo ngay hoac theo gio, nhap tay hoac
tu tep CSV/Excel) va so voi luot vao long cau do 2 camera dem.
"""

import pandas as pd
import streamlit as st

from common import (COLORS, HAS_PLOTLY, ApiError, api_delete, api_post, fmt_int, fmt_time, kpi, kpi_row,
                    local_today, note, page_header, safe_get, style_fig)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Vận hành · Bộ phận soát vé", "Đối chiếu vé", "So sánh số cuống vé thu tại Chùa Cầu với lượt vào lòng cầu do camera đếm.")
note("Theo BRULE-08: chỉ so <b>lượt vào lòng cầu</b> (2 camera chân cầu), không dùng lượt qua mặt tiền. "
     "Kết quả chỉ dùng để điều phối lực lượng soát vé, <b>không dùng làm bằng chứng xử phạt</b>. "
     "Tỷ lệ chênh lệch = (lượt vào − số vé) / lượt vào × 100%.")

day = st.date_input("Ngày đối chiếu", value=local_today(), format="DD/MM/YYYY")
day_s = day.isoformat()

left, right = st.columns([1, 1])
with left, st.container(border=True):
    st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Nhập số cuống vé</div>', unsafe_allow_html=True)
    with st.form("ticket", clear_on_submit=True):
        mode = st.radio("Nhập theo", ["Cả ngày", "Từng giờ"], horizontal=True)
        hour = st.number_input("Giờ (0–23)", 0, 23, 8, help="Chỉ dùng khi nhập theo từng giờ")
        count = st.number_input("Số cuống vé", 0, 100000, 0, step=10)
        ok = st.form_submit_button("Lưu", type="primary")
    if ok:
        try:
            api_post("/tickets", {"date": day_s, "hour": None if mode == "Cả ngày" else int(hour),
                                  "ticket_count": int(count)})
            st.success("Đã lưu. Nhập lại cùng ngày/giờ sẽ ghi đè số cũ.")
        except ApiError as e:
            st.error(str(e))

with right, st.container(border=True):
    st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Nhập từ tệp CSV / Excel</div>', unsafe_allow_html=True)
    st.caption("Các cột: `date` (YYYY-MM-DD), `hour` (để trống = cả ngày), `ticket_count`.")
    up = st.file_uploader("Chọn tệp", type=["csv", "xlsx"], label_visibility="collapsed")
    if up is not None:
        try:
            df_up = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
            df_up.columns = [c.strip().lower() for c in df_up.columns]
            items = [{"date": str(r["date"])[:10],
                      "hour": None if "hour" not in df_up or pd.isna(r.get("hour")) else int(r["hour"]),
                      "ticket_count": int(r["ticket_count"])} for _, r in df_up.iterrows()]
            st.dataframe(pd.DataFrame(items).head(10), hide_index=True, width="stretch")
            if st.button(f"Nhập {len(items)} dòng", type="primary"):
                api_post("/tickets/bulk", items)
                st.success(f"Đã nhập {len(items)} dòng.")
        except (KeyError, ValueError) as e:
            st.error(f"Tệp không đúng định dạng: {e}")
        except ApiError as e:
            st.error(str(e))

rec = safe_get("/tickets/reconciliation", {"date": day_s})
if rec is None:
    st.stop()

rate = rec["gap_rate_pct"]
kpi_row([
    kpi("Lượt vào lòng cầu", fmt_int(rec["entries_counted"]), "camera đếm", "primary"),
    kpi("Số cuống vé", fmt_int(rec["tickets_sold"]), "chưa nhập" if rec["tickets_sold"] is None else "", "info"),
    kpi("Chênh lệch", fmt_int(rec["gap"]),
        "lượt vào − số vé" if rec["mode"] == "day" else f"chỉ tính các giờ đã nhập vé ({fmt_int(rec['compared_entries'])} lượt vào)",
        "warn" if (rec["gap"] or 0) > 0 else "ok"),
    kpi("Tỷ lệ chênh lệch", "–" if rate is None else f"{rate:.1f}%", "",
        "danger" if (rate or 0) >= 10 else "warn" if (rate or 0) > 0 else "ok"),
])

rows = rec["by_hour"]
if rows:
    df = pd.DataFrame(rows)
    df["Giờ"] = df["hour"].map(lambda h: f"{h:02d}h")
    with st.container(border=True):
        st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Theo giờ trong ngày</div>', unsafe_allow_html=True)
        if HAS_PLOTLY:
            fig = go.Figure()
            fig.add_bar(x=df["Giờ"], y=df["entries"], name="Lượt vào cầu", marker_color=COLORS["primary"])
            if df["tickets"].notna().any():
                fig.add_bar(x=df["Giờ"], y=df["tickets"], name="Số cuống vé", marker_color=COLORS["ochre"])
            st.plotly_chart(style_fig(fig, 300), width="stretch")
        show = df[["Giờ", "entries", "tickets", "gap", "gap_rate_pct"]].astype(object).where(
            df[["Giờ", "entries", "tickets", "gap", "gap_rate_pct"]].notna(), "–").astype(str).rename(columns={
            "entries": "Lượt vào", "tickets": "Số vé", "gap": "Chênh lệch", "gap_rate_pct": "Tỷ lệ (%)"})
        st.dataframe(show, hide_index=True, width="stretch")
else:
    st.info("Chưa có lượt vào cầu nào trong ngày này.")

with st.expander("Số vé đã nhập trong ngày"):
    tickets = safe_get("/tickets", {"date_from": day_s, "date_to": day_s}) or []
    for t in tickets:
        c1, c2 = st.columns([5, 1])
        c1.write(f"**{'Cả ngày' if t['hour'] is None else str(t['hour']) + 'h'}**: {fmt_int(t['ticket_count'])} vé · "
                 f"nhập bởi {t['entered_by']} lúc {fmt_time(t['created_at'], '%H:%M %d/%m')}")
        if c2.button("Xóa", key=f"del{t['id']}"):
            try:
                api_delete(f"/tickets/{t['id']}")
                st.rerun()
            except ApiError as e:
                st.error(str(e))
    if not tickets:
        st.caption("Chưa nhập số vé cho ngày này.")
