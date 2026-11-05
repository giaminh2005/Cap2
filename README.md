# SmartCau AI — Camera AI quản lý đám đông Chùa Cầu (Nhóm 50 · 49K22.3)

> **Tài liệu tổng thể mã nguồn (chức năng ↔ tệp code, API, CSDL, tra lỗi):** [`docs/TONG_QUAN_MA_NGUON.md`](docs/TONG_QUAN_MA_NGUON.md). Khi nhờ AI sửa lỗi, gửi kèm tệp này.

Hệ thống đếm khách trên Chùa Cầu bằng 2 camera đặt ở 2 chân cầu, cảnh báo quá tải Vàng/Đỏ, ước lượng giới tính, độ tuổi, khách trong nước/châu Á hay quốc tế, và trang web quản lý cho người trực, quản lý và quản trị viên.

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

### DeepFace không nhận diện

Camera vẫn đếm người nhưng không hiện giới tính / tuổi, và in **[LỖI NHẬN DIỆN]** kèm lỗi gốc. Kiểm tra trong đúng `.venv`:
```powershell
python -c "import sys; print(sys.executable)"
python -c "import tensorflow as tf; print('TF', tf.__version__)"
python -c "from deepface import DeepFace; print('DeepFace OK')"
```
| Lỗi | Cách sửa |
|---|---|
| `No module named 'deepface'` | `.venv` chưa kích hoạt hoặc cài nhầm Python khác: kích hoạt `.venv` rồi `pip install deepface` |
| `No module named 'tensorflow'` / không cài được tensorflow | `pip install tensorflow tf-keras`; nếu pip báo không có bản phù hợp thì dùng Python 3.11 |
| `DLL load failed` (Windows) | Cài **Microsoft Visual C++ Redistributable x64** (aka.ms/vs/17/release/vc_redist.x64.exe), khởi động lại máy |
| Lỗi nhắc tới `Keras 3` / `tf_keras` | `pip install tf-keras==` + đúng số phiên bản tensorflow (vd tensorflow 2.17.1 → `tf-keras==2.17.0`) |
| Lỗi nhắc tới `numpy` | `pip install "numpy<2"` |

Sau khi cài thêm gói, chạy lại 2 lệnh sửa OpenCV ở trên (pip có thể kéo OpenCV 5 về lại).

## Chạy hệ thống (mọi lệnh chạy từ thư mục gốc `Cap2/`)

| Cửa sổ | Lệnh | Ghi chú |
|---|---|---|
| 1 | `uvicorn backend.main:app --reload --port 8000` | API: http://127.0.0.1:8000/docs |
| 2 | `streamlit run frontend/app.py` | Web: http://localhost:8501 |
| 3 | `python ai_engine/camera_bridge.py --camera-id 1 --source 0` | camera chân cầu 1 (gửi cảnh báo) |
| 4 | `python ai_engine/camera_bridge.py --camera-id 2 --source 1` | camera chân cầu 2 |

Bot Telegram trả lời `/tinhhinh`, `/homnay`, `/suco` và có nút **✅ Đã xử lý** ngay dưới tin cảnh báo Đỏ; mỗi tin kèm tình hình hiện tại. Xem `docs/GHI_CHU_GIAO_DIEN.md`, mục "Tin nhắn Telegram và tự động hóa".

Dùng webcam USB hoặc **điện thoại làm camera** (`--source 1`, `--source phone:<IP>`, `--source droidcam:<IP>`): xem `docs/CAMERA_NGOAI.md`; dò camera bằng `python tools/tim_camera.py`.

Nhận diện giới tính / tuổi / nguồn khách bật sẵn; thêm `--no-demographics` nếu chỉ cần đếm. Các ghi chú, hướng dẫn và mã yêu cầu (FR, BRULE, KPI) đã gỡ khỏi giao diện web được lưu ở `docs/GHI_CHU_GIAO_DIEN.md`.

- **Đăng nhập lần đầu:** `admin` / `admin123`, hệ thống bắt đổi mật khẩu. Tạo thêm tài khoản Quản lý, Người trực ở trang **Tài khoản**.
- `--source` nhận số webcam, đường dẫn video hoặc địa chỉ `rtsp://...`.
- Trên cửa sổ camera (**click vào cửa sổ trước** để nó nhận phím): **chữ L**, số 1 hoặc **chuột phải** = kẻ lại vạch (click 2 đầu vạch rồi click 1 điểm ở phía cầu), `R` = vạch mặc định, `Q` = thoát.
- Tăng độ chính xác: `--imgsz 960`, `--model yolov8s-pose.pt`, `--face-detector retinaface`. Xem [docs/AI_CAI_THIEN.md](docs/AI_CAI_THIEN.md).
- Không có camera: `python tools/simulate_bridge.py --random 200` để giả lập lượt qua cầu.
- **Nhận tin Telegram:** đặt biến `TELEGRAM_BOT_TOKEN` trên máy chạy backend, thêm chat_id ở trang **Người nhận cảnh báo**.

