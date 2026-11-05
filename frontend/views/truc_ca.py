"""
frontend/views/truc_ca.py  —  MODULE M3 · F2.4 Ghi nhan xu ly su co (FR-07, AC-04.1, AC-04.2, KPI O4, O5)
Phu trach: HOAN.
Xac nhan "Da xu ly" bang 1 cham; danh dau "Bao sai" de tinh ty le canh bao sai (O5).
Su co tu dong khi <= 15 nguoi lien tuc 15 giay. Tu cap nhat 2 giay.
"""

import pandas as pd
import streamlit as st

from common import (ApiError, fmt_mmss, api_post, badge, empty, fmt_duration, fmt_int, fmt_pct, fmt_time, kpi, kpi_row,
                    page_header, safe_get, section)

page_header("Vận hành · Người trực kiểm soát vé", "Trực ca & sự cố",
            "Xác nhận đã xử lý sự cố quá tải chỉ với một chạm. Đánh dấu “báo sai” nếu cảnh báo không đúng thực tế.")


def _act(path, payload=None):
    try:
        api_post(path, payload)
        st.rerun(scope="fragment")
    except ApiError as e:
        st.error(str(e))


@st.fragment(run_every=2)
def open_incidents():
    section("Sự cố đang mở")
    incidents = safe_get("/incidents", {"status": "open"})
    if incidents is None:
        return
    if not incidents:
        empty("Không có sự cố quá tải nào đang mở.")
        return
    for i in incidents:
        with st.container(border=True):
            c1, c2, c3 = st.columns([2.6, 1.6, 1.1], gap="medium")
            c1.markdown(f'<div class="sc-eyebrow" style="color:var(--danger)">Cảnh báo Đỏ · sự cố #{i["id"]}</div>'
                        f'<div class="sc-title" style="font-size:1.9rem;margin:2px 0 4px">{i["peak_count"]} người trên cầu</div>'
                        f'<div class="sc-sub">Bắt đầu {fmt_time(i["opened_at"], "%H:%M:%S")} · đã kéo dài '
                        f'{fmt_duration(i["duration_seconds"])} · {i["alert_count"]} lần cảnh báo</div>',
                        unsafe_allow_html=True)
            if i["acknowledged"]:
                c1.markdown(badge(f"Đã xác nhận · {i['acked_by']} · sau {fmt_duration(i['handle_seconds'])}", "ok"),
                            unsafe_allow_html=True)
            if i["false_alarm"]:
                c1.markdown(badge(f"Báo sai · {i['false_by']}", "warn"), unsafe_allow_html=True)
            note_txt = c2.text_input("Ghi chú", key=f"note{i['id']}", placeholder="vd: đã dừng đoàn tại đầu cầu Bắc")
            if not i["acknowledged"] and c3.button("Đã xử lý", key=f"ack{i['id']}", type="primary", width="stretch"):
                _act(f"/incidents/{i['id']}/ack", {"note": note_txt})
            if not i["false_alarm"] and c3.button("Báo sai", key=f"fa{i['id']}", width="stretch",
                                                  help="Cảnh báo không đúng thực tế"):
                _act(f"/incidents/{i['id']}/false_alarm", {"is_false": True, "note": note_txt})
            if c3.button("Đóng sự cố", key=f"close{i['id']}", width="stretch",
                         help="Dùng khi camera mất tín hiệu và đã xử lý xong bằng tay"):
                _act(f"/incidents/{i['id']}/close")


open_incidents()

tab1, tab2 = st.tabs(["Sự cố đã đóng", "Nhật ký cảnh báo"])
with tab1:
    closed = safe_get("/incidents", {"status": "closed", "limit": 200}) or []
    real = [i for i in closed if not i["false_alarm"]]
    within = [i for i in real if i["handle_seconds"] is not None and i["handle_seconds"] <= 180]
    handled = [i["handle_seconds"] for i in real if i["handle_seconds"] is not None]
    kpi_row([
        kpi("Sự cố đã đóng", fmt_int(len(closed)), "200 sự cố gần nhất", "primary"),
        kpi("Xử lý trong 3 phút", fmt_pct(len(within) / len(real) * 100) if real else "–", "mục tiêu ≥ 90%",
            "ok" if real and len(within) / len(real) >= .9 else "warn"),
        kpi("Phản hồi trung bình", fmt_mmss(sum(handled) / len(handled)) if handled else "–", "từ lúc báo Đỏ đến lúc xác nhận", "info"),
        kpi("Báo sai", fmt_pct((len(closed) - len(real)) / len(closed) * 100) if closed else "–", "mục tiêu ≤ 5%",
            "ok" if closed and (len(closed) - len(real)) / len(closed) <= .05 else "warn"),
    ])
    if closed:
        st.dataframe(pd.DataFrame([{
            "Mã": str(i["id"]), "Bắt đầu": fmt_time(i["opened_at"]), "Kết thúc": fmt_time(i["closed_at"]),
            "Kéo dài": fmt_duration(i["duration_seconds"]), "Cao nhất": str(i["peak_count"]),
            "Người xác nhận": i["acked_by"] or "–", "Phản hồi sau": fmt_duration(i["handle_seconds"]),
            "Cách đóng": "Tự động" if i["close_reason"] == "auto" else f"Thủ công · {i['closed_by']}",
            "Báo sai": "Có" if i["false_alarm"] else "", "Ghi chú": i["false_note"] or i["note"] or "",
        } for i in closed]), width="stretch", hide_index=True, height=360)
        with st.expander("Đánh dấu / bỏ đánh dấu báo sai cho sự cố đã đóng"):
            c1, c2, c3 = st.columns([1, 2, 1])
            iid = c1.selectbox("Sự cố", [i["id"] for i in closed], format_func=lambda x: f"#{x}")
            why = c2.text_input("Lý do", placeholder="vd: camera đếm nhầm bóng người")
            cur = next(i for i in closed if i["id"] == iid)
            if c3.button("Bỏ đánh dấu" if cur["false_alarm"] else "Đánh dấu báo sai", width="stretch"):
                try:
                    api_post(f"/incidents/{iid}/false_alarm", {"is_false": not cur["false_alarm"], "note": why})
                    st.rerun()
                except ApiError as e:
                    st.error(str(e))
    else:
        empty("Chưa có sự cố nào được đóng.")

with tab2:
    events = safe_get("/system_events", {"limit": 200}) or []
    if events:
        st.dataframe(pd.DataFrame([{
            "Thời gian": fmt_time(e["timestamp"]), "Loại": e["label"], "Camera": str(e["camera_id"] or "–"),
            "Số người": str(e["count"]) if e["count"] is not None else "–",
            "Nội dung": (e["message"] or "").replace("[SmartCau AI] ", ""),
        } for e in events]), width="stretch", hide_index=True, height=460)
    else:
        empty("Chưa có cảnh báo nào.")
