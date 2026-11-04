# AI Usage Log (mẫu) — SmartCầu AI

Biểu mẫu bắt buộc theo Module 7 học phần. Đây là ví dụ đã điền sẵn dựa trên phiên làm việc dựng demo này — nhóm hãy tiếp tục ghi nối các dòng mới mỗi khi dùng AI (Claude/ChatGPT...) cho các phần tiếp theo (BRD, DFD, ERD, slide...).

| Ngày | Công cụ AI | Mục đích | Prompt (tóm tắt) | Kết quả | Người kiểm chứng | Phần đã chỉnh sửa |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-09-23 | Claude | Xây dựng tài liệu định hướng đề tài (lý do chọn đề tài, kiến trúc module, rủi ro) | "Giúp xây dựng đề tài Camera AI quản lý đám đông & nhân khẩu học tại Chùa Cầu, hướng dẫn từ đầu theo yêu cầu học phần" | Tài liệu định hướng đầy đủ 9 mục (đã lưu dạng doc riêng) | Sinh viên (nhóm) | Điều chỉnh tên đề tài, bổ sung ngữ cảnh thực tế nhóm biết |
| 2026-09-23 | Claude | Viết mã nguồn demo module đếm người + cảnh báo ngưỡng | "Viết crowd_counter.py dùng OpenCV, không cần Internet, có ngưỡng cảnh báo 18/20/25" | `crowd_counter.py` + `test_crowd_counter.py` (3 test PASS) | Sinh viên (nhóm) — cần tự chạy lại `python test_crowd_counter.py` để xác nhận |
| 2026-09-23 | Claude | Sinh dữ liệu mô phỏng khách du lịch + dashboard marketing | "Sinh dữ liệu mô phỏng 14 ngày theo quốc tịch/tuổi/giới tính, xuất dashboard HTML offline" | `data_simulator.py`, `generate_dashboard.py`, `dashboard.html` | Sinh viên (nhóm) — cần đối chiếu các giả định tỷ lệ quốc tịch có hợp lý không |

**Lưu ý khi nhóm tự bổ sung log:**
- Ghi *mọi* lần dùng AI có ảnh hưởng đến sản phẩm nộp (kể cả việc AI viết 1 đoạn BRD, vẽ gợi ý DFD, sửa lỗi code…).
- Cột "Người kiểm chứng" không được để trống — thể hiện nhóm đã tự kiểm tra lại, không copy nguyên AI.
- Nên đính kèm cả **AI Output Evaluation Sheet** (đánh giá độ chính xác/phù hợp) cho các output quan trọng như BRD, ERD.
