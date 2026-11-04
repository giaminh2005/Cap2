"""
frontend/views/bang_led.py  —  MODULE M3 · F2.2 Tin hieu tai cho (FR-05, AC-03.1)
Phu trach: HOAN.
Mo phong den + bang LED song ngu Viet - Anh tai 2 dau cau. Doi trang thai
trong <= 2 giay khi muc canh bao doi (tu cap nhat moi 2 giay).
Mo trang nay toan man hinh (F11) tren man hinh dat tai dau cau.
"""

import streamlit as st

from common import page_header, safe_get

page_header("🪧", "Bảng LED tại chỗ", "Mô phỏng đèn và bảng thông báo song ngữ tại hai đầu cầu · nhấn F11 để toàn màn hình")

SIGNS = {
    "CRITICAL": ("#9B1C14", "#FF5A4F", "CẦU ĐANG ĐẦY — VUI LÒNG CHỜ", "BRIDGE IS FULL — PLEASE WAIT"),
    "WARNING": ("#9A6A05", "#FFC233", "CẦU SẮP ĐẦY — ĐI CHẬM, KHÔNG DỪNG LẠI", "NEARLY FULL — PLEASE KEEP MOVING"),
    "OK": ("#1F5C3B", "#4CD07D", "MỜI QUÝ KHÁCH THAM QUAN", "WELCOME — PLEASE ENTER"),
}


@st.fragment(run_every=2)
def sign():
    cur = safe_get("/stats/current")
    cfg = safe_get("/config")
    if cur is None or cfg is None:
        return
    level = cur["current_status"]
    key = "CRITICAL" if level == "CRITICAL" else "WARNING" if level in ("WARNING", "ALERT") else "OK"
    bg, lamp, vi, en = SIGNS[key]
    lamps = "".join(
        f'<div style="width:54px;height:54px;border-radius:50%;margin:0 10px;background:{c if k == key else "#2b2b2b"};'
        f'box-shadow:{"0 0 28px " + c if k == key else "none"};border:3px solid #111"></div>'
        for k, c in (("OK", "#4CD07D"), ("WARNING", "#FFC233"), ("CRITICAL", "#FF5A4F")))
    st.markdown(
        f"""
        <div style="background:#111;border-radius:22px;padding:22px;box-shadow:0 18px 40px rgba(0,0,0,.25)">
          <div style="display:flex;justify-content:center;margin-bottom:18px">{lamps}</div>
          <div style="background:{bg};border-radius:14px;padding:44px 20px;text-align:center;color:#FFF8E8;
                      border:4px solid {lamp}">
            <div style="font-size:clamp(2.6rem,7vw,5.5rem);font-weight:800;line-height:1;font-variant-numeric:tabular-nums">
              {cur['current_count']}<span style="font-size:.4em;opacity:.85"> / {cfg['alert_threshold']}</span></div>
            <div style="font-size:.95rem;letter-spacing:.2em;opacity:.8;margin-top:6px">NGƯỜI TRÊN CẦU · PEOPLE ON BRIDGE</div>
            <div style="font-size:clamp(1.4rem,3.6vw,2.6rem);font-weight:800;margin-top:22px">{vi}</div>
            <div style="font-size:clamp(1.1rem,2.6vw,1.8rem);opacity:.92;margin-top:8px">{en}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if cur["status_stale"]:
        st.caption("Chưa nhận được mức cảnh báo từ camera 1 trong 30 giây qua — bảng đang hiện trạng thái Bình thường.")


sign()
