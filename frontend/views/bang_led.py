"""
frontend/views/bang_led.py  —  SKELETON
----------------------------------------
Phu trach: HOAN      Chuc nang: F2.2 Phat canh bao tai cho (FR-05) · PB-04
API dung: GET /stats/current, GET /config

MVP mo phong den + bang LED song ngu Viet - Anh tren man hinh (khong lap
phan cung that - Bang 27 BRD). Mo trang nay toan man hinh tren 1 may
rieng/TV khi demo de dong vai "bang dien tu dau cau".
"""

import streamlit as st

from common import api_get, todo_box

todo_box("Hoan", [
    "Chot nguong Vang/Do voi Khanh (BRULE-01/02: Vang tu 15 nguoi, Do tren 20 nguoi lien tuc 15 giay)",
    "Tu lam moi moi 2 giay de khop FR-02 (cap nhat <= 2 giay)",
    "Them dong 'thoi gian cho du kien' neu nhom quyet dinh lam FR-17 (ngoai MVP)",
])

stats, err1 = api_get("/stats/current")
cfg, err2 = api_get("/config")
if err1 or err2:
    st.error(err1 or err2)
    st.stop()

count = stats["current_count"]
threshold = cfg["alert_threshold"]
yellow_at = round(threshold * 0.75)

if count > threshold:
    bg, vi, en = "#7A1F1A", "CẦU ĐANG QUÁ TẢI — VUI LÒNG CHỜ", "BRIDGE FULL — PLEASE WAIT"
elif count >= yellow_at:
    bg, vi, en = "#B7791F", "CẦU SẮP ĐẦY — ĐI CHẬM, KHÔNG DỪNG LẠI", "NEARLY FULL — KEEP MOVING"
else:
    bg, vi, en = "#2F5D46", "MỜI QUÝ KHÁCH THAM QUAN", "WELCOME — PLEASE ENTER"

st.markdown(
    f"""
    <div style="background:{bg};color:#FFF8E8;border-radius:18px;padding:48px 24px;text-align:center;
                font-family:'Be Vietnam Pro',sans-serif;box-shadow:0 12px 30px rgba(0,0,0,.25);">
        <div style="font-size:5rem;font-weight:800;line-height:1;">{count}<span style="font-size:2rem;"> / {threshold}</span></div>
        <div style="font-size:2rem;font-weight:700;margin-top:18px;">{vi}</div>
        <div style="font-size:1.4rem;opacity:.9;margin-top:6px;">{en}</div>
    </div>
    """,
    unsafe_allow_html=True,
)
