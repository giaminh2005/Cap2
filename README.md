# SmartCau AI — Camera AI quản lý đám đông Chùa Cầu (Nhóm 50 · 49K22.3)

Hệ thống đếm khách trên Chùa Cầu bằng 2 camera đặt ở 2 chân cầu, cảnh báo quá tải Vàng/Đỏ, ước lượng giới tính, độ tuổi, khách trong nước / nước ngoài, và trang web quản lý cho người trực, quản lý và quản trị viên.

## Kiến trúc 3 lớp

```
Cap2/
├── ai_engine/            Lớp AI tại camera (OpenCV + YOLOv8 + DeepFace)
│   ├── camera_bridge.py      ★ chương trình camera chân cầu (dùng cho cả camera 1 và 2)
│   ├── line_crossing.py      vạch kẻ vào/ra (F1.2, F1.3) + đếm lượt mặt tiền (F1.4)
│   ├── group_detector.py     phát hiện đoàn khách ≥ 10 người (F3.1)
│   ├── visitor_profiler.py   giới tính, tuổi, trong/ngoài nước cho khách vào cầu (F3.2)
│   ├── crowd_counter.py      ngưỡng và mức cảnh báo Vàng/Đỏ (F2.1)
│   ├── camera_ui.py          vẽ chữ tiếng Việt có dấu trên khung hình
│   ├── demographics_engine.py, age_gender_estimator.py, region_mapping.py   lõi nhận diện
│   └── camera_in.py, camera_out.py   bản cũ 1 camera vào + 1 camera ra (không dùng chung với camera_bridge)
├── backend/              Lớp nghiệp vụ + dữ liệu (FastAPI + SQLAlchemy + SQLite)
│   ├── main.py, database.py, models.py, schemas.py, security.py, timeutil.py, notify.py
│   └── routers/          counting · bridge · demographics (M1) · accounts (M2) · alerts (M3)
│                         reports (M4) · tickets (M5) · admin (M7)
├── frontend/             Lớp giao diện (Streamlit nhiều trang, tiếng Việt)
│   ├── app.py, common.py, report_export.py
│   └── views/            mỗi trang 1 file
├── tests/                pytest: backend 7 module, vạch kẻ, nhận diện, đoàn khách, mặt tiền
├── tools/                simulate_bridge.py (thử không cần camera), google_sheets_sync.py ...
└── docs/                 API_CONTRACT.md, PHAN_CONG.md
```

## Cài đặt (1 lần mỗi máy)

Khuyến nghị Python 3.11 hoặc 3.12. DeepFace cần TensorFlow; nếu `pip install` báo không tìm thấy bản tensorflow phù hợp với Python của máy, hãy tạo môi trường bằng Python 3.11 như dưới.

**Windows (PowerShell):**
```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
**macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```
Nếu cửa sổ camera báo lỗi `The function is not implemented` (OpenCV bản headless hoặc bản 5): gỡ hết rồi cài lại đúng bản.
```bash
pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python
pip install "opencv-python>=4.9,<5"
```

## Chạy hệ thống (mọi lệnh chạy từ thư mục gốc `Cap2/`)

| Cửa sổ | Lệnh | Ghi chú |
|---|---|---|
| 1 | `uvicorn backend.main:app --reload --port 8000` | API: http://127.0.0.1:8000/docs |
| 2 | `streamlit run frontend/app.py` | Web: http://localhost:8501 |
| 3 | `python ai_engine/camera_bridge.py --camera-id 1 --source 0 --demographics` | camera chân cầu 1 (gửi cảnh báo) |
| 4 | `python ai_engine/camera_bridge.py --camera-id 2 --source 1 --demographics` | camera chân cầu 2 |

- **Đăng nhập lần đầu:** `admin` / `admin123`, hệ thống bắt đổi mật khẩu. Tạo thêm tài khoản Quản lý, Người trực ở trang **Tài khoản**.
- `--source` nhận số webcam, đường dẫn video hoặc địa chỉ `rtsp://...`.
- Trên cửa sổ camera (**click vào cửa sổ trước** để nó nhận phím): **chữ L**, số 1 hoặc **chuột phải** = kẻ lại vạch (click 2 đầu vạch rồi click 1 điểm ở phía cầu), `R` = vạch mặc định, `Q` = thoát.
- Tăng độ chính xác: `--imgsz 960`, `--model yolov8s-pose.pt`, `--face-detector retinaface`. Xem [docs/AI_CAI_THIEN.md](docs/AI_CAI_THIEN.md).
- Không có camera: `python tools/simulate_bridge.py --random 200` để giả lập lượt qua cầu.
- **Nhận tin Telegram:** đặt biến `TELEGRAM_BOT_TOKEN` trên máy chạy backend, thêm chat_id ở trang **Người nhận cảnh báo**.

