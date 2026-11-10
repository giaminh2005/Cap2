# Hợp đồng API — SmartCau AI (bản 1.0, toàn bộ là dữ liệu thật)

Frontend chỉ đọc đúng các khóa JSON ghi ở đây; backend được thêm khóa mới, không đổi/xóa khóa cũ. Muốn đổi: mở GitHub Issue nhãn `api-change`.

**Xác thực:** camera ghi dữ liệu bằng header `X-API-Key` (khi máy chủ đặt `SMARTCAU_API_KEY`). Người dùng web gửi `Authorization: Bearer <token>` lấy từ `/auth/login`. Cột "Quyền": — = công khai, 📷 = camera, 👤 = đã đăng nhập, 🧑‍💼 = admin/quản lý, 🔑 = admin.

| Module | Phương thức + đường dẫn | Quyền | Ghi chú |
|---|---|---|---|
| M2 | `POST /auth/login` `{username, password}` → `{token, username, full_name, role, must_change_password}` | — | |
| M2 | `POST /auth/logout`, `GET /auth/me`, `POST /auth/change_password` | 👤 | |
| M2 | `GET/POST /users`, `PUT /users/{id}` `{full_name?, role?, active?, password?}` | 🔑 | FR-12 |
| M2 | `GET /audit` | 🧑‍💼 | nhật ký thay đổi |
| M1 | `POST /bridge/crossing` `{camera_id, direction: in\|out, track_id}` → `{num1, num2, onbridge, dem, date, reset}` | 📷 | F1.2, F1.3 |
| M1 | `GET /bridge/state` · `GET /bridge/stats?group=hour\|day\|month\|year&date_from&date_to` | — | |
| M1 | `POST /bridge/reset?reset_dem=` | 🧑‍💼 | |
| M1 | `POST /bridge/heartbeat` · `GET /bridge/cameras` | 📷 / — | F1.1, NFR-03 |
| M1 | `POST /occupancy` `{count, status}` · `GET /stats/occupancy` · `GET /stats/occupancy/history?minutes=60` | 📷 / — | |
| M1 | `GET /stats/current` → `{current_count, current_status, status_stale, alert_threshold, entries_today, facade_today, profiles_today, gender_today, open_incidents, last_update}` | — | F5.1 |
| M1 | `POST /facade_pass` `{camera_id, count}` · `GET /stats/facade?date=` | 📷 / — | F1.4 |
| M1 | `POST /visit_events` `{track_id, age, age_range, gender, origin, camera_id}` | 📷 | F3.2, origin = `Trong nuoc` \| `Nuoc ngoai` \| null |
| M1 | `GET /visit_events?date_from&date_to&gender&age_range&origin&limit` | — | gender=`unknown` lọc "Không xác định" |
| M1 | `GET /stats/demographics?date_from&date_to` → `{total, identified, unknown, gender, age_range, origin, by_hour}` | — | F3.3, BRULE-06 |
| M3 | `POST /system_events` `{event_type, count, message, camera_id}` | 📷 | mở/đóng sự cố + gửi Telegram |
| M3 | `GET /system_events?limit&event_type` | — | có `label` tiếng Việt |
| M3 | `GET /incidents?status=open\|closed\|all` | — | F2.4 |
| M3 | `POST /incidents/{id}/ack` `{note}` · `POST /incidents/{id}/close` | 👤 | FR-07 |
| M4 | `GET /reports/summary?period=day\|week\|month\|year\|custom&date=&date_from=&date_to=` | — | F5.2, F5.3; xuất Excel |
| M4 | `GET /reports/heatmap` · `GET /reports/daily` | — | biểu đồ nhiệt 8 tuần & danh sách báo cáo ngày |
| M4 | `GET /reports/daily/{date}/pdf` · `GET /reports/weekly/pdf?date=` | — | xuất file PDF báo cáo chuẩn hành chính |
| M4 | `POST /reports/daily/{date}/send` · `POST /reports/weekly/send?date=` | 🧑‍💼 | gửi báo cáo PDF tức thời qua Telegram |
| M5 | `POST /tickets` `{date, hour?, ticket_count}` · `POST /tickets/bulk` · `GET /tickets` · `DELETE /tickets/{id}` | 👤 | F4.1 |
| M5 | `GET /tickets/reconciliation?date=` → `{mode, entries_counted, compared_entries, tickets_sold, gap, gap_rate_pct, by_hour}` | — | F4.2, BRULE-08 |
| M5 | `GET /tickets/reconciliation_range?date_from=&date_to=` | — | đối chiếu vé nhiều ngày |
| M6 | `GET /insights/live` → `{entries_5m, exits_5m, net_trend, minutes_to_full, wait_label, forecast_today}` | — | F5.1; xu hướng, dự báo & thời gian chờ |
| M6 | `GET /insights/summary` → danh sách nhận định tự động | — | tóm tắt tình hình tự động cho quản lý |
| M3 | `GET /display/state` | — | F2.2; API thời gian thực cho bảng LED 2 đầu cầu |
| M7 | `GET /config` → `{alert_threshold, warning_threshold, open_time, close_time, is_open_now, ...}` · `PUT /config` | — / 🔑 | F6.2, FR-13 |
| M7 | `GET /recipients` · `POST/PUT/DELETE /recipients` · `POST /recipients/{id}/test` · `GET /recipients/topics` | 👤 / 🔑 | F6.3; danh sách & cài đặt chủ đề nhận tin |
| M7 | `GET /telegram/status` · `PUT/DELETE /telegram/token` · `GET /telegram/chats` | 🔑 | kết nối bot Telegram & tìm chat_id mới |
| M7 | `GET /privacy/summary` · `POST /privacy/purge?older_than_days=` (≥ 730) | 🧑‍💼 / 🔑 | BRULE-09; dọn dẹp dữ liệu theo luật bảo vệ dữ liệu cá nhân |

`event_type`: `WARNING`, `CRITICAL_ALERT`, `CRITICAL_CLEARED`, `GROUP_DETECTED`, `CAMERA_LOST`, `CAMERA_RESTORED`, `GATE_CLOSED`, `GATE_REOPENED`.

## Quy ước

- Thời gian trả về dạng ISO UTC; frontend cộng `utc_offset_hours` lấy từ `GET /health` (mặc định +7). Ngày nhập vào dạng `YYYY-MM-DD` theo giờ Việt Nam.
- Giới tính luôn là `"Man"` / `"Woman"` / `null`; giao diện đổi sang Nam / Nữ / Không xác định.
- Bảng CSDL mới của module nào khai báo trong file router của module đó; cột mới tự được bổ sung vào `smartcau.db` cũ khi khởi động.
