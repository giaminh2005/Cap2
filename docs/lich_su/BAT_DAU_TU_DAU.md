# SmartCầu AI — Bắt đầu lại từ đầu (đọc file này là đủ)

File này thay thế mọi hướng dẫn rải rác trước đó. Làm đúng theo thứ tự bên dưới.

Bản này đã gộp **toàn bộ bản nâng cấp 5 Phase** (sửa 10 lỗi + thêm tính năng
Demographics Engine, phân nhóm khu vực, kiểm soát cổng tự động, dashboard
mở rộng) — xem chi tiết từng mục đã sửa/thêm trong `NANG_CAP.md`.

---

## 0. Trước khi bắt đầu — có 2 hướng, không cần chạy cả 2

Dự án có **2 hướng độc lập**, không phụ thuộc nhau. Chọn 1 hướng để chạy trước
(khuyên dùng Hướng A nếu bạn cần demo đầy đủ: có tách vào/ra, lưu hồ sơ tuổi/giới
tính, cảnh báo + kiểm soát cổng tự động khi quá tải):

- **Hướng A — Hệ thống camera 2 chiều (vào/ra) đầy đủ**: `api_server.py` +
  `camera_in.py` + `camera_out.py`. Có nhận diện tuổi/giới tính (Demographics
  Engine - gộp DeepFace + tư thế cơ thể + bỏ phiếu theo thời gian), lưu hồ sơ
  vào database, kiểm soát cổng tự động (banner "CHỜ - CẦU ĐANG ĐẦY" + đếm
  ngược), cảnh báo Telegram + buzzer khi quá tải.
- **Hướng B — PoC đếm người theo vùng (zone)**: `poc_dem_nguoi_chua_cau.py`.
  Đơn giản hơn, 1 lệnh duy nhất, dùng YOLO + Supervision để đếm số người đang
  đứng trong 1 vùng vẽ sẵn trên khung hình (ví dụ: lòng cầu). Không tách
  vào/ra, không nhận diện tuổi/giới tính.

---

## 1. Cài Python (bỏ qua nếu máy đã có)

Mở Terminal, gõ:

```bash
python3 --version
```

Nếu hiện ra số phiên bản (ví dụ `Python 3.11.x`) là máy đã có Python, bỏ qua
bước này. Nếu báo lỗi "command not found", tải Python tại
https://www.python.org/downloads/ (bản 3.10 trở lên), cài xong mở lại Terminal.

## 2. Giải nén và cài thư viện

1. Giải nén file zip tôi gửi, bạn sẽ có thư mục `chuacau-ai-demo-v2/`.
2. Mở Terminal, `cd` vào đúng thư mục đó, ví dụ:

```bash
cd ~/Downloads/chuacau-ai-demo-v2
```

3. (Khuyên dùng, không bắt buộc) Tạo môi trường ảo riêng cho dự án, tránh xung
   đột với các thư viện Python khác trên máy:

```bash
python3 -m venv venv
source venv/bin/activate
```

   (Mỗi lần mở Terminal mới để chạy lại dự án, phải chạy lại đúng 1 dòng
   `source venv/bin/activate` này trước, nếu không máy sẽ không thấy các thư
   viện vừa cài.)

4. Cài toàn bộ thư viện cần thiết (đã gộp sẵn cho cả 2 hướng A và B, đã pin
   phiên bản tối thiểu và sửa xung đột tf-keras — xem chi tiết trong chính
   file `requirements.txt`):

```bash
pip install -r requirements.txt
```

Lệnh này mất vài phút (tải khá nhiều thư viện AI). Cần có Internet. Nếu bị
lỗi ở riêng 1 dòng thư viện nào đó, cứ chạy `pip install <tên-thư-viện>` lại
riêng dòng đó, không cần cài lại từ đầu. Nếu `deepface`/`tf-keras` báo lỗi
xung đột Keras, đọc ghi chú ở cuối `requirements.txt`.

---

## 3. Chạy Hướng A — hệ thống camera 2 chiều đầy đủ

Cần **3 cửa sổ Terminal riêng biệt**, mở cùng lúc (nhớ `cd` vào đúng thư mục
`chuacau-ai-demo-v2/src` và kích hoạt lại `venv` ở mỗi cửa sổ nếu có dùng venv).

**Terminal 1 — chạy server lưu dữ liệu (bắt buộc chạy trước tiên):**

```bash
cd chuacau-ai-demo-v2/src
uvicorn api_server:app --reload --port 8000
```

Thấy dòng `Uvicorn running on http://127.0.0.1:8000` là server đã chạy. Để
yên cửa sổ này, không tắt.

