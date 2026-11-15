# Hợp đồng API — SmartCau AI (bản 1.0, toàn bộ là dữ liệu thật)

Frontend chỉ đọc đúng các khóa JSON ghi ở đây; backend được thêm khóa mới, không đổi/xóa khóa cũ. Muốn đổi: mở GitHub Issue nhãn `api-change`.

**Xác thực:** camera ghi dữ liệu bằng header `X-API-Key` (khi máy chủ đặt `SMARTCAU_API_KEY`). Người dùng web gửi `Authorization: Bearer <token>` lấy từ `/auth/login`. Cột "Quyền": — = công khai, 📷 = camera, 👤 = đã đăng nhập, 🧑‍💼 = admin/quản lý, 🔑 = admin.

| Module | Phương thức + đường dẫn | Quyền | Ghi chú |
|---|---|---|---|
| — | `GET /health` → `{status, api_key_required, admin_key_required, utc_offset_hours}` | — | camera và web kiểm tra kết nối |
| M2 | `POST /auth/login` `{username, password}` → `{token, id, username, full_name, role, role_label, must_change_password, active, last_login, created_at}` | — | |
| M2 | `POST /auth/logout`, `GET /auth/me`, `POST /auth/change_password` | 👤 | |
| M2 | `GET/POST /users`, `PUT /users/{id}` `{full_name?, role?, active?, password?}` | 🔑 | FR-12 |
| M2 | `GET /audit` | 🧑‍💼 | nhật ký thay đổi |
| M1 | `POST /bridge/crossing` `{camera_id, direction: in\|out, track_id}` → `{num1, num2, onbridge, dem, date, reset}` | 📷 | F1.2, F1.3 |
| M1 | `GET /bridge/state` · `GET /bridge/stats?group=hour\|day\|month\|year&date_from&date_to` | — | |
| M1 | `POST /bridge/reset?reset_dem=` | 🧑‍💼 | |
| M1 | `POST /bridge/heartbeat` · `GET /bridge/cameras` (thêm `has_stream`) | 📷 / — | F1.1, NFR-03 |
| M1 | `POST /bridge/stream_frame/{id}` (thân = ảnh JPEG) | 📷 | hình trực tiếp, tối đa 2 MB/ảnh |
| M1 | `GET /bridge/stream/{id}?t=<token>` (MJPEG) · `GET /bridge/stream_snapshot/{id}?t=<token>` | 🧑‍💼 | hình trực tiếp cho trang Camera; ảnh cũ hơn 5 giây → 404 |
| M1 | `POST /occupancy` `{count, status}` · `GET /stats/occupancy` · `GET /stats/occupancy/history?minutes=60` | 📷 / — | |
| M1 | `GET /stats/current` → `{current_count, current_status, status_stale, alert_threshold, entries_today, facade_today, profiles_today, gender_today, open_incidents, last_update}` | — | F5.1 |
| M1 | `POST /facade_pass` `{camera_id, count}` · `GET /stats/facade?date=` | 📷 / — | F1.4 |
| M1 | `POST /visit_events` `{track_id, age, age_range, gender, origin, camera_id}` | 📷 | F3.2, origin = `Trong nuoc` \| `Nuoc ngoai` \| null |
| M1 | `GET /visit_events?date_from&date_to&gender&age_range&origin&limit` | — | gender=`unknown` lọc "Không xác định" |
| M1 | `GET /stats/demographics?date_from&date_to` → `{date_from, date_to, total, identified, unknown, gender, age_range, origin, by_hour}` | — | F3.3, BRULE-06 |
| M3 | `POST /system_events` `{event_type, count, message, camera_id}` | 📷 | mở/đóng sự cố + gửi Telegram |
| M3 | `GET /system_events?limit&event_type` | — | có `label` tiếng Việt |
| M3 | `GET /incidents?status=open\|closed\|all` | — | F2.4 |
| M3 | `POST /incidents/{id}/ack` `{note}` · `POST /incidents/{id}/close` | 👤 | FR-07; xác nhận cũng làm được bằng nút "✅ Đã xử lý" trên Telegram |
| M3 | `POST /incidents/{id}/false_alarm` `{is_false, note}` | 👤 | KPI O5 (đánh dấu / bỏ đánh dấu báo sai) |
| M4 | `GET /reports/summary?period=day\|week\|month\|year\|custom&date=&date_from=&date_to=` → `{period, date_from, date_to, total_entries, total_exits, facade_passes, peak_*, by_day, by_month, by_hour, by_15min, time_slots, demographics, alerts, incidents, kpis, tickets, previous, capacity, ...}` | — | F5.2, F5.3; month = tháng dương lịch, year = năm dương lịch, custom tối đa 3 năm |
| M4 | `GET /reports/heatmap?date_from&date_to` (mặc định 8 tuần) · `GET /reports/daily` | — | biểu đồ nhiệt giờ × thứ & danh sách báo cáo ngày |
| M4 | `GET /reports/daily/{date}/pdf` · `GET /reports/weekly/pdf` | — | PDF thể thức hành chính; tuần = Thứ Hai – Chủ nhật vừa qua |
| M4 | `POST /reports/daily/{date}/send` · `POST /reports/weekly/send` | 🧑‍💼 | lập lại và gửi PDF qua Telegram ngay |
| M5 | `POST /tickets` `{date, hour?, ticket_count}` · `POST /tickets/bulk` · `GET /tickets` · `DELETE /tickets/{id}` | 👤 | F4.1 |
| M5 | `GET /tickets/reconciliation?date=` → `{mode, entries_counted, compared_entries, tickets_sold, gap, gap_rate_pct, by_hour}` | — | F4.2, BRULE-08 |
| M5 | `GET /tickets/reconciliation_range?date_from=&date_to=` → `{date_from, date_to, days, total_entries, total_tickets, compared_entries, gap, gap_rate_pct, days_with_tickets, worst_day}` | — | đối chiếu vé theo ngày, tối đa 1 năm |
| M6 | `GET /insights/live` → `{now, onbridge, capacity, in_per_min, out_per_min, net_per_min, trend, minutes_to_full, wait_minutes, wait_label, wait_label_en, forecast, history_days, today_vs_usual, expected_peak, expected_rest_of_day}` | — | F5.1, FR-17; xu hướng 5 phút, dự báo, thời gian chờ |
| M6 | `GET /insights/summary` → danh sách nhận định tự động | — | tóm tắt tình hình tự động cho quản lý |
| M3 | `GET /display/state` → `{onbridge, level, stale, dem, capacity, warning_threshold, wait_label, wait_label_en, is_open_now, utc_offset_hours, server_time}` | — | F2.2; bảng LED gọi mỗi giây (bản nhẹ, không tính dự báo) |
| M7 | `GET /config` → `{alert_threshold, warning_threshold, open_time, close_time, is_open_now, updated_at, updated_by}` · `PUT /config` | — / 🔑 | F6.2, FR-13 |
| M7 | `GET /recipients` (👤) · `POST /recipients` · `PUT/DELETE /recipients/{id}` · `POST /recipients/{id}/test` (🔑) · `GET /recipients/topics` (—) | 👤 / 🔑 / — | F6.3; mỗi người nhận có `topics` (loại tin), `null` = nhận tất cả |
| M7 | `GET /telegram/status` · `PUT/DELETE /telegram/token` · `GET /telegram/chats` | 🔑 | kết nối bot Telegram & tìm chat_id mới |
| M7 | `GET /privacy/summary` · `POST /privacy/purge?older_than_days=` (≥ 730) | 🧑‍💼 / 🔑 | BRULE-09; dọn dẹp dữ liệu theo luật bảo vệ dữ liệu cá nhân |

`event_type` camera gửi: `WARNING`, `CRITICAL_ALERT`, `CRITICAL_CLEARED`, `GROUP_DETECTED`, `CAMERA_LOST`, `CAMERA_RESTORED` (`GATE_CLOSED`, `GATE_REOPENED` có nhãn nhưng chưa dùng). Hệ thống tự ghi thêm `MORNING_BRIEF`, `TICKET_REMINDER`, `WEEKLY_REPORT` để biết việc tự động đã làm trong ngày / tuần.

## Quy ước

- Thời gian trả về dạng ISO UTC; frontend cộng `utc_offset_hours` lấy từ `GET /health` (mặc định +7). Ngày nhập vào dạng `YYYY-MM-DD` theo giờ Việt Nam.
- Giới tính luôn là `"Man"` / `"Woman"` / `null`; giao diện đổi sang Nam / Nữ / Không xác định.
- Bảng CSDL mới của module nào khai báo trong file router của module đó; cột mới tự được bổ sung vào `smartcau.db` cũ khi khởi động.
