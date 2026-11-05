# Chạy SmartCau trên nhiều máy (mô phỏng như triển khai thật)

```
                         Wi-Fi / mạng LAN chung
   ┌──────────────────────────┬──────────────────────────┬────────────────────────┐
   │ MÁY CHỦ (1 máy)          │ MÁY CAMERA (1–2 máy)      │ MÁY XEM (bao nhiêu cũng │
   │  backend + CSDL :8000    │  camera_bridge.py         │ được, chỉ cần trình    │
   │  web quản lý     :8501   │  --api http://IP:8000     │ duyệt)                 │
   │  bảng LED   :8000/led/   │  gửi lượt qua vạch, mức   │  web  http://IP:8501   │
   │  báo cáo tự động, Telegram│ cảnh báo, nhịp tim        │  LED  http://IP:8000/led│
   └──────────────────────────┴──────────────────────────┴────────────────────────┘
```

- **Chỉ máy chủ có cơ sở dữ liệu** (`backend/smartcau.db`). Các máy khác không lưu gì, chỉ gửi và đọc qua API, nên mọi màn hình luôn thấy cùng một số liệu.
- Máy chủ có thể kiêm luôn camera 1. Mỗi máy camera cắm 1 webcam, đóng vai 1 chân cầu.
- Máy xem **không cần cài Python hay code**: điện thoại, máy tính bảng, laptop bất kỳ trong cùng mạng đều mở được.

## 1. Chuẩn bị mạng

- Tất cả máy kết nối **cùng một mạng Wi-Fi**. Mạng trường học, quán cà phê, khách sạn thường **chặn các máy nói chuyện với nhau** ("client isolation"). Nếu kiểm tra ở bước 4 bị lỗi, hãy bật **điểm phát Wi-Fi từ một điện thoại** và cho tất cả máy vào mạng đó.
- Trên máy chủ, tắt chế độ ngủ khi cắm sạc để demo không bị ngắt.

## 2. Máy chủ (Windows)

```powershell
cd "D:\...\Cap2"
.venv\Scripts\Activate.ps1
python tools/kiem_tra_mang.py
```
Lệnh này in **IP của máy chủ** (ví dụ `192.168.1.10`) và các lệnh dùng cho máy khác.

Mở tường lửa cho cổng 8000 và 8501 (chỉ làm 1 lần, PowerShell **Run as Administrator**):
```powershell
New-NetFirewallRule -DisplayName "SmartCau 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
New-NetFirewallRule -DisplayName "SmartCau 8501" -Direction Inbound -Protocol TCP -LocalPort 8501 -Action Allow
```
Khi Windows hỏi "Allow access" lúc chạy Python lần đầu, chọn **Private networks → Allow**.

Chạy backend **mở cho cả mạng** (khác với trước: thêm `--host 0.0.0.0`) và web:
```powershell
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```
```powershell
streamlit run frontend/app.py --server.address 0.0.0.0
```
Khuyến nghị đặt khóa cho camera để máy lạ trong mạng không gửi số liệu giả (đặt trước khi chạy backend):
```powershell
$env:SMARTCAU_API_KEY = "chuacau2026"
```

## 3. Máy camera (mỗi chân cầu 1 máy)

Máy camera cần code dự án và thư viện AI (giống phần cài đặt trong README). Không cần chạy backend hay web.
```powershell
python tools/kiem_tra_mang.py http://192.168.1.10:8000
python ai_engine/camera_bridge.py --camera-id 1 --source 0 --api http://192.168.1.10:8000
```
Máy thứ hai dùng `--camera-id 2`. Nếu máy chủ đặt khóa ở bước 2, thêm `--api-key chuacau2026`.
Chỉ camera 1 gửi mức cảnh báo Vàng/Đỏ; cả hai đều gửi lượt vào/ra, lượt mặt tiền, đoàn khách, hồ sơ khách.

## 4. Máy xem

