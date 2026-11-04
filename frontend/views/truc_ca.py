"""
frontend/views/truc_ca.py  —  MODULE M3 · F2.4 Ghi nhan xu ly su co (FR-07, AC-04.1, AC-04.2)
Phu trach: HOAN.
Nguoi truc xac nhan "Da xu ly" bang 1 cham. Su co tu dong khi <= 15 nguoi
lien tuc 15 giay (camera bao CRITICAL_CLEARED). Tu cap nhat 3 giay.
"""

import pandas as pd
import streamlit as st

from common import (EVENT_TONE, ApiError, api_post, badge, fmt_duration, fmt_int, fmt_time, kpi, kpi_row,
                    page_header, safe_get)

page_header("🚨", "Trực ca & sự cố", "Xác nhận đã xử lý sự cố quá tải chỉ với một chạm")


@st.fragment(run_every=3)
def open_incidents():
    incidents = safe_get("/incidents", {"status": "open"})
    if incidents is None:
        return
    if not incidents:
        st.success("Không có sự cố quá tải nào đang mở.")
        return
    for i in incidents:
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1.3, 1])
            c1.markdown(f"### ⛔ Sự cố #{i['id']} · {i['peak_count']} người")
            c1.markdown(f"Bắt đầu **{fmt_time(i['opened_at'], '%H:%M:%S')}** · đã kéo dài **{fmt_duration(i['duration_seconds'])}** · "
                        f"{i['alert_count']} lần cảnh báo")
            if i["acknowledged"]:
                c1.markdown(badge(f"✓ Đã xác nhận bởi {i['acked_by']} sau {fmt_duration(i['handle_seconds'])}", "ok"),
                            unsafe_allow_html=True)
                c1.caption("Sự cố sẽ tự đóng khi trên cầu còn ≤ 15 người liên tục 15 giây.")
            note_txt = c2.text_input("Ghi chú (tùy chọn)", key=f"note{i['id']}", placeholder="vd: đã dừng đoàn tại đầu cầu")
            if not i["acknowledged"]:
                if c3.button("✅ Đã xử lý", key=f"ack{i['id']}", type="primary", width="stretch"):
                    try:
                        api_post(f"/incidents/{i['id']}/ack", {"note": note_txt})
                        st.rerun(scope="fragment")
                    except ApiError as e:
                        st.error(str(e))
            if c3.button("Đóng sự cố", key=f"close{i['id']}", width="stretch",
                         help="Dùng khi camera mất tín hiệu và đã xử lý xong bằng tay"):
                try:
                    api_post(f"/incidents/{i['id']}/close")
                    st.rerun(scope="fragment")
                except ApiError as e:
                    st.error(str(e))


open_incidents()

tab1, tab2 = st.tabs(["Sự cố đã đóng", "Nhật ký cảnh báo"])
with tab1:
    closed = safe_get("/incidents", {"status": "closed", "limit": 200}) or []
    handled = [i["handle_seconds"] for i in closed if i["handle_seconds"] is not None]
    kpi_row([
        kpi("Sự cố đã đóng", fmt_int(len(closed)), "200 sự cố gần nhất", "primary"),
        kpi("Thời gian phản hồi TB", fmt_duration(sum(handled) / len(handled)) if handled else "–",
            "từ lúc báo Đỏ đến lúc xác nhận", "info"),
        kpi("Chưa từng được xác nhận", fmt_int(len(closed) - len(handled)), "sự cố tự đóng khi chưa ai bấm", "warn"),
    ])
    if closed:
        df = pd.DataFrame([{
            "Mã": i["id"], "Bắt đầu": fmt_time(i["opened_at"]), "Kết thúc": fmt_time(i["closed_at"]),
            "Kéo dài": fmt_duration(i["duration_seconds"]), "Cao nhất (người)": i["peak_count"],
            "Người xác nhận": i["acked_by"] or "–", "Phản hồi sau": fmt_duration(i["handle_seconds"]),
            "Cách đóng": "Tự động" if i["close_reason"] == "auto" else f"Thủ công ({i['closed_by']})",
            "Ghi chú": i["note"] or "",
        } for i in closed])
        st.dataframe(df, width="stretch", hide_index=True)
    else:
        st.info("Chưa có sự cố nào được đóng.")

with tab2:
    events = safe_get("/system_events", {"limit": 200}) or []
    if events:
        st.dataframe(pd.DataFrame([{
            "Thời gian": fmt_time(e["timestamp"]), "Loại": e["label"],
            "Camera": str(e["camera_id"] or "–"), "Số người": str(e["count"]) if e["count"] is not None else "–",
            "Nội dung": (e["message"] or "").replace("[SmartCau AI] ", ""),
        } for e in events]), width="stretch", hide_index=True, height=460)
        counts = {}
        for e in events:
            counts[e["label"]] = counts.get(e["label"], 0) + 1
        st.markdown(" ".join(badge(f"{k}: {v}", EVENT_TONE.get(next(x["event_type"] for x in events if x["label"] == k), "muted"))
                             for k, v in counts.items()), unsafe_allow_html=True)
    else:
        st.info("Chưa có cảnh báo nào.")