**Terminal 2 — camera VÀO:**

```bash
cd chuacau-ai-demo-v2/src
python3 camera_in.py 0
# hoặc cách mới, rõ nghĩa hơn khi chạy nhiều camera:
python3 camera_in.py --camera-index 0
```

Lần đầu chạy sẽ tự tải thêm model `yolov8n-pose.pt` (model có nhận khớp
xương, dùng làm tín hiệu phụ cho việc đoán giới tính — xem `NANG_CAP.md`
mục Phase 2), cần Internet, chỉ tải 1 lần.

**Terminal 3 — camera RA** (nếu chỉ có 1 webcam để test cả 2, dùng số khác,
ví dụ webcam ngoài cắm USB là `1`):

```bash
cd chuacau-ai-demo-v2/src
python3 camera_out.py --camera-index 1
```

Nếu chỉ có đúng 1 webcam, chỉ cần chạy 1 trong 2 script trên (bỏ qua
Terminal còn lại) — vào trang http://127.0.0.1:8000/docs để tự gọi thử
`/entry` hoặc `/exit` mô phỏng camera kia.

Nhấn phím `q` trên cửa sổ camera để thoát.

**Quan trọng khi test:** đứng/ngồi cách camera khoảng 50–80cm, để camera
nhìn thấy **cả khuôn mặt** (mắt, mũi, miệng) — nếu camera chỉ thấy đỉnh đầu/
tóc (ví dụ đặt quá cao hoặc bạn cúi sát), hệ thống sẽ không đoán được giới
tính/tuổi, vì bản thân khuôn mặt không nằm trong khung hình. Người mới xuất
hiện sẽ hiện "(đang xác định... X/3)" vài giây trước khi "chốt" kết quả —
đây là cơ chế bỏ phiếu nhiều khung hình (Phase 2), không phải lỗi.

**Ngưỡng cảnh báo mới (theo BRD):** gần đầy = 18 người, cổng chờ (hiện banner
"CHỜ - CẦU ĐANG ĐẦY") = 20 người, quá tải khẩn cấp (Telegram + buzzer) = 25
người.

## 4. Chạy Hướng B — PoC đếm người theo vùng

Chỉ cần **1 cửa sổ Terminal**, không cần chạy `api_server.py`:

```bash
cd chuacau-ai-demo-v2/src
python3 poc_dem_nguoi_chua_cau.py --source 0
```

Mặc định đếm toàn bộ khung hình, ngưỡng cảnh báo 20 người. Nếu muốn giới hạn
đúng 1 vùng cụ thể (ví dụ lòng cầu) thay vì cả khung hình, truyền 4 điểm toạ
độ (x,y) vẽ nên vùng đó:

```bash
python3 poc_dem_nguoi_chua_cau.py --source 0 --zone "100,50 540,50 540,400 100,400" --threshold 20
```

Nhấn `q` để thoát.

Lần đầu chạy, `ultralytics` sẽ tự tải model `yolo11n.pt` (~6MB), cần Internet,
chỉ tải 1 lần.

---

## 5. Hướng C (mới) — Trang Admin Web + đồng bộ Google Sheets

Đây là 2 tính năng **tuỳ chọn, cộng thêm** vào Hướng A (không thay thế) —
dùng khi bạn muốn: (1) một trang web riêng để xem/đổi ngưỡng cảnh báo, xem
lịch sử lượt khách, xuất CSV mà không cần mở code; (2) tự động đẩy dữ liệu
sang Google Sheets để chia sẻ với người không dùng được trang admin.

### 5.1 Chạy trang Admin Web

Trang admin là 1 ứng dụng Streamlit, nói chuyện với `api_server.py` qua HTTP
(không đụng trực tiếp vào database) — vẫn cần **Terminal 1 (`uvicorn`) đang
chạy** như ở Hướng A. Mở thêm 1 Terminal mới:

```bash
cd chuacau-ai-demo-v2
streamlit run admin_web/app.py
```

Trình duyệt sẽ tự mở `http://localhost:8501`. Mật khẩu đăng nhập mặc định là
`admin123` (**đổi lại trước khi cho người khác dùng** — xem biến môi trường
`ADMIN_WEB_PASSWORD` ở mục 6 dưới đây). Trang có 4 mục:

- **Tổng quan**: số người đang có mặt, trạng thái cảnh báo, tỉ lệ giới
  tính, phân bố tuổi.
- **Lịch sử lượt khách**: danh sách hồ sơ đã ghi nhận, lọc theo giới
  tính/nhóm tuổi, xuất CSV.