## Quy tắc đếm và cảnh báo

- Khách qua vạch về phía cầu ở camera k: `num_k += 1`, `dem += 1`. Qua vạch ra ngoài: `num_k -= 1`.
- `onbridge = num1 + num2`. Khi `onbridge ≤ 0` thì đặt lại `num1 = num2 = 0`. `dem` về 0 lúc 0 giờ mỗi ngày (giờ Việt Nam).
- Người chỉ đi ngang phía ngoài, không qua vạch, được tính 1 lượt mặt tiền (BRULE-10).
- **Vàng** từ 75% sức chứa (15/20). **Đỏ** khi vượt sức chứa **liên tục 15 giây**. Hết Đỏ khi ≤ 15 người liên tục 15 giây. Tin nhắn không lặp trong 3 phút (BRULE-02, BRULE-04).
- Sự cố Đỏ được mở tự động, người trực bấm **Đã xử lý** (1 chạm), sự cố tự đóng khi hết quá tải.

## Lưu ý về nhận diện

- **Trong nước / nước ngoài là ước lượng**: mô hình chỉ phân được nhóm khu vực rộng và gộp khách Việt Nam với khách Hàn, Nhật, Trung, nên không xác định được quốc tịch.
- Kết quả có độ tin cậy dưới 70% được ghi là “Không xác định” và không tính vào tỷ lệ (BRULE-06).
- Hệ thống không lưu ảnh hay đặc trưng khuôn mặt; khung hình chỉ xử lý trong bộ nhớ.

## Tính năng thông minh trên giao diện

- **Sơ đồ cầu trực tiếp**: mỗi chấm là một người đang trên cầu, màu theo mức cảnh báo, kèm tốc độ vào/ra mỗi phút.
- **Dự báo**: "cầu sẽ đầy sau bao nhiêu phút" theo xu hướng 5 phút; **thời gian chờ dự kiến** khi cầu đầy (FR-17, hiện cả trên Bảng LED); dự báo lượt vào từng giờ còn lại trong ngày (trung bình cùng thứ các tuần trước × mức đông hôm nay).
- **Nhận định tự động**: so với cùng giờ tuần trước, khung giờ cao điểm sắp tới, cơ cấu khách, sự cố xử lý chậm…
- **Thông báo nổi** ở mọi trang khi có sự cố Đỏ mới, đoàn khách lớn hoặc mất tín hiệu camera.
- **Biểu đồ bấm được**: ở trang *Lượt qua cầu*, bấm vào một cột ngày/tháng/năm để xem chi tiết bên trong.

## Báo cáo ngày tự động và chỉ số KPI

- Sau **giờ đóng cửa** (trang *Ngưỡng & giờ hoạt động*), backend tự lập báo cáo ngày, lưu lại và gửi tin tóm tắt kèm tệp **PDF** qua Telegram cho danh sách người nhận. Nếu máy tắt lúc đóng cửa, lần chạy sau sẽ lập bù ngày hôm trước. Xem và tải lại ở trang *Báo cáo định kỳ*.
- Báo cáo có các chỉ số Sprint 0: **O1** số phút vượt sức chứa, **O4** % sự cố xử lý trong 3 phút, **O5** % cảnh báo sai (người trực bấm **Báo sai** ở trang *Trực ca & sự cố*), **O8** chênh lệch lượt vào / cuống vé; kèm **biểu đồ nhiệt giờ × thứ**.

## Đo độ chính xác để nghiệm thu

| Script | Yêu cầu | Cách chạy |
|---|---|---|
| `tools/eval_counting.py` | NFR-02, O2: sai số đếm ≤ 15% (MVP), ≤ 10% (nghiệm thu) trên ≥ 3 video | `python tools/eval_counting.py --truth video_thu/dem_tay.csv` |
| `tools/eval_demographics.py` | FR-09: giới tính ≥ 85%, nhóm tuổi ≥ 55% (±1 nhóm ≥ 85%); NFR-08: chênh lệch giữa các nhóm ≤ 5 điểm % | `python tools/eval_demographics.py --dataset fairface --images D:/fairface --labels D:/fairface/fairface_label_val.csv --limit 2000` |

Tệp đếm tay cho `eval_counting.py` có các cột `video,true_in,true_out,line` (hoặc `video,second,true_count` với `--presence`). Mỗi script in bảng kết quả và lưu thêm tệp `.md`, `.csv` để dán vào báo cáo.

## Kiểm thử trước khi tạo Pull Request

```bash
pytest tests/ -q
```
