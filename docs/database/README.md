# Cơ sở dữ liệu SmartCau AI

## Cách tạo và nâng cấp CSDL

- Mặc định dùng SQLite, tệp `backend/smartcau.db` (không đưa lên GitHub, đã có trong `.gitignore`). Đổi sang PostgreSQL/MySQL bằng biến `SMARTCAU_DATABASE_URL`.
- Khi khởi động, `backend/main.py` gọi `backend/database.py::ensure_schema()`:
  1. tạo các bảng còn thiếu (`Base.metadata.create_all`);
  2. so cột trong code với cột trong CSDL, cột mới được thêm bằng `ALTER TABLE ... ADD COLUMN`.
  Vì vậy tệp `.db` cũ vẫn chạy khi code thêm cột. `ensure_schema` **không** đổi kiểu, không xóa cột, không thêm ràng buộc.
- Thay đổi khác (thêm khóa ngoại, đổi kiểu, tách bảng) phải viết thành tệp migration đánh số trong thư mục này và chạy tay sau khi sao lưu CSDL.

## Các tệp

| Tệp | Nội dung | Trạng thái |
|---|---|---|
| `000_initial_schema.sql` | Lược đồ hiện hành, 17 bảng, khớp các lớp SQLAlchemy | Đang dùng |
| `001_proposed_constraints.sql` | Thêm khóa ngoại, UNIQUE (date, hour) cho vé, CHECK, bảng `recipient_topics` | Đề xuất, chưa áp dụng vào code |
| `../../sample_data/sample_day.sql` | Dữ liệu mẫu một ngày vận hành (10/11/2026) | Dùng để thử, demo |

## Nạp dữ liệu mẫu vào một CSDL riêng

```bash
python - <<'PY'
import sqlite3
c = sqlite3.connect("backend/sample.db")
c.executescript(open("docs/database/000_initial_schema.sql", encoding="utf-8").read())
c.executescript(open("sample_data/sample_day.sql", encoding="utf-8").read())
PY
# chạy backend trên CSDL mẫu (Windows PowerShell: $env:SMARTCAU_DATABASE_URL="sqlite:///backend/sample.db")
SMARTCAU_DATABASE_URL=sqlite:///backend/sample.db uvicorn backend.main:app --port 8000
```

Tài khoản mẫu: `admin`, `quanly`, `truc1`, mật khẩu `SmartCau@2026`.

## Quy ước

- Thời gian lưu UTC; `bridge_crossings.local_time` lưu giờ Việt Nam; thống kê dùng `backend/timeutil.py`.
- Mã lưu CSDL không đổi: `Man`/`Woman`, `Trong nuoc`/`Nuoc ngoai`, `OK`/`WARNING`/`ALERT`/`CRITICAL`, `in`/`out`.
- Thêm bảng/cột: khai báo trong lớp SQLAlchemy, `ensure_schema` tự thêm cột; cập nhật `000_initial_schema.sql` cho khớp.
