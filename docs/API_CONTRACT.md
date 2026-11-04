# Hợp đồng API (API Contract) — SmartCau AI

**Chốt ngày 09/11/2026 (đầu Sprint 3).** Đây là "thỏa thuận" giữa người làm giao diện và người làm backend: frontend chỉ đọc đúng các khóa JSON ghi ở đây, backend chỉ được thêm khóa mới chứ không đổi/xóa khóa cũ. Nhờ vậy giao diện làm trên dữ liệu mẫu ngay từ ngày đầu, không phải chờ backend xong.

Muốn đổi hợp đồng: mở GitHub Issue gắn nhãn `api-change`, cả 3 người đồng ý rồi mới sửa file này.

Trạng thái: **Chạy** = đã có dữ liệu thật · **Mock** = trả dữ liệu mẫu, có khóa `"mock": true`.

| Chức năng | Phương thức + đường dẫn | Trạng thái | Backend | Frontend dùng |
|---|---|---|---|---|
| — | `GET /health` | Chạy | Minh | app.py |
| F1.3 | `POST /entry` `{track_id, age, age_range, gender}` | Chạy | Minh | camera_in.py |
| F1.3 | `POST /exit` | Chạy | Minh | camera_out.py |
| F1.2 | `POST /occupancy` `{count, status}` | Chạy | Minh | camera |
| F1.2 | `GET /stats/occupancy` → `{current_count}` | Chạy | Minh | camera, Bảng LED |
| F5.1 | `GET /stats/current` → `{current_count, current_status, total_visitors_logged, gender_breakdown, average_age}` | Chạy | Minh | Tổng quan, Bảng LED |
| F5.1 | `GET /stats/occupancy/history?limit=` → `[{timestamp, count, status}]` | Chạy | Minh | Tổng quan (Khánh) |
| F1.2/F1.3 | `POST /bridge/crossing` `{camera_id: 1\|2, direction: "in"\|"out", track_id}` → `{num1, num2, onbridge, dem, date, reset}` | Chạy | Minh | camera_bridge.py |
| F1.2 | `GET /bridge/state` → `{num1, num2, onbridge, dem, date}` | Chạy | Minh | Lượt qua cầu |
| F1.3 | `GET /bridge/stats?group=hour\|day\|month\|year&date_from=&date_to=` → `{total_entries, total_exits, rows:[{period, entries, exits, entries_cam1, entries_cam2}]}` | Chạy | Minh | Lượt qua cầu |
| F1.2 | `POST /bridge/reset?reset_dem=` (X-Admin-Key) | Chạy | Minh | — |
| F1.4 | `POST /facade_pass`, `GET /stats/facade?date=` → `{date, by_hour:[{hour, facade_passes}]}` | Mock | Minh (S5) | Báo cáo |
| F2 | `POST /system_events` `{event_type, count, message}` | Chạy | Minh | camera |
| F2 | `GET /system_events?limit=` | Chạy | Minh | — |
| F2.4 | `GET /incidents` → `[{id, timestamp, event_type, count, message, acknowledged, acked_at, acked_by, handle_seconds}]` | Nửa thật* | Hoan (S4) | Trực ca |
| F2.4 | `POST /incidents/{id}/ack?acked_by=&note=` | Mock | Hoan (S4) | Trực ca |
| F3.2 | `POST /visit_events`, `GET /visit_events?limit=&gender=&age_range=` | Chạy | Minh | Lịch sử |
| F3.3 | `GET /stats/demographics?date=` → `{date, by_hour:[{hour, Man, Woman}], age_range:{}, domestic_vs_foreign:{}}` | Mock | Minh (S4) | Cơ cấu khách (Hoan) |
| F3.3 | `POST /region_stats`, `GET /stats/region` | Chạy | Minh | — |
| F4.1 | `POST /tickets` `{date, hour, ticket_count, entered_by}` | Mock | Hoan (S5) | Đối chiếu vé |
| F4.2 | `GET /tickets/reconciliation?date=` → `{entries_counted, tickets_sold, gap, gap_rate_pct, by_hour:[]}` | Mock | Hoan (S5) | Đối chiếu vé |
| F5.2 | `GET /reports/summary?period=day\|week\|month&date=` → `{total_entries, peak_hour, peak_count, by_day:[], gender:{}, age_range:{}, alerts:{}, avg_handle_seconds}` | Mock | Hoan (S4–5) | Báo cáo |
| F6.2 | `GET /config`, `PUT /config` `{alert_threshold}` | Chạy | Minh | Ngưỡng cảnh báo (Khánh) |
| F6.3 | `GET /recipients`, `POST /recipients` `{name, channel, address, active}`, `DELETE /recipients/{id}` | Mock (lưu tạm RAM) | Khánh (S4) | Người nhận cảnh báo |
| F6.1 | `POST /auth/login` `{username, password}` → `{username, role}` | Mock | Minh (S5) | app.py |

\* `/incidents` đọc sự cố thật từ `system_events`; các trường xử lý (`acknowledged`…) chưa lưu thật.

## Quy ước

- Thời gian trả về dạng ISO `YYYY-MM-DDTHH:MM:SS` (UTC, như hiện tại). Ngày nhập vào dạng `YYYY-MM-DD`.
- Giới tính luôn là `"Man"` / `"Woman"` (giá trị gốc của DeepFace); giao diện tự đổi sang Nam / Nữ.
- Bảng CSDL mới của module nào khai báo **trong file router của module đó**, không sửa `backend/models.py` (tránh xung đột).
- Khi thay mock bằng dữ liệu thật: xóa khóa `"mock"` → giao diện tự ẩn dòng "Đang hiển thị dữ liệu mẫu".
