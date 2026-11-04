"""
frontend/views/quyen_rieng_tu.py  —  SKELETON
----------------------------------------------
Phu trach: KHANH     Chuc nang: PB-06 / US-12 Cam ket khong luu anh khuon mat
                                (AC-12.1) - gan voi F6 Quan tri he thong
Khong can API. Noi dung nay cung dung lam bang thong bao in dat o dau cau.
"""

import streamlit as st

from common import page_header, todo_box

page_header("🛡️", "Du khach", "Cam ket quyen rieng tu",
            "Thong bao cong khai ve cach he thong camera xu ly hinh anh tai Chua Cau.")

todo_box("Khanh", [
    "Doi chieu noi dung voi muc Phap ly / quyen rieng tu trong BRD (Nghi dinh 13/2023 ve bao ve du lieu ca nhan)",
    "Ban tieng Anh ben canh (khach quoc te)",
    "Chup man hinh trang nay dua vao bao cao + video demo",
])

st.markdown(
    """
**He thong camera tai Chua Cau KHONG luu hinh anh khuon mat cua quy khach.**

- Camera chi dem so nguoi va uoc luong nhom tuoi, gioi tinh **ngay trong luc xu ly**; anh goc bi bo ngay sau do.
- Co so du lieu chi luu: thoi diem, khoang tuoi uoc luong, gioi tinh uoc luong - **khong** ten, **khong** anh, **khong** ma dinh danh co the truy nguoc ve 1 nguoi.
- Thong ke khu vuc/quoc tich (neu bat) chi luu **tong hop theo gio**, khong gan cho tung nguoi.
- Muc dich: giu an toan cho di tich va du khach, ho tro Trung tam bo tri nhan su.

**The camera system at the Japanese Covered Bridge does NOT store any facial images.**
Only anonymous counts and estimated age group / gender are kept, aggregated for safety and planning.
"""
)
