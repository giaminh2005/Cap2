"""
frontend/views/co_cau_khach.py  —  SKELETON
--------------------------------------------
Phu trach: HOAN (giao dien) · MINH (API that)
Chuc nang: F3.3 Tong hop co cau khach (FR-09) · PB-07 (US-08, can bo xuc tien)
API dung: GET /stats/demographics?date=   (routers/demographics.py)

Hoan lam giao dien ngay tren du lieu mau; khi Minh thay mock bang du lieu
that (giu nguyen cau truc JSON), trang tu hien so lieu that.
"""

from datetime import date

import pandas as pd
import streamlit as st

from common import _HAS_PLOTLY, api_get, mock_notice, page_header, todo_box

page_header("👥", "Can bo xuc tien", "Co cau khach tham quan",
            "Gioi tinh, nhom tuoi, trong nuoc / nuoc ngoai theo tung gio - khong luu anh khuon mat.")

todo_box("Hoan", [
    "Bieu do cot chong Nam/Nu theo gio, bieu do nhom tuoi, ty le trong nuoc/nuoc ngoai",
    "Loc theo ngay + nut xuat CSV",
    "Ghi chu 'so lieu uoc luong boi AI, sai so ...' (lay tu muc Gioi han do chinh xac trong NANG_CAP.md)",
])

day = st.date_input("Ngay", value=date.today())
data, err = api_get("/stats/demographics", params={"date": day.isoformat()})
if err:
    st.error(err)
    st.stop()
mock_notice(data)

df_hour = pd.DataFrame(data["by_hour"]).set_index("hour")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Nam / Nu theo gio**")
    st.bar_chart(df_hour)
with c2:
    st.markdown("**Nhom tuoi**")
    st.bar_chart(pd.Series(data["age_range"], name="So luot"))

st.markdown("**Trong nuoc / Nuoc ngoai** (muc minh hoa - BRD Bang 27)")
st.dataframe(pd.Series(data["domestic_vs_foreign"], name="So luot"), use_container_width=True)
