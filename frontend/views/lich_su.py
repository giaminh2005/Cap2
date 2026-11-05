"""
frontend/views/lich_su.py  —  MODULE M6 · F3.2 / F5.1 Tra cuu luot khach (FR-09, FR-10)
Phu trach: KHANH.
"""

from datetime import timedelta

import pandas as pd
import streamlit as st

from common import (AGE_ORDER, GENDER_VI, ORIGIN_VI, fmt_int, fmt_time, kpi, kpi_row, local_today,
                    page_header, safe_get)

page_header("Phân tích · Hồ sơ lượt khách", "Lịch sử lượt khách", "Tra cứu, lọc và xuất nhãn nhận diện của từng lượt khách vào cầu.")

today = local_today()
with st.container(border=True):
    c1, c2, c3, c4, c5 = st.columns([2, 1, 1, 1.2, 1])
    picked = c1.date_input("Khoảng thời gian", value=(today - timedelta(days=6), today), format="DD/MM/YYYY")
    gender = c2.selectbox("Giới tính", ["Tất cả", "Nữ", "Nam", "Không xác định"])
    age = c3.selectbox("Nhóm tuổi", ["Tất cả"] + AGE_ORDER)
    origin = c4.selectbox("Nguồn khách", ["Tất cả", "Trong nước/châu Á", "Quốc tế"])
    limit = c5.number_input("Số dòng tối đa", 50, 20000, 1000, step=50)

if not isinstance(picked, (tuple, list)) or len(picked) != 2:
    st.info("Chọn ngày bắt đầu và ngày kết thúc.")
    st.stop()

params = {"date_from": picked[0].isoformat(), "date_to": picked[1].isoformat(), "limit": int(limit)}
if gender != "Tất cả":
    params["gender"] = {"Nữ": "Woman", "Nam": "Man", "Không xác định": "unknown"}[gender]
if age != "Tất cả":
    params["age_range"] = age
if origin != "Tất cả":
    params["origin"] = {"Trong nước/châu Á": "Trong nuoc", "Quốc tế": "Nuoc ngoai"}[origin]

rows = safe_get("/visit_events", params)
if rows is None:
    st.stop()
if not rows:
    st.info("Không có lượt khách nào khớp bộ lọc.")
    st.stop()

df = pd.DataFrame([{
    "Thời gian": fmt_time(r["timestamp"]),
    "Camera": f"Chân cầu {r['camera_id']}" if r["camera_id"] else "–",
    "Giới tính": GENDER_VI.get(r["gender"], r["gender"]),
    "Nhóm tuổi": "Không xác định" if r["age_range"] in (None, "Khong xac dinh", "Khong ro") else r["age_range"],
    "Tuổi ước tính": str(r["age"]) if r["age"] is not None else "–",
    "Nguồn khách": ORIGIN_VI.get(r["origin"], "Chưa rõ"),
    "Mã theo dõi": str(r["track_id"]) if r["track_id"] is not None else "–",
} for r in rows])

kpi_row([
    kpi("Số lượt hiển thị", fmt_int(len(df)), "theo bộ lọc", "primary"),
    kpi("Nữ", fmt_int((df["Giới tính"] == "Nữ").sum()), "", "info"),
    kpi("Nam", fmt_int((df["Giới tính"] == "Nam").sum()), "", "info"),
    kpi("Quốc tế", fmt_int((df["Nguồn khách"] == "Quốc tế").sum()), "ước lượng", "warn"),
])
st.dataframe(df, width="stretch", hide_index=True, height=480)
st.download_button("Xuất CSV", data=df.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"luot_khach_{picked[0]}_{picked[1]}.csv", mime="text/csv")