- **Cấu hình**: đổi ngưỡng cảnh báo (`alert_threshold`) — đổi ở đây, camera
  `camera_in.py`/`camera_out.py` đang chạy sẽ **tự động nhận ngưỡng mới**
  trong vòng tối đa 15 giây (không cần sửa code/restart camera — xem
  `CONFIG_POLL_INTERVAL_SEC` trong 2 file đó).
- **Đồng bộ Google Sheets**: xem mục 5.2 dưới đây.

### 5.2 Đồng bộ dữ liệu sang Google Sheets (tuỳ chọn)

Cần tạo 1 "Service Account" của Google (miễn phí) để script được phép ghi
vào Google Sheet của bạn — làm 1 lần duy nhất:

1. Vào https://console.cloud.google.com/ → tạo 1 Project mới (hoặc dùng
   project có sẵn).
2. Vào "APIs & Services" → "Enabled APIs" → bật **Google Sheets API** và
   **Google Drive API**.
3. Vào "APIs & Services" → "Credentials" → "Create Credentials" → "Service
   Account" → đặt tên tuỳ ý → tạo xong, mở Service Account đó → tab "Keys"
   → "Add Key" → "Create new key" → chọn JSON → tự tải về 1 file `.json`.
4. Tạo 1 Google Sheet mới (trên drive.google.com), mở sheet đó → bấm "Share"
   → dán **email của Service Account** (dạng `...@...iam.gserviceaccount.com`,
   xem trong file `.json` vừa tải, trường `client_email`) → cấp quyền
   "Editor".
5. Copy `SHEET_ID` từ URL của sheet, ví dụ:
   `https://docs.google.com/spreadsheets/d/ĐÂY_LÀ_SHEET_ID/edit` → chỉ lấy
   phần giữa `/d/` và `/edit`.
6. Đặt file `.json` đã tải vào đâu đó trên máy (ví dụ cùng thư mục dự án,
   KHÔNG commit/chia sẻ file này — đây là "chìa khoá" truy cập sheet của
   bạn), rồi set biến môi trường trước khi chạy:

```bash
export GOOGLE_SHEETS_ID="sheet-id-cua-ban"
export GOOGLE_SHEETS_CREDENTIALS_FILE="/duong/dan/toi/file-service-account.json"
```

Sau đó có 2 cách đồng bộ:

- **Qua trang Admin Web**: mục "Đồng bộ Google Sheets" → bấm "Đồng bộ ngay".
- **Qua dòng lệnh** (tiện nếu muốn tự đặt lịch chạy định kỳ, ví dụ bằng
  `cron`):

```bash
cd chuacau-ai-demo-v2/src
python3 google_sheets_sync.py
```

Script sẽ ghi đè (overwrite) 2 trang tính `LuotKhach` (danh sách hồ sơ) và
`TongQuan` (số liệu tổng hợp) mỗi lần chạy — phù hợp cho PoC/demo; nếu dữ
liệu lớn hơn nhiều (hàng chục nghìn dòng), nên đổi sang cơ chế ghi nối tiếp
(append) thay vì ghi đè toàn bộ.

---

## 6. Các biến môi trường tuỳ chọn (set trước khi chạy camera script)

