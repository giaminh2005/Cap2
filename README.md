# SmartCau AI

SmartCau AI là hệ thống hỗ trợ điều tiết khách tại **Chùa Cầu, Hội An**, do **Nhóm 50 · 49K22.3** thực hiện. Hai camera đặt ở hai đầu cầu ghi nhận lượt vào và ra. Người trực theo dõi số người đang trên cầu, nhận cảnh báo quá tải và xác nhận xử lý sự cố qua web hoặc Telegram. Hai bảng LED hướng dẫn khách tại chỗ.

## Chạy thử trên một máy

Dùng Python 3.11 hoặc 3.12. Chạy các lệnh từ thư mục gốc `Cap2/`.

**Windows (PowerShell)**

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**macOS**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Mở hai terminal, kích hoạt `.venv` ở mỗi terminal, rồi chạy backend trước và web sau.

| Thành phần | Lệnh | Địa chỉ |
| --- | --- | --- |
| Backend FastAPI | `python -m uvicorn backend.main:app --port 8000` | [Tài liệu API](http://127.0.0.1:8000/docs) · [Kiểm tra kết nối](http://127.0.0.1:8000/health) |
| Web Streamlit | `python -m streamlit run frontend/app.py` | [Web quản lý](http://localhost:8501) |

Với cơ sở dữ liệu chưa có tài khoản, backend tạo tài khoản `admin` với mật khẩu `admin123`. Web yêu cầu đổi mật khẩu khi đăng nhập lần đầu. Sau đó có thể tạo tài khoản **Quản lý** và **Người trực** trong trang **Tài khoản**.

Để thử luồng đếm mà không cần camera, dùng backend trỏ vào cơ sở dữ liệu thử nghiệm rồi chạy một trong hai lệnh sau. Kết quả hiện ở trang **Lượt qua cầu**. Công cụ này gửi sự kiện qua vạch. Mức cảnh báo tự động do tiến trình camera 1 tính.

```powershell
python tools/simulate_bridge.py
python tools/simulate_bridge.py --random 200
```

## Cơ sở dữ liệu

| Chế độ | Cấu hình |
| --- | --- |
| SQLite cục bộ | Khi `SMARTCAU_DATABASE_URL` chưa được đặt, backend dùng `backend/smartcau.db`. |
| PostgreSQL dùng chung qua Supabase | Đặt `SMARTCAU_DATABASE_URL` trong `.env` ở thư mục gốc trên máy chạy backend. Backend đọc tệp này khi khởi động. |

Ví dụ cấu hình `.env` cho Supabase. Thay toàn bộ phần kết nối bằng thông tin của dự án Supabase.

```dotenv
SMARTCAU_DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
```

Để demo cục bộ, đặt URL của một tệp SQLite riêng trong terminal backend. Biến môi trường được ưu tiên hơn giá trị trong `.env`. Đặt `SMARTCAU_DISABLE_SCHEDULER=1` để tắt lịch báo cáo và bot Telegram trong lần chạy demo.

```powershell
$env:SMARTCAU_DATABASE_URL = "sqlite:///backend/demo.db"
$env:SMARTCAU_DISABLE_SCHEDULER = "1"
python -m uvicorn backend.main:app --port 8000
```

Backend tạo bảng và thêm cột còn thiếu lúc khởi động. Nếu cần chuyển dữ liệu từ `backend/smartcau.db`, chạy [công cụ chuyển SQLite sang PostgreSQL](tools/migrate_sqlite_to_pg.py) trước lần khởi động backend đầu tiên trên cơ sở dữ liệu đích. Công cụ chèn dữ liệu theo từng bảng và có thể dừng giữa chừng nếu trùng khóa chính. Với demo có sẵn số liệu, xem [cách nạp dữ liệu mẫu vào SQLite riêng](docs/database/README.md#nạp-dữ-liệu-mẫu-vào-một-csdl-riêng).

## Chạy camera

Chạy mỗi camera trong một terminal riêng sau khi backend đã sẵn sàng. Ví dụ dưới đây dùng hai thiết bị video trên cùng một máy.

```powershell
python ai_engine/camera_bridge.py --camera-id 1 --source 0
python ai_engine/camera_bridge.py --camera-id 2 --source 1
```

- Dùng `python tools/tim_camera.py` để dò số thiết bị. `--source` cũng nhận đường dẫn video, URL RTSP, `phone:<IP>` và `droidcam:<IP>`. [Hướng dẫn kết nối camera ngoài](docs/CAMERA_NGOAI.md)
- Bấm **L** hoặc chuột phải trong cửa sổ camera, chọn hai đầu vạch rồi chọn một điểm ở phía cầu. Bấm **R** để về vạch mặc định hoặc **Q** để thoát.
- Nhận diện cơ cấu khách bật mặc định và dùng YOLOv8n-Pose để lấy điểm mốc cơ thể. Dùng `--no-demographics` để chỉ đếm người, `--no-origin` để bỏ ước lượng nguồn khách hoặc `--no-stream` để tắt truyền hình ảnh lên web.
- Nếu backend đặt `SMARTCAU_API_KEY`, truyền cùng giá trị qua `--api-key` hoặc biến môi trường trong terminal camera. Công cụ giả lập đọc khóa từ biến môi trường.

Để ước lượng giới tính và tuổi, hệ thống ưu tiên InsightFace qua ONNX Runtime. Đặt `genderage.onnx` trong `ai_engine/models/buffalo_s/` hoặc `~/.insightface/models/buffalo_s/`. DeepFace là phương án dự phòng và hỗ trợ ước lượng nhóm nguồn khách. Có thể chọn DeepFace bằng biến môi trường `SMARTCAU_DEMOGRAPHICS_BACKEND=deepface` trên máy camera. Nếu bộ nhận diện không khởi tạo được, camera vẫn chạy phần đếm.

Nhãn **Trong nước/châu Á** và **Quốc tế** là ước lượng theo nhóm khu vực. Hồ sơ khách lưu các nhãn ước lượng, với mục **Không xác định** khi thiếu tín hiệu đủ tin cậy. Khung hình xem trực tiếp được giữ tạm trong bộ nhớ.

Nếu OpenCV báo `The function is not implemented` khi mở cửa sổ camera, cài lại bản có hỗ trợ giao diện đồ họa.

```powershell
python -m pip uninstall -y opencv-python opencv-python-headless opencv-contrib-python
python -m pip install "opencv-python>=4.9,<5"
```

## Chạy trên nhiều máy

Trên máy chủ, cho phép các máy trong mạng truy cập backend và web.

```powershell
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

```powershell
python -m streamlit run frontend/app.py --server.address 0.0.0.0 --server.port 8501
```

Trên mỗi máy camera, thêm `--api http://IP_MAY_CHU:8000` và dùng `--camera-id` tương ứng với đầu cầu. Máy xem mở `http://IP_MAY_CHU:8501` cho web và cổng `8000` cho bảng LED hoặc hình camera trực tiếp. Chạy `python tools/kiem_tra_mang.py http://IP_MAY_CHU:8000` trên máy camera để kiểm tra kết nối. [Hướng dẫn triển khai nhiều máy](docs/TRIEN_KHAI_NHIEU_MAY.md)

## Vận hành

- **Đếm khách.** Mỗi lượt qua vạch làm tăng hoặc giảm bộ đếm của đầu cầu tương ứng. Tổng hai bộ đếm là số người đang trên cầu. Tổng lượt vào trong ngày (`dem`) được đặt lại khi sang ngày mới theo giờ Việt Nam. AI cũng ghi nhận lượt đi ngang mặt tiền và phát hiện đoàn khách lớn.
- **Cảnh báo.** Cả hai camera gửi lượt vào và ra, camera 1 phát mức cảnh báo Vàng và Đỏ. Với sức chứa mặc định 20 người, Vàng bắt đầu từ 15 người. Đỏ bật khi có trên 20 người liên tục 15 giây và hạ khi còn tối đa 15 người liên tục 15 giây. Quản trị viên đổi sức chứa và giờ mở cửa trong trang **Ngưỡng & giờ hoạt động**.
- **Trực ca và Telegram.** Thêm token bot và chọn loại tin cho từng người nhận trong trang **Người nhận cảnh báo**. Bot hỗ trợ `/tinhhinh`, `/homnay`, `/suco` và nút **Đã xử lý**. Người trực cũng có thể xác nhận, đóng hoặc đánh dấu báo sai trong trang **Trực ca & sự cố**.
- **Phân tích và báo cáo.** Web hiển thị xu hướng, dự báo thời gian chờ, cơ cấu khách, lịch sử và đối chiếu lượt vào với cuống vé. Báo cáo xuất PDF hoặc Excel theo kỳ, kèm biểu đồ nhiệt và các KPI về thời gian quá tải (O1), tốc độ xử lý sự cố (O4), tỷ lệ báo sai (O5) và chênh lệch vé (O8). Backend lập báo cáo ngày sau giờ đóng cửa, gửi báo cáo tuần vào thứ Hai và có thể đồng bộ Google Sheets sau khi lập báo cáo ngày. [Hướng dẫn từng trang và tự động hóa](docs/GHI_CHU_GIAO_DIEN.md)

### Bảng LED hai đầu cầu

Mở bảng LED trên trình duyệt và bấm **F11** để hiển thị toàn màn hình. Trang LED mở trực tiếp từ backend.

| Màn hình | Địa chỉ |
| --- | --- |
| Đầu cầu 1 · Linh Thân đón khách | [Mở bảng LED đầu cầu 1](http://127.0.0.1:8000/led/?dau=1) |
| Đầu cầu 2 · Linh Khuyển đón khách | [Mở bảng LED đầu cầu 2](http://127.0.0.1:8000/led/?dau=2) |
| Hai đầu cầu | [Xem song song](http://127.0.0.1:8000/led/hai-man-hinh.html) |

Bảng LED hiển thị số người, trạng thái và hướng dẫn song ngữ. Khi Đỏ, mascot đổi vai và bảng hiện thời gian chờ dự kiến nếu có. Thêm `&scene=3` vào URL của một đầu cầu để cố định phông nền hoặc dùng `&debug=1` hay phím **D** để thử các mức Xanh, Vàng và Đỏ. Câu thoại, cảnh nền và vai mascot được cấu hình trong [led.js](backend/led_display/led.js).

## Kiểm thử và nghiệm thu AI

Chạy bộ kiểm thử trong một terminal riêng. Bộ test API dùng SQLite trong bộ nhớ. Hai biến dưới đây giúp tách lần chạy khỏi `.env` và cấu hình Google Sheets của máy.

```powershell
$env:PYTHON_DOTENV_DISABLED = "1"
$env:GOOGLE_SHEETS_CREDENTIALS_FILE = "config/pytest-no-credentials.json"
python -m pytest tests -q
```

| Hạng mục | Tiêu chí | Công cụ |
| --- | --- | --- |
| Đếm lượt qua vạch · NFR-02, O2 | Sai số ≤ 15% ở MVP, ≤ 10% khi nghiệm thu, trên ít nhất 3 video có mật độ khác nhau | [eval_counting.py](tools/eval_counting.py) |
| Ước lượng cơ cấu khách · FR-09, NFR-08 | Giới tính ≥ 85%, đúng nhóm tuổi ≥ 55%, lệch tối đa một nhóm tuổi ≥ 85%, chênh lệch giữa các nhóm ≤ 5 điểm phần trăm | [eval_demographics.py](tools/eval_demographics.py) |

Lần đo sơ bộ ngày 15/11/2026 dùng `yolov8n.pt` trên **1 video**. Đếm tay được 6 lượt vào và 3 lượt ra, công cụ đếm được 5 lượt vào và 4 lượt ra, tương ứng sai số **16,7%** và **33,3%**. Lần đo này chưa đạt ngưỡng MVP. Camera khi bật nhận diện mặc định dùng `yolov8n-pose.pt` và cấu hình BoT-SORT riêng.

Để đo lại, tạo CSV đếm tay với các cột `video,true_in,true_out,line`. Đường dẫn video tương đối tính từ thư mục chứa CSV, đường dẫn tệp vạch tương đối tính từ thư mục gốc dự án. Để trống `line` để dùng vạch mặc định.

```powershell
python tools/eval_counting.py --truth video_thu/dem_tay.csv
python tools/eval_demographics.py --dataset fairface --images D:/fairface --labels D:/fairface/fairface_label_val.csv --limit 2000
```

Dùng `--presence` với CSV `video,second,true_count` để đo số người trong khung hình tại từng thời điểm. Hai công cụ xuất báo cáo `.md` và `.csv`. [Quy trình đo và cấu hình AI](docs/AI_CAI_THIEN.md)

## Cấu trúc mã nguồn

| Thư mục | Vai trò |
| --- | --- |
| [`ai_engine/`](ai_engine/) | Xử lý video, theo dõi người, đếm qua vạch, tính cảnh báo và ước lượng cơ cấu khách. |
| [`backend/`](backend/) | API FastAPI, dữ liệu qua SQLAlchemy, nghiệp vụ, bot Telegram, lịch báo cáo và [bảng LED](backend/led_display/). |
| [`frontend/`](frontend/) | Web Streamlit theo vai trò cho người trực, quản lý và quản trị viên. |
| [`tools/`](tools/) và [`tests/`](tests/) | Công cụ demo, kiểm tra mạng, đánh giá AI, chuyển dữ liệu và bộ kiểm thử tự động. |
| [`sample_data/`](sample_data/), [`media/`](media/) và [`docs/`](docs/) | Dữ liệu demo, video mascot và phông nền, tài liệu thiết kế và triển khai. |

Tra cứu thêm trong [tổng quan mã nguồn](docs/TONG_QUAN_MA_NGUON.md), [hợp đồng API](docs/API_CONTRACT.md) và [phân công 7 module](docs/PHAN_CONG.md).