| Màn hình | Địa chỉ |
|---|---|
| Web quản lý (đăng nhập theo vai trò) | `http://192.168.1.10:8501` |
| Bảng LED đầu cầu 1 (Chrome/Edge, F11) | `http://192.168.1.10:8000/led/?dau=1` |
| Bảng LED đầu cầu 2 | `http://192.168.1.10:8000/led/?dau=2` |
| Xem song song 2 bảng LED | `http://192.168.1.10:8000/led/hai-man-hinh.html` |
| Tài liệu API | `http://192.168.1.10:8000/docs` |

Trang **Camera** trong web cho biết camera nào đang chạy trên **máy nào**, tốc độ khung hình và lúc mất tín hiệu.

## 5. Kịch bản demo "như thật"

| Máy | Vai trò | Người phụ trách |
|---|---|---|
| Laptop A (máy chủ + camera 1) | Chân cầu 1, máy chủ | Minh |
| Laptop B (camera 2) | Chân cầu 2 | Hoan |
| Laptop / máy chiếu C | Bảng LED đầu cầu 1 (`?dau=1`) | — |
| Laptop / máy chiếu D (nếu có) | Bảng LED đầu cầu 2 (`?dau=2`) | — |
| Điện thoại của Khánh | Người trực: trang *Trực ca & sự cố* | Khánh |
| Laptop của giảng viên | Quản lý: *Tổng quan*, *Báo cáo* | — |

1. Đặt sức chứa = 3 ở trang *Ngưỡng & giờ hoạt động* để dễ lên Vàng/Đỏ.
2. Hai người đi vào qua vạch ở camera 1, một người ở camera 2 → *Lượt qua cầu* thấy `num1 = 2, num2 = 1, onbridge = 3`, bảng LED chuyển Vàng.
3. Thêm một người vào, đứng trên 15 giây → Đỏ: cả 2 bảng LED đổi màu, nhân vật canh đi vào giơ tay ngăn, điện thoại người trực nhận thông báo, Telegram báo sự cố.
4. Người trực bấm **Đã xử lý** trên điện thoại; mọi người đi ra ở camera 2 → sự cố tự đóng, `num1`, `num2` tự về 0.
5. Rút dây webcam ở laptop B → trang *Camera* và Telegram báo mất tín hiệu, cắm lại thì tự kết nối.

## 6. Khi các máy ở khác mạng (học nhóm từ xa)

Dùng **Tailscale** (miễn phí, tailscale.com): cài trên mọi máy, đăng nhập cùng một tài khoản, mỗi máy có một IP dạng `100.x.y.z` dùng thay cho IP LAN ở trên. Không cần mở cổng trên router.

## 7. Lỗi thường gặp

| Hiện tượng | Cách xử lý |
|---|---|
| `kiem_tra_mang.py` báo không mở được cổng | Sai IP, khác mạng Wi-Fi, chưa `--host 0.0.0.0`, hoặc tường lửa — xem bước 2 |
| Camera in "KHÔNG kết nối được máy chủ" | Như trên; thử mở `http://IP:8000/docs` bằng trình duyệt trên máy camera |
| Camera báo `401` | Máy chủ đặt `SMARTCAU_API_KEY` mà camera thiếu `--api-key` |
| Máy xem mở web được nhưng bảng LED trong web trống | Tường lửa chưa mở cổng 8000 (web dùng 8501, LED dùng 8000) |
| IP máy chủ đổi sau khi khởi động lại | Chạy lại `python tools/kiem_tra_mang.py`; muốn cố định thì đặt IP tĩnh hoặc dùng Tailscale |
| Số liệu chậm / giật | Wi-Fi yếu; máy camera nên cắm dây hoặc ngồi gần điểm phát |

Muốn nhiều người cùng ghi dữ liệu lâu dài, có thể chuyển sang PostgreSQL bằng biến `SMARTCAU_DATABASE_URL` (cài thêm `psycopg2-binary`); với demo học kỳ, SQLite trên máy chủ là đủ.