| Biến | Dùng để làm gì | Mặc định |
|---|---|---|
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Gửi cảnh báo quá tải thật qua Telegram (xem hướng dẫn tạo bot trong `src/telegram_alert.py`) | Không set = chỉ in cảnh báo ra Terminal |
| `SMARTCAU_API_KEY` | Bật xác thực đơn giản cho API — set **CÙNG giá trị** ở cả Terminal chạy `uvicorn` VÀ Terminal chạy camera | Không set = API mở, không cần key (phù hợp demo) |
| `SMARTCAU_ENABLE_REGION` | Bật tính năng "phân nhóm khu vực" (Phase 3) — set `=1`. **Đọc kỹ `src/region_mapping.py` trước khi bật** (giới hạn pháp lý/đạo đức) | Không set = tắt (không phân nhóm khu vực) |
| `SMARTCAU_SOLO_DEMO` | Demo chỉ với **1 webcam duy nhất** (không có camera RA để trừ số) — set `=1` trước khi chạy `camera_in.py`. Khi bật, số "đang có mặt" sẽ tính **trực tiếp theo số người đang trong khung hình ngay lúc đó** (tự giảm khi người rời khung hình), hồ sơ giới tính/tuổi vẫn lưu vào backend bình thường. Triển khai thật 2 camera (vào + ra) thì **KHÔNG bật** biến này | Không set = dùng đúng kiến trúc 2 camera (số "đang có mặt" = tổng vào − tổng ra, lấy từ server) |
| `SMARTCAU_BUZZER_WEBHOOK` | Địa chỉ HTTP của thiết bị còi/đèn báo thật (nếu có phần cứng IoT) | Không set = chỉ in `[BUZZER]` ra Terminal |
| `SMARTCAU_API` | Đổi địa chỉ server nếu không chạy ở `127.0.0.1:8000` (dùng chung cho camera script VÀ admin_web) | `http://127.0.0.1:8000` |
| `ADMIN_API_KEY` | Bật xác thực cho việc **đổi** cấu hình (`PUT /config`) — set **CÙNG giá trị** ở Terminal chạy `uvicorn` VÀ ở Terminal chạy `streamlit run admin_web/app.py`. Khác với `SMARTCAU_API_KEY` (dùng cho camera ghi dữ liệu) — 2 key tách riêng để có thể đưa `SMARTCAU_API_KEY` cho người vận hành camera mà không lo họ đổi được ngưỡng cảnh báo hệ thống | Không set = ai cũng đổi được cấu hình qua `/config` (phù hợp demo nội bộ) |
| `ADMIN_WEB_PASSWORD` | Mật khẩu đăng nhập trang Admin Web | Không set = dùng mật khẩu demo `admin123` (trang sẽ tự cảnh báo "đang dùng mật khẩu demo") |
| `GOOGLE_SHEETS_ID`, `GOOGLE_SHEETS_CREDENTIALS_FILE` | Đồng bộ dữ liệu sang Google Sheets — xem hướng dẫn tạo Service Account ở mục 5.2 | Không set = tắt tính năng đồng bộ Sheets (các phần khác của dự án không bị ảnh hưởng) |

Ví dụ bật đồng thời Telegram + xác thực API + xác thực admin:

```bash
export TELEGRAM_BOT_TOKEN="123456789:ABCdef..."
export TELEGRAM_CHAT_ID="987654321"
export SMARTCAU_API_KEY="mot-chuoi-bi-mat-tuy-chon"
export ADMIN_API_KEY="mot-chuoi-bi-mat-khac-cho-admin"
export ADMIN_WEB_PASSWORD="mot-mat-khau-khac-admin123"
```

---

## 7. Lỗi thường gặp

| Hiện tượng | Nguyên nhân | Cách sửa |
|---|---|---|
| Màn hình cứ hiện "đang tìm mặt..." mãi, không lưu hồ sơ | Đã sửa trong `age_gender_estimator.py` đi kèm (lọc nhầm kết quả "giả" + cắt vùng ảnh sai khi camera quay gần/từ trên xuống) | Đảm bảo bạn đang dùng đúng bộ file này, không trộn với bản cũ |
| Vẫn không hiện giới tính dù code đã đúng | Camera chưa nhìn thấy khuôn mặt (chỉ thấy tóc/đỉnh đầu) | Lùi ra xa, chỉnh góc camera ngang tầm mặt |
| Hiện "(đang xác định... 1/3)" mãi không chốt | Chưa đủ số khung hình để bỏ phiếu đạt 70% tin cậy (Phase 2) — có thể do góc mặt thay đổi liên tục | Giữ yên tư thế vài giây để hệ thống thu đủ phiếu |
| `ModuleNotFoundError: No module named '...'` | Thiếu thư viện / quên kích hoạt venv | Kích hoạt lại venv (`source venv/bin/activate`) rồi `pip install -r requirements.txt` |
| `Address already in use` khi chạy `uvicorn` | Terminal 1 (server) đã chạy ở cửa sổ khác rồi | Không cần chạy lại, dùng cửa sổ cũ, hoặc tắt (Ctrl+C) rồi chạy lại 1 lần |
| `401 Unauthorized` khi camera gọi API | Server bật `SMARTCAU_API_KEY` nhưng camera script không set cùng giá trị | Set cùng `SMARTCAU_API_KEY` ở cả 2 phía, hoặc bỏ set ở cả 2 phía |
| `no such column` / `no such table` khi chạy `uvicorn` | File `smartcau.db` cũ (tạo từ bản code trước, cấu trúc bảng khác) | Xoá file `src/smartcau.db` rồi chạy lại `uvicorn` (bảng tự tạo lại, mất dữ liệu demo cũ — không sao) |
| Trang Admin Web báo "Không kết nối được server" | Chưa chạy `uvicorn` (Terminal 1), hoặc `SMARTCAU_API` của admin_web không khớp địa chỉ server | Chạy `uvicorn api_server:app --reload --port 8000` trước, hoặc set `SMARTCAU_API` cho đúng |
| `401 Unauthorized` khi bấm "Lưu cấu hình" trên Admin Web | Server bật `ADMIN_API_KEY` nhưng admin_web không set cùng giá trị | Set cùng `ADMIN_API_KEY` ở cả Terminal `uvicorn` và Terminal `streamlit run admin_web/app.py` |
| Đổi ngưỡng trên Admin Web nhưng camera không đổi theo | Camera đang chạy từ TRƯỚC khi nâng cấp này (bản cũ không tự đọc `/config`), hoặc chưa đợi đủ 15 giây cho lần poll kế tiếp | Dùng đúng bản `camera_in.py`/`camera_out.py` trong gói này; đợi tối đa 15 giây, hoặc khởi động lại camera để nhận ngay |
| `ModuleNotFoundError: No module named 'streamlit'` (hoặc `gspread`) | Chưa cài thư viện Nhóm 4 | Chạy lại `pip install -r requirements.txt` ở thư mục gốc dự án (đã gồm sẵn Nhóm 4) |
| `AttributeError: module 'supervision' has no attribute 'ByteTrack'` khi chạy `poc_dem_nguoi_chua_cau.py` | Bản `supervision` bạn cài là **bản rất mới (>=0.31)** — thư viện này đã **gỡ bỏ** `ByteTrack` ra khỏi lõi, chuyển qua 1 gói riêng tên `trackers` | Cài thêm: `pip install trackers` rồi chạy lại (không cần sửa code gì — script tự nhận biết nên dùng bản nào). Nếu vẫn lỗi, chạy `python3 -c "import supervision as sv; print(sv.__version__)"` để xem đúng bản đang cài |

