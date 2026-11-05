"""
frontend/views/doi_chieu_ve.py  —  MODULE M5 · F4.1, F4.2 (FR-14, BRULE-08)
Phu trach: HOAN.
Nhap so cuong ve thu tai Chua Cau (theo ngay hoac theo gio, nhap tay hoac
tu tep CSV/Excel) va so voi luot vao long cau do 2 camera dem.
"""

import pandas as pd
import streamlit as st

from common import (COLORS, HAS_PLOTLY, ApiError, api_delete, api_post, fmt_int, fmt_time, kpi, kpi_row,
                    local_now, local_today, page_header, safe_get, style_fig)

if HAS_PLOTLY:
    import plotly.graph_objects as go

page_header("Vận hành · Bộ phận soát vé", "Đối chiếu vé", "So sánh số cuống vé thu tại Chùa Cầu với lượt vào lòng cầu do camera đếm.")

day = st.date_input("Ngày đối chiếu", value=local_today(), max_value=local_today(), format="DD/MM/YYYY")
day_s = day.isoformat()

cfg = safe_get("/config") or {}
open_h = int((cfg.get("open_time") or "07:00")[:2])
close_h = int((cfg.get("close_time") or "21:30")[:2])
OPEN_HOURS = list(range(open_h, close_h + 1)) or list(range(24))
existing = {t["hour"]: t["ticket_count"] for t in (safe_get("/tickets", {"date_from": day_s, "date_to": day_s}) or [])}

left, right = st.columns([1, 1])
with left, st.container(border=True):
    st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Nhập số cuống vé</div>', unsafe_allow_html=True)
    # Radio nam NGOAI form -> doi lua chon la giao dien doi ngay (o gio chi hien khi nhap tung gio)
    mode = st.segmented_control("Nhập theo", ["Cả ngày", "Từng giờ"], default="Cả ngày", key="tk_mode")
    hour = None
    if mode == "Từng giờ":
        hour = st.selectbox("Khung giờ", OPEN_HOURS, format_func=lambda h: f"{h:02d}:00 – {h + 1:02d}:00"
                            + (f"  ·  đã nhập {existing[h]} vé" if h in existing else ""),
                            index=min(max(0, local_now().hour - OPEN_HOURS[0]), len(OPEN_HOURS) - 1)
                            if day == local_today() else 0)
    cur = existing.get(hour)
    count = st.number_input("Số cuống vé", 0, 100000, int(cur or 0), step=10, key=f"tk_count_{day_s}_{hour}")
    if cur is not None:
        st.caption(f"Đã nhập {fmt_int(cur)} vé cho {'cả ngày' if hour is None else f'khung {hour:02d}h'}; lưu lại sẽ ghi đè.")
    if st.button("Lưu", type="primary"):
        try:
            api_post("/tickets", {"date": day_s, "hour": hour, "ticket_count": int(count)})
            st.toast("Đã lưu số cuống vé.", icon=":material/check_circle:")
            st.rerun()
        except ApiError as e:
            st.error(str(e))


def template_df(kind: str) -> pd.DataFrame:
    """Tep mau: ca ngay = 1 dong; tung gio = moi gio mo cua 1 dong. Cot ticket_count de trong de dien."""
    if kind == "day":
        return pd.DataFrame({"date": [day_s], "hour": [None], "ticket_count": [None]})
    return pd.DataFrame({"date": [day_s] * len(OPEN_HOURS), "hour": OPEN_HOURS, "ticket_count": [None] * len(OPEN_HOURS)})


def to_xlsx(df: pd.DataFrame) -> bytes:
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name="so_cuong_ve")
        ws = w.sheets["so_cuong_ve"]
        for col, width in (("A", 14), ("B", 8), ("C", 14)):
            ws.column_dimensions[col].width = width
    return buf.getvalue()


with right, st.container(border=True):
    st.markdown('<div class="sc-eyebrow" style="margin-bottom:6px">Nhập từ tệp CSV / Excel</div>', unsafe_allow_html=True)
    kind = st.radio("Tệp mẫu", ["Từng giờ", "Cả ngày"], horizontal=True, key="tpl_kind")
    tpl = template_df("hour" if kind == "Từng giờ" else "day")
    d1, d2 = st.columns(2)
    d1.download_button("Tải mẫu Excel", to_xlsx(tpl), f"mau_so_cuong_ve_{day_s}.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       icon=":material/download:", width="stretch")
    d2.download_button("Tải mẫu CSV", tpl.to_csv(index=False).encode("utf-8-sig"), f"mau_so_cuong_ve_{day_s}.csv",
                       "text/csv", icon=":material/download:", width="stretch")
    up = st.file_uploader("Chọn tệp đã điền", type=["csv", "xlsx"],
                          help="Điền cột ticket_count rồi tải lên. Dòng để trống ticket_count sẽ bỏ qua.")
    if up is not None:
        try:
            df_up = pd.read_csv(up) if up.name.endswith(".csv") else pd.read_excel(up)
            df_up.columns = [str(c).strip().lower() for c in df_up.columns]
            df_up = df_up[df_up["ticket_count"].notna()]
            items = [{"date": str(r["date"])[:10],
                      "hour": None if "hour" not in df_up or pd.isna(r.get("hour")) else int(r["hour"]),
                      "ticket_count": int(r["ticket_count"])} for _, r in df_up.iterrows()]
            if not items:
                st.warning("Tệp chưa có dòng nào điền số vé.")
            else:
                prev = pd.DataFrame(items)
                prev["hour"] = prev["hour"].map(lambda h: "Cả ngày" if h is None or pd.isna(h) else f"{int(h):02d}h")
                st.dataframe(prev.rename(columns={"date": "Ngày", "hour": "Giờ", "ticket_count": "Số vé"}),
                             hide_index=True, width="stretch", height=min(300, 38 + 35 * len(prev)))
                if st.button(f"Nhập {len(items)} dòng · tổng {sum(i['ticket_count'] for i in items):,} vé".replace(",", "."),
                             type="primary"):
                    api_post("/tickets/bulk", items)
                    st.toast(f"Đã nhập {len(items)} dòng.", icon=":material/check_circle:")
        except (KeyError, ValueError) as e:
            st.error(f"Tệp không đúng định dạng (cần cột date, hour, ticket_count): {e}")
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
