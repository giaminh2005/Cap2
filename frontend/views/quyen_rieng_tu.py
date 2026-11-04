"""
frontend/views/quyen_rieng_tu.py  —  MODULE M7 · PB-06 Cam ket quyen rieng tu (NFR-05, BRULE-05, BRULE-09)
Phu trach: KHANH.
"""

import streamlit as st

from common import ApiError, api_post, fmt_int, fmt_time, has_role, kpi, kpi_row, note, page_header, safe_get

page_header("🛡️", "Quyền riêng tư", "Cam kết xử lý dữ liệu theo Nghị định 13/2023/NĐ-CP và Luật Bảo vệ dữ liệu cá nhân 2025")

s = safe_get("/privacy/summary")
if s:
    kpi_row([
        kpi("Ảnh khuôn mặt đang lưu", fmt_int(s["face_images_stored"]), "hệ thống không lưu ảnh", "ok"),
        kpi("Lượt khách có nhãn", fmt_int(s["visit_events"]), "chỉ giới tính, nhóm tuổi, nguồn khách", "info"),
        kpi("Lượt qua vạch", fmt_int(s["bridge_crossings"]), "không gắn danh tính", "info"),
        kpi("Dữ liệu cũ nhất", fmt_time(s["oldest_visit"], "%d/%m/%Y") if s["oldest_visit"] else "–",
            f"giữ tối thiểu {s['retention_min_days'] // 30} tháng", "primary"),
    ])

st.markdown("""
#### Hệ thống làm gì với hình ảnh
- Khung hình camera chỉ được xử lý **trong bộ nhớ**, không ghi ra ổ đĩa, không gửi lên máy chủ.
- **Không lưu** ảnh, video hay đặc trưng khuôn mặt. Máy chủ chỉ nhận số đếm và nhãn ước lượng
  (giới tính, nhóm tuổi, trong nước / nước ngoài) của từng lượt vào, không kèm tên hay ảnh.
- Kết quả có độ tin cậy dưới 70% được ghi là **“Không xác định”** và không đưa vào tỷ lệ (BRULE-06).
- “Trong nước / nước ngoài” chỉ là **ước lượng thô** từ nhóm khu vực rộng, không phải quốc tịch.
- Số liệu và nhật ký sự cố được lưu tối thiểu **24 tháng** (BRULE-09).
""")

st.markdown("#### Bảng thông báo song ngữ đặt tại hai đầu cầu")
st.markdown(
    """<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
    <div class="sc-kpi primary"><b>KHU VỰC CÓ CAMERA AI ĐẾM LƯỢNG KHÁCH</b><br>
    Camera chỉ đếm số người và ước lượng giới tính, độ tuổi để bảo vệ di tích và an toàn của quý khách.
    Hệ thống không lưu hình ảnh khuôn mặt. Đơn vị quản lý: Trung tâm Quản lý Bảo tồn Di sản Văn hóa Hội An.</div>
    <div class="sc-kpi primary"><b>AI CAMERA VISITOR COUNTING IN OPERATION</b><br>
    Cameras only count visitors and estimate gender and age group to protect the heritage site and your safety.
    No facial images are stored. Operator: Hoi An Centre for Cultural Heritage Management and Preservation.</div>
    </div>""",
    unsafe_allow_html=True,
)

if has_role("admin"):
    st.markdown("#### Xóa dữ liệu cũ")
    with st.form("purge"):
        days = st.number_input("Xóa dữ liệu cũ hơn (ngày)", min_value=730, max_value=3650, value=730, step=30)
        confirm = st.checkbox("Tôi hiểu thao tác này không thể hoàn tác")
        if st.form_submit_button("Xóa dữ liệu cũ", type="primary"):
            if not confirm:
                st.error("Hãy tích xác nhận trước khi xóa.")
            else:
                try:
                    r = api_post("/privacy/purge", params={"older_than_days": int(days)})
                    st.success(f"Đã xóa {r['deleted_rows']} dòng dữ liệu cũ.")
                except ApiError as e:
                    st.error(str(e))
    note("Theo BRULE-09 phải giữ số liệu tổng hợp và nhật ký sự cố tối thiểu 24 tháng, nên chỉ xóa được dữ liệu cũ hơn 730 ngày.")