---

## 8. Cấu trúc thư mục

```
chuacau-ai-demo-v2/
├── BAT_DAU_TU_DAU.md          <- file này
├── NANG_CAP.md                 <- đối chiếu TỪNG lỗi/tính năng bạn yêu cầu -> đã sửa ở đâu
├── requirements.txt            <- cài 1 lần duy nhất: pip install -r requirements.txt
├── README.md                   <- tài liệu gốc (bản demo offline co ban, tham khao them)
├── dashboard.html               <- dashboard tinh (mo bang trinh duyet, khong can server)
├── admin_web/                    <- NEW (Huong C): trang quan ly web (Streamlit) - "streamlit run admin_web/app.py"
│   ├── app.py                     <- 4 trang: Tong quan / Lich su / Cau hinh / Dong bo Google Sheets
│   ├── requirements.txt           <- tham khao rieng (da gom vao requirements.txt goc, Nhom 4)
│   └── .streamlit/config.toml     <- theme mau "di san Hoi An" cho trang admin
├── src/
│   ├── api_server.py             <- Huong A: server luu du lieu (FastAPI) + auth tuy chon + system_events + region_stats + /config
│   ├── google_sheets_sync.py     <- NEW (Huong C): dong bo du lieu sang Google Sheets (qua gspread)
│   ├── camera_in.py               <- Huong A: camera VAO (pose model + Demographics Engine + gate control + tu doc nguong tu /config)
│   ├── camera_out.py              <- Huong A: camera RA (cung tu doc nguong tu /config)
│   ├── camera_backend.py          <- NEW: mo camera cross-platform + doc --camera-index
│   ├── age_gender_estimator.py    <- uoc luong tuoi/gioi tinh/(tuy chon) race tu DeepFace (DA SUA 2 LOI)
│   ├── demographics_engine.py     <- NEW: gop tin hieu (DeepFace + pose + bo phieu theo thoi gian)
│   ├── region_mapping.py          <- NEW: quy doi ve 4 nhom khu vuc (tuy chon, doc ky gioi han)
│   ├── crowd_counter.py           <- dem nguoi (HOG hoac YOLO) + nguong 18/20/25
│   ├── camera_ui.py               <- ve khung/nhan/banner cong/dem nguoc tren man hinh camera
│   ├── telegram_alert.py          <- gui canh bao Telegram + tin hieu buzzer
│   ├── webcam_tracking_demo.py    <- ban demo 1-camera don gian (khong tach vao/ra)
│   ├── webcam_full_demo.py        <- demo dem nguoi + nhan khau hoc tu 1 webcam
│   ├── poc_dem_nguoi_chua_cau.py  <- Huong B: PoC dem theo vung (YOLO + Supervision)
│   ├── data_simulator.py          <- sinh du lieu mo phong (co cot khu vuc) cho dashboard.html
│   ├── generate_dashboard.py      <- xuat dashboard.html + marketing_summary.csv
│   ├── demo_run.py                <- chay nhanh demo offline co ban (1 lenh)
│   └── test_crowd_counter.py      <- unit test
└── sample_data/                   <- du lieu/anh mau (+ marketing_summary.csv moi)
```
