# media/ — Tệp gốc của nhóm

Lưu nguyên bản các tệp nhóm gửi (không chỉnh sửa). Bản đã xử lý để chạy trên bảng LED (tách nền xanh thành WebM trong suốt, cắt dấu ✦, nén 720p) nằm ở `backend/led_display/media/`.

## mascot/ — Chú khỉ áo dài xanh cầm quạt (phông xanh, 1920×1080, 24 fps, ~10 giây, có tiếng)

| Tệp | Hành động | Dự kiến dùng |
|---|---|---|
| `1_idle_dung_yen.mp4` | Đứng yên, chớp mắt | Trạng thái Bình thường (chạy lặp) |
| `2_wave_vay_chao.mp4` | Mở quạt, vẫy tay | Chào khách |
| `3_bow_chap_tay_cam_on.mp4` | Chắp tay cúi chào | Cảm ơn / đóng cửa |
| `4_yellow_canh_bao_vang.mp4` | Phe phẩy quạt, giơ tay | Cảnh báo Vàng — cầu sắp đầy |
| `5_red_canh_bao_do.mp4` | Giơ tay ra hiệu dừng | Cảnh báo Đỏ — cầu đang đầy |

## phong_nen/ — Nền động chạy lặp (1920×1080, 24 fps, ~10 giây, có tiếng)

Đánh số theo hướng dẫn sử dụng bảng LED:

| Tệp | Cảnh | Khung giờ | Vai trò |
|---|---|---|---|
| `1_pho_co_ban_ngay.mp4` | Phố cổ Hội An, đèn lồng | Ngày | Cảnh chính ban ngày |
| `2_song_hoai_hoa_dang_dem.mp4` | Sông Hoài, hoa đăng | Đêm | Xen kẽ ban đêm |
| `3_cau_rong_da_nang_dem.mp4` | Cầu Rồng, Đà Nẵng | Đêm | Cảnh chính ban đêm |
| `4_chua_cau.mp4` | Chùa Cầu bên mặt nước | Ngày | Xen kẽ ban ngày |

Ở mức Đỏ, cả 4 cảnh chạy thành tour tham quan ảo, mỗi cảnh 30 giây.

Cả mascot và phông nền đều có dấu "✦" nhỏ ở góc dưới bên phải (dấu của công cụ tạo video); bản đã xử lý đã cắt bỏ.

## tai_lieu/ — Tài liệu dự án

- `BaoCao_Sprint0_Nhom50_v1.0.docx` — Báo cáo Sprint 0 (Business Case, Project Charter)
- `Sprint1_BRD_Nhom50.docx` / `.pdf` — Tài liệu yêu cầu nghiệp vụ
- `Sprint1_BFD_Nhom50.pdf` — Sơ đồ phân rã chức năng
- `Sprint1_BPMN_Flowchart_Nhom50.pdf` — Flowchart và BPMN AS-IS / TO-BE
