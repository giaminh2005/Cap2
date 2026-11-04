"""
frontend/views/bang_led.py  —  MODULE M3 · F2.2 Tin hieu tai cho (FR-05, AC-03.1)
Phu trach: HOAN.
Mo phong den + bang LED song ngu Viet - Anh tai 2 dau cau, doi trang thai
trong <= 2 giay. Mo toan man hinh (F11) tren man hinh dat tai dau cau.
"""

import streamlit as st

from common import page_header, safe_get

page_header("Vận hành · Tín hiệu tại chỗ", "Bảng LED tại chỗ",
            "Mô phỏng đèn và bảng thông báo song ngữ đặt tại hai đầu cầu. Nhấn F11 để hiển thị toàn màn hình.")

SIGNS = {
    "CRITICAL": ("#2A0B07", "#E2483A", "CẦU ĐANG ĐẦY · VUI LÒNG CHỜ", "THE BRIDGE IS FULL · PLEASE WAIT"),
    "WARNING": ("#2A1E05", "#E8B23A", "CẦU SẮP ĐẦY · XIN ĐI CHẬM, KHÔNG DỪNG LẠI", "NEARLY FULL · PLEASE KEEP MOVING"),
    "OK": ("#0B1F16", "#4FBF7C", "MỜI QUÝ KHÁCH THAM QUAN", "WELCOME · PLEASE ENTER"),
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
        f'<div style="width:46px;height:46px;border-radius:50%;margin:0 12px;background:{c if k == key else "#1a1a1a"};'
        f'box-shadow:{"0 0 26px " + c if k == key else "inset 0 0 8px #000"};border:2px solid #2b2b2b"></div>'
        for k, c in (("OK", "#4FBF7C"), ("WARNING", "#E8B23A"), ("CRITICAL", "#E2483A")))
    st.markdown(
        f"""
        <div style="background:#0E0C0B;padding:26px;border:1px solid #3A2E25;box-shadow:0 22px 50px rgba(31,26,23,.25)">
          <div style="display:flex;justify-content:center;margin-bottom:22px">{lamps}</div>
          <div style="background:{bg};padding:46px 24px 40px;text-align:center;border:1px solid {lamp}55;
                      font-family:'Be Vietnam Pro',sans-serif;color:{lamp};text-shadow:0 0 14px {lamp}66">
            <div style="font-size:clamp(3rem,8vw,6rem);font-weight:600;line-height:1;font-variant-numeric:tabular-nums">
              {cur['current_count']}<span style="font-size:.38em;opacity:.75"> / {cfg['alert_threshold']}</span></div>
            <div style="font-size:.85rem;letter-spacing:.32em;opacity:.7;margin-top:10px">NGƯỜI TRÊN CẦU · PEOPLE ON THE BRIDGE</div>
            <div style="width:60px;height:1px;background:{lamp};opacity:.5;margin:26px auto"></div>
            <div style="font-size:clamp(1.3rem,3.4vw,2.4rem);font-weight:600;letter-spacing:.04em">{vi}</div>
            <div style="font-size:clamp(1rem,2.4vw,1.6rem);opacity:.85;margin-top:10px;letter-spacing:.06em">{en}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if cur["status_stale"]:
        st.caption("Chưa nhận được mức cảnh báo từ camera chân cầu 1 trong 30 giây qua; bảng đang hiển thị trạng thái Bình thường.")


sign()
