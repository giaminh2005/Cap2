# SmartCau AI — Camera AI quản lý đám đông Chùa Cầu (Nhóm 50 · 49K22.3)

Hệ thống gồm 3 lớp, mỗi lớp 1 thư mục, mỗi chức năng BFD (F1–F6) 1 file riêng để 3 người làm song song:

```
Cap2/
├── ai_engine/        Lớp xử lý AI tại camera (OpenCV + YOLOv8 + DeepFace)      — Minh
│   ├── camera_in.py / camera_out.py   chương trình chạy ở camera VÀO / RA
│   ├── crowd_counter.py               F1.2 đếm người, ngưỡng cảnh báo F2.1
│   ├── age_gender_estimator.py        F3.2 ước lượng tuổi / giới tính
│   ├── demographics_engine.py         F3.2 bỏ phiếu theo thời gian (ổn định kết quả)
│   ├── telegram_alert.py              F2.3 gửi tin nhắn người trực
│   └── camera_backend.py, camera_ui.py, region_mapping.py
├── backend/          Lớp nghiệp vụ + dữ liệu (FastAPI + SQLAlchemy + SQLite)
│   ├── main.py                        khởi động, gom các router
│   ├── database.py, models.py, schemas.py, security.py      — Minh
│   └── routers/
│       ├── counting.py      F1 Giám sát lượng khách          — Minh
│       ├── alerts.py        F2 Điều tiết quá tải             — Minh (+ Hoan: F2.4 sự cố)
│       ├── demographics.py  F3 Phân tích khách tham quan     — Minh
│       ├── tickets.py       F4 Đối chiếu vé                  — Hoan
│       ├── reports.py       F5 Lập báo cáo                   — Hoan
│       └── admin.py         F6 Quản trị hệ thống             — Khánh (+ Minh: tài khoản)
├── frontend/         Lớp giao diện (Streamlit nhiều trang)
│   ├── app.py, common.py              menu, đăng nhập, theme dùng chung — Minh
│   └── views/                         mỗi trang 1 file (xem bảng phân công trong app.py)
├── tools/            seed_demo_data.py (nạp dữ liệu mẫu), data_simulator, generate_dashboard, demo_run, google_sheets_sync
├── tests/            test_api.py (backend), test_crowd_counter.py
├── legacy_demos/     các bản demo webcam cũ (giữ để tham khảo, không phát triển tiếp)
├── docs/             API_CONTRACT.md, PHAN_CONG.md, AI_Usage_Log.md, lich_su/
└── sample_data/
```

## Có cần đổi framework không?

Không. Dự án **đã dùng framework**: FastAPI (backend), SQLAlchemy (ORM), Streamlit (frontend), Ultralytics YOLO + DeepFace (AI). Điều còn thiếu trước đây là **cấu trúc thư mục** — toàn bộ file nằm chung một chỗ. Bản tổ chức lại này giữ nguyên công nghệ, chỉ tách theo kiến trúc 3 lớp và theo chức năng BFD. Đổi sang React/Django lúc này sẽ tốn 1–2 tuần mà không thêm điểm nào cho học phần.

## Cài đặt (1 lần cho mỗi máy)

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate        macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

Ai chỉ làm giao diện/backend (Hoan, Khánh) có thể bỏ qua `ultralytics`, `deepface`, `tf-keras` nếu máy yếu — dùng `tools/seed_demo_data.py` thay cho camera.

## Chạy hệ thống (mọi lệnh chạy từ THƯ MỤC GỐC `Cap2/`)

| Terminal | Lệnh | Ghi chú |
|---|---|---|
| 1 | `uvicorn backend.main:app --reload --port 8000` | mở http://127.0.0.1:8000/docs để xem API |
| 2 | `streamlit run frontend/app.py` | mở http://localhost:8501 — mật khẩu demo `admin123` |
| 3a | `python ai_engine/camera_in.py` | camera thật (cần YOLO + DeepFace) |
| 3b | `python tools/seed_demo_data.py` | **hoặc** nạp dữ liệu mẫu, không cần camera |

### Chế độ 2 camera chân cầu (khuyến nghị)

Mỗi chân cầu 1 camera quay từ cầu ra chân cầu, kẻ 1 vạch ngang lối đi. Khách qua vạch về phía cầu = **vào** (`num_k += 1`, `dem += 1`), qua vạch ra ngoài = **ra** (`num_k -= 1`). Số khách trên cầu `onbridge = num1 + num2`; khi `onbridge <= 0` thì đặt lại `num1 = num2 = 0`. `dem` là lượt vào cầu trong ngày, tự về 0 khi sang ngày mới (giờ Việt Nam). Chi tiết: `backend/routers/bridge.py`, `ai_engine/line_crossing.py`.

| Terminal | Lệnh |
|---|---|
| 3 | `python ai_engine/camera_bridge.py --camera-id 1 --source 0` (chân cầu 1, gửi cảnh báo) |
| 4 | `python ai_engine/camera_bridge.py --camera-id 2 --source 1` (chân cầu 2) |
| — | **hoặc** `python tools/simulate_bridge.py` để giả lập 2 camera |

Trên cửa sổ camera nhấn `l` để kẻ lại vạch bằng chuột (2 điểm của vạch + 1 điểm phía cầu), vạch lưu ở `ai_engine/config/`. Thống kê xem ở trang **Lượt qua cầu**. Không chạy chung với `camera_in.py` / `camera_out.py` vì cả hai cùng ghi số người trên cầu.

Kiểm thử trước khi tạo Pull Request: `pytest tests/ -q`

## Ghi chú di chuyển từ cấu trúc cũ

- `api_server.py` → tách thành `backend/` (đường dẫn API **giữ nguyên**, camera không phải sửa).
- `admin_web/app.py` → tách thành `frontend/app.py` + `frontend/common.py` + `frontend/views/*.py`.
- CSDL chuyển sang `backend/smartcau.db` (tự tạo, không commit). Các file `*.db`, `*.pt`, `__pycache__/` không còn đưa lên GitHub.
- API có `"mock": true` là skeleton trả dữ liệu mẫu — xem `docs/API_CONTRACT.md` để biết ai làm thật và khi nào.