## Chạy trên nhiều máy

Một máy làm **máy chủ** (`uvicorn backend.main:app --host 0.0.0.0 --port 8000`), mỗi máy camera chạy `camera_bridge.py ... --api http://<IP-máy-chủ>:8000`, các máy khác chỉ cần trình duyệt mở `http://<IP-máy-chủ>:8501` (web) hoặc `:8000/led/` (bảng LED). Kiểm tra kết nối: `python tools/kiem_tra_mang.py`. Hướng dẫn đầy đủ, mở tường lửa và kịch bản demo: [docs/TRIEN_KHAI_NHIEU_MAY.md](docs/TRIEN_KHAI_NHIEU_MAY.md).

## Quy tắc đếm và cảnh báo

- Khách qua vạch về phía cầu ở camera k: `num_k += 1`, `dem += 1`. Qua vạch ra ngoài: `num_k -= 1`.
- `onbridge = num1 + num2`. Khi `onbridge ≤ 0` thì đặt lại `num1 = num2 = 0`. `dem` về 0 lúc 0 giờ mỗi ngày (giờ Việt Nam).
- Người chỉ đi ngang phía ngoài, không qua vạch, được tính 1 lượt mặt tiền (BRULE-10).
- **Vàng** từ 75% sức chứa (15/20). **Đỏ** khi vượt sức chứa **liên tục 15 giây**. Hết Đỏ khi ≤ 15 người liên tục 15 giây. Tin nhắn không lặp trong 3 phút (BRULE-02, BRULE-04).
- Sự cố Đỏ được mở tự động, người trực bấm **Đã xử lý** (1 chạm), sự cố tự đóng khi hết quá tải.

## Lưu ý về nhận diện

- **Trong nước/châu Á – Quốc tế là ước lượng**: mô hình chỉ phân được nhóm khu vực rộng và gộp khách Việt Nam với khách Hàn, Nhật, Trung, nên không xác định được quốc tịch.
- Kết quả có độ tin cậy dưới 70% được ghi là “Không xác định” và không tính vào tỷ lệ (BRULE-06).
- Hệ thống không lưu ảnh hay đặc trưng khuôn mặt; khung hình chỉ xử lý trong bộ nhớ.

## Bảng LED hai đầu cầu (mascot Linh Thân + Linh Khuyển)

- Mỗi đầu cầu một màn hình, mở bằng Chrome hoặc Edge rồi nhấn **F11**:
  - Đầu cầu 1: **http://127.0.0.1:8000/led/?dau=1** (Linh Thân đón khách, Linh Khuyển ra ngăn khi Đỏ, đúng bảng hướng dẫn).
  - Đầu cầu 2: **http://127.0.0.1:8000/led/?dau=2** (đổi vai: Linh Khuyển đón khách, Linh Thân ra ngăn khi Đỏ).
  - Xem song song cả hai: **http://127.0.0.1:8000/led/hai-man-hinh.html**.
  Nếu máy LED khác máy chủ, thay `127.0.0.1` bằng IP của máy chủ. Trang này không cần đăng nhập.
- Khởi động: nhân vật đón khách **đi vào** rồi vẫy tay giới thiệu. Xanh: đứng chờ, xen vẫy tay / cúi chào. Vàng: quạt và ra hiệu đi chậm mỗi 20 giây. **Lên Đỏ**: biển báo đổi ngay; nhân vật đón khách vẫy tay **đi ra**, nhân vật canh **đi vào** rồi giơ tay ngăn mỗi 18 giây. **Đỏ hạ xuống**: nhân vật canh cúi chào cảm ơn, đi ra, nhân vật đón khách đi vào lại. Câu thoại chọn ngẫu nhiên, không lặp câu vừa nói, tự đổi "Chào buổi sáng / chiều / tối".
- **Phông nền theo giờ:** ban ngày (06:00–17:30) dùng cảnh 1, xen cảnh 4 mỗi 5 phút; ban đêm dùng cảnh 3, xen cảnh 2. Mức Vàng thêm tông ấm. Mức Đỏ chạy **tour 4 cảnh**, mỗi cảnh 30 giây, có thuyết minh. Đổi cảnh bằng hiệu ứng mờ chéo 0,8 giây đúng lúc video hết vòng lặp.
- `&scene=3` khóa một cảnh; `&debug=1` hoặc phím **D** mở bảng giả lập Xanh / Vàng / Đỏ, +1 khách, chọn cảnh, thử từng clip (kể cả `walk_loop`) và "đi ra → đi vào".
- Muốn đổi câu thoại, giờ ngày/đêm, thời lượng, vai nhân vật mỗi đầu cầu (`CONFIG.ends`): sửa `CONFIG` ở đầu tệp `backend/led_display/led.js`.
- Tệp gốc: `media/mascot/`, `media/phong_nen/`.

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
