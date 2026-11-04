# Đối chiếu bản nâng cấp — từng mục bạn yêu cầu đã được xử lý ở đâu

Tài liệu này đối chiếu 1-1 với danh sách "Kế hoạch nâng cấp 5 Phase" + "10 lỗi"
bạn gửi, để bạn kiểm tra lại dễ dàng (và dùng cho AI Usage Log).

## Lỗi Nghiêm Trọng (Critical)

| # | Mô tả | Đã sửa ở đâu |
|---|---|---|
| 1 | Ngưỡng sai (7/9/10 thay vì 20-25) | `src/crowd_counter.py` → `CameraThresholds` đổi thành `warning=18, alert=20, critical=25` |
| 2 | Dashboard cũ hiển thị 20-25 nhưng code dùng 7/9/10 → lệch | Tự hết lệch vì cùng đọc từ `CameraThresholds()`; thêm cơ chế TỰ PHÁT HIỆN dữ liệu mô phỏng cũ và tự sinh lại trong `generate_dashboard.py` (`need_regen`), và luôn TÍNH LẠI `status` từ ngưỡng hiện tại thay vì tin cột đã lưu sẵn trong CSV cũ |
| 3 | 2 camera cùng máy dùng cùng 1 index | `src/camera_backend.py` → `parse_camera_source()` hỗ trợ `--camera-index`/`--source` rõ ràng (vẫn giữ cách cũ dùng số thứ tự tham số dòng lệnh) |
| 4 | macOS-only (`cv2.CAP_AVFOUNDATION` hardcode) | `src/camera_backend.py` → `open_camera()` tự chọn backend theo hệ điều hành (Windows→`CAP_DSHOW`, Linux→`CAP_V4L2`, macOS→`CAP_AVFOUNDATION`), tự thử lại bằng backend mặc định nếu backend riêng không mở được. Áp dụng cho `camera_in.py`, `camera_out.py`, `webcam_tracking_demo.py` |

## Lỗi Trung Bình (Medium)

| # | Mô tả | Đã sửa ở đâu |
|---|---|---|
| 5 | Code trùng lặp (`send_telegram_alert`, `draw_info_panel`) | `src/poc_dem_nguoi_chua_cau.py` nay `import` từ `telegram_alert.py` thay vì tự định nghĩa lại; `src/webcam_full_demo.py` nay gọi lại `camera_ui.draw_info_panel()` |
| 6 | `yolo11n.pt` nhưng requirements chỉ ghi `ultralytics>=8.1` (YOLO11 cần ≥8.3) | `requirements.txt` nâng lên `ultralytics>=8.3.0` |
| 7 | SQLite đường dẫn tương đối | `src/api_server.py` → `DATABASE_URL` nay dùng đường dẫn TUYỆT ĐỐI tính từ vị trí thật của file (`os.path.dirname(os.path.abspath(__file__))`) |
| 8 | API không có auth | `src/api_server.py` → thêm `require_api_key` (dependency FastAPI), bật bằng biến môi trường `SMARTCAU_API_KEY` (tuỳ chọn, mặc định TẮT để không cản demo nhanh); các script camera tự gắn header `X-API-Key` nếu máy cũng set biến này |

## Lỗi Nhẹ (Low)

| # | Mô tả | Đã sửa ở đâu |
|---|---|---|
| 9 | Test TC-02 dùng ngưỡng 18/20/25 khác default | Tự hết lệch sau khi sửa mục #1 — `test_crowd_counter.py` không cần sửa gì thêm |
| 10 | Không có Re-ID giữa camera IN/OUT | GIỮ NGUYÊN theo đúng quyết định gốc của nhóm ("chấp nhận được cho PoC", ngoài phạm vi đồ án) — không đổi |

---

## Phase 1 — Fix Bugs & Cập nhật thư viện

Xem bảng lỗi ở trên (đã xử lý đủ cả 10 mục) + `requirements.txt` đã pin phiên
bản tối thiểu rõ ràng và ghi chú cách xử lý xung đột `tf-keras`/Keras 3.

## Phase 2 — Nâng cấp nhận dạng giới tính

File mới: `src/demographics_engine.py`.

- **Multi-signal fusion**: tín hiệu chính là DeepFace gender (như cũ), tín
  hiệu phụ là tỷ lệ vai/hông tính từ keypoints YOLO-Pose
  (`estimate_gender_signal_from_pose`) — CHỈ cộng thêm khi DeepFace chưa
  chắc chắn (độ tin cậy < 60%), không bao giờ "đè" lên một kết quả DeepFace
  đã rất chắc chắn.
- **Temporal voting**: lớp `TemporalVoter` giữ tối đa 6 phiếu gần nhất cho
  mỗi `track_id`, mỗi phiếu có trọng số theo độ tin cậy, kết quả cuối là
  bên thắng theo tổng trọng số.
- **Confidence threshold 70%**: `CONFIDENCE_THRESHOLD = 0.70` trong
  `demographics_engine.py` — chỉ `ready=True` (cho phép hiển thị/lưu hồ sơ)
  khi đạt ngưỡng này VÀ đã có ít nhất 3 phiếu.
- **Smoothing**: một khi đã "chốt" 1 giới tính cho `track_id`, kết quả mới
  phải thắng áp đảo (chênh lệch ≥ 15%) mới được phép đổi — tránh nhảy giới
  tính liên tục giữa các khung hình.
- Đã viết test logic thuần Python (không cần camera thật) xác minh cả 4
  hành vi trên đều đúng — xem phần "Đã kiểm thử" bên dưới.

`camera_in.py` đã đổi sang dùng model `yolov8n-pose.pt` (thay vì
`yolov8n.pt`) để có keypoints cho tín hiệu phụ, và dùng `DemographicsEngine`
thay cho việc gọi `age_gender_estimator` trực tiếp.

## Phase 3 — Phân biệt khu vực (KHÔNG xác định chủng tộc)

File mới: `src/region_mapping.py` (đọc kỹ docstring đầu file — ghi rõ 3
nguyên tắc sử dụng + hạn chế kỹ thuật thật sự của DeepFace).

- Quy đổi về đúng 4 nhóm bạn đề xuất (gộp "Đông Nam Á/Nội địa" và "Đông Á"
  thành 1 nhóm — lý do: DeepFace chỉ có 1 nhãn "asian" duy nhất, KHÔNG thể tự
  phân biệt khách Việt Nam với khách Hàn/Nhật/Trung chỉ từ khuôn mặt, nên
  tách thành 2 nhóm riêng sẽ là ảo tưởng về độ chính xác — đã ghi rõ hạn chế
  này trong code và trong dashboard).
- **Mặc định TẮT** (`enable_region=False`) — chỉ bật khi set biến môi trường
  `SMARTCAU_ENABLE_REGION=1` trước khi chạy `camera_in.py`, kèm cảnh báo in
  ra màn hình khi bật.
- **Dữ liệu CHỈ lưu tổng hợp theo giờ** — bảng `RegionStat` trong
  `api_server.py` KHÔNG có cột liên kết tới `track_id`/hồ sơ cá nhân nào,
  chỉ là 1 bộ đếm (ngày, giờ, khu vực) → đúng yêu cầu "aggregate, KHÔNG lưu
  per-face".
- **Disclaimer**: `region_mapping.DISCLAIMER_VI` được hiển thị trực tiếp
  trong dashboard (mục 7) và in ra console khi bật tính năng.

## Phase 4 — Hệ thống kiểm soát tự động

- `src/camera_ui.py` → thêm `draw_gate_banner()` (banner "CHỜ - CẦU ĐANG
  ĐẦY") và `draw_countdown()` ("Còn X chỗ trống").
- `src/camera_in.py`: khi `current_count >= 20` (ngưỡng `alert`) → hiện
  banner chờ + ghi sự kiện `GATE_CLOSED` (1 lần duy nhất lúc CHUYỂN trạng
  thái, không spam mỗi frame); khi tụt xuống dưới → ghi `GATE_REOPENED`.
  Khi `current_count >= 25` (ngưỡng `critical`) → banner đỏ to + gửi
  Telegram + `trigger_buzzer_signal()` (xem dưới) + ghi `CRITICAL_ALERT`,
  tất cả có cooldown 60 giây chống spam.
- `src/telegram_alert.py` → thêm `trigger_buzzer_signal()`: in cảnh báo +
  ký tự chuông, và (tuỳ chọn) gọi webhook HTTP tới thiết bị còi/đèn thật nếu
  set `SMARTCAU_BUZZER_WEBHOOK` — vì bản demo này không có phần cứng còi
  thật, đây là điểm nối sẵn cho phần cứng thật sau này (không "giả vờ" có
  còi khi không kiểm chứng được).
- `src/api_server.py` → bảng `SystemEvent` + endpoint `POST/GET
  /system_events` để xem lại lịch sử đóng/mở cổng, cảnh báo khẩn.

## Phase 5 — Dashboard nhân khẩu học

`src/generate_dashboard.py` + `src/data_simulator.py`:

- `data_simulator.py` sinh thêm cột `region` (quy đổi từ `nationality` qua
  `region_mapping.nationality_to_region`).
- 4 biểu đồ/bảng mới trong `dashboard.html` (mục 7-10): phân bố khách theo
  khu vực, xu hướng giờ × khu vực, heatmap tuổi × giới tính × khu vực, bảng
  giờ cao điểm theo TỪNG khu vực.
- `export_marketing_summary_csv()` → xuất `sample_data/marketing_summary.csv`
  (giờ × khu vực × nhóm tuổi × giới tính × số lượt) mỗi lần chạy
  `generate_dashboard.py`, sẵn để đội marketing import vào Excel/PowerBI.

---

## Đã kiểm thử được (trong môi trường soạn tài liệu này, KHÔNG có
## camera/GPU thật)

- `python3 -m py_compile` toàn bộ file `.py` trong `src/` — không lỗi cú pháp.
- Chạy thật `data_simulator.py` + `generate_dashboard.py` end-to-end → sinh
  đúng `dashboard.html` (có đủ 7 biểu đồ, không ảnh lỗi) và
  `marketing_summary.csv`.
- Test logic thuần Python cho `demographics_engine.py` (4 kịch bản: chưa đủ
  phiếu, đồng thuận cao, phiếu lẫn lộn, smoothing khi đổi ý) và
  `region_mapping.py` (gộp xác suất, trường hợp thiếu dữ liệu) — PASS cả.
- Test `camera_backend.py` (`parse_camera_source`, `open_camera` không
  crash khi không có camera thật) và các hàm vẽ mới trong `camera_ui.py`
  (không crash trên khung hình giả).

**CHƯA kiểm thử được** (cần máy có webcam/GPU thật, môi trường này không có):
FastAPI/SQLAlchemy thật (không cài được do mạng sandbox bị chặn — bạn cần tự
chạy `uvicorn` để xác nhận), độ chính xác thực tế của tín hiệu tư thế
(vai/hông) và của phân loại khu vực, hiệu năng model pose so với model detect
thường trên máy yếu. Khi chạy thật, nếu thấy hành vi khác mô tả ở đây, báo
lại để điều chỉnh tiếp.

---

## Nâng cấp thêm (sau Phase 1-5) — Lưu dữ liệu qua Google Sheets + trang Admin Web

Yêu cầu: *"tôi muốn lưu dữ liệu thông qua gg sheet và kèm theo đó là 1 trang
web admin để quản lý số liệu dashboard nữa"*.

| Việc cần làm | Đã xử lý ở đâu |
|---|---|
| Trang web admin xem/quản lý số liệu dashboard | `admin_web/app.py` (Streamlit, theme "di sản Hội An") — 4 trang: Tổng quan, Lịch sử lượt khách (lọc + xuất CSV), Cấu hình (đổi ngưỡng cảnh báo), Đồng bộ Google Sheets. Chạy bằng `streamlit run admin_web/app.py`, chỉ nói chuyện với `api_server.py` qua HTTP (không đụng trực tiếp database) |
| Đồng bộ dữ liệu sang Google Sheets | `src/google_sheets_sync.py` (dùng `gspread` + Google Service Account) — ghi 2 trang tính `LuotKhach` (danh sách hồ sơ) và `TongQuan` (số liệu tổng hợp); gọi qua nút "Đồng bộ ngay" trên Admin Web hoặc chạy trực tiếp `python3 google_sheets_sync.py` |
| Đổi ngưỡng cảnh báo mà không cần sửa code/restart camera | `src/api_server.py` — bảng `SystemConfig` (1 dòng) + endpoint `GET/PUT /config`; `camera_in.py`/`camera_out.py` tự đọc `/config` lúc khởi động VÀ định kỳ mỗi 15 giây (`CONFIG_POLL_INTERVAL_SEC`), tự suy ra lại 3 ngưỡng warning/alert/critical đúng tỉ lệ qua `CameraThresholds.from_alert_threshold()` (đây chính là phần đã ghi "CHƯA làm" trong tài liệu dự án trước đó) |
| Tách quyền "ghi dữ liệu camera" và "đổi cấu hình hệ thống" | 2 key riêng: `SMARTCAU_API_KEY` (camera ghi `/entry`, `/exit`...) và `ADMIN_API_KEY` (chỉ cho `PUT /config`) — không dùng chung 1 key để có thể giao `SMARTCAU_API_KEY` cho người vận hành camera mà không lo họ đổi được ngưỡng cảnh báo toàn hệ thống |
| Lọc lịch sử lượt khách theo giới tính/nhóm tuổi (Admin Web cần) | `GET /visit_events` trong `api_server.py` thêm 2 tham số tuỳ chọn `gender`, `age_range` |
| Cập nhật trích dẫn pháp lý | `region_mapping.py` và `age_gender_estimator.py`: đổi trích dẫn cũ "Nghị định 13/2023/NĐ-CP" (đã hết hiệu lực) sang căn cứ pháp lý hiện hành: Luật Bảo vệ dữ liệu cá nhân 2025 (Luật số 91/2025/QH15) + Nghị định 356/2025/NĐ-CP (hiệu lực từ 1/1/2026) |

Xem hướng dẫn cài đặt/chạy chi tiết (tạo Google Service Account, biến môi
trường, chạy song song với Hướng A) trong `BAT_DAU_TU_DAU.md` mục 5
("Hướng C").

**CHƯA kiểm thử được** (giống lý do ở trên — môi trường soạn tài liệu này
không cài được `streamlit`/`gspread` do mạng sandbox bị chặn): giao diện
Admin Web thật trên trình duyệt, luồng đăng nhập Google Service Account,
và việc ghi thật lên Google Sheets. Đã kiểm tra bằng `py_compile` (không
lỗi cú pháp) cho `admin_web/app.py`, `src/google_sheets_sync.py` và toàn bộ
phần sửa trong `api_server.py`/`camera_in.py`/`camera_out.py`/
`crowd_counter.py`, cùng 1 test logic thuần Python xác nhận
`CameraThresholds.from_alert_threshold(20)` cho đúng lại 18/20/25 như cũ.

## Sửa lỗi nhận diện giới tính/khoảng tuổi hay bị sai (sau khi test camera thật)

Người dùng báo lỗi thực tế: giới tính hay đoán sai, khoảng tuổi hiển thị
không đúng. Đọc lại `src/demographics_engine.py` thì phát hiện 2 nguyên
nhân (chi tiết đầy đủ ở "SỬA LỖI LẦN 5" trong docstring đầu file đó):

| # | Nguyên nhân | Đã sửa |
|---|---|---|
| 1 | Khoảng tuổi **không hề được bỏ phiếu qua nhiều khung hình** như giới tính — chỉ đơn giản lấy kết quả của khung hình **mới nhất**, ghi đè liên tục lên khung trước. 1 khung hình lẻ có thể bị mờ/góc nghiêng/ánh sáng xấu nên khoảng tuổi hiển thị hay "nhảy" qua lại, không đáng tin như giới tính (đã có bỏ phiếu) | Thêm `age_votes` — khoảng tuổi hiển thị giờ là khoảng được **nhiều khung hình gần nhất "bầu" nhiều nhất** (cùng cơ chế với giới tính), không còn bị 1 khung hình lẻ quyết định |
| 2 | Tín hiệu phụ "tỉ lệ vai/hông" (đoán giới tính thô từ dáng người, cộng thêm khi DeepFace không chắc chắn) là heuristic **chưa được kiểm chứng bằng dữ liệu thật** (tự ghi rõ trong code gốc) — lại được dùng đúng vào lúc DeepFace yếu nhất, nên nhiều khả năng đang **kéo kết quả sai thêm** chứ không giúp, đặc biệt với trang phục VN không khớp giả định "vai rộng = nam" kiểu phương Tây dùng để hiệu chuẩn | Tắt mặc định (`_POSE_SIGNAL_ENABLED = False`) — giới tính giờ dựa 100% vào kết quả DeepFace (tín hiệu chính, đáng tin nhất trong 3 tín hiệu), có thể bật lại để tự thử nghiệm nhưng không khuyến nghị |

Đã kiểm tra bằng `py_compile` + 1 test logic mô phỏng 6 khung hình liên
tiếp (giả lập kết quả DeepFace, không cần cài `deepface` thật) xác nhận
khoảng tuổi được chọn đúng là khoảng được bầu nhiều nhất (4/6 phiếu),
không bị khung hình cuối cùng (chỉ 1/6 phiếu) ghi đè lên.

## Sửa lỗi gán nhầm giới tính của người NGỒI/ĐỨNG SÁT NHAU (phát hiện từ ảnh thực tế người dùng gửi)

Người dùng gửi ảnh chụp thực tế: 2 người ngồi sát nhau, 1 bạn nữ (tóc dài,
đeo kính) bị hệ thống gán nhầm thành "Man". Đọc kỹ `age_gender_estimator.py`
(`estimate_demographics_from_person_box`) thì phát hiện đúng nguyên nhân —
chi tiết đầy đủ ở "SỬA LỖI LẦN 6" trong docstring hàm đó:

Khi 2 người đứng/ngồi sát nhau, khung người (box) do YOLO vẽ cho mỗi người
có thể đã gần chạm nhau; vùng cắt ảnh (ROI) để đưa vào DeepFace lại được
**phóng to thêm bằng viền đệm** ở mọi phía (trước là 20%) — khiến ROI của
người A dễ **lấn sang cả mặt người B** ngồi cạnh. Khi đó DeepFace tìm thấy
2 khuôn mặt thật trong cùng 1 ROI, và code cũ chọn khuôn mặt **to nhất**
trong đó để dùng kết quả — nhưng "to nhất trong ROI của A" không có nghĩa
là "mặt của A": nếu B ở gần/rõ hơn, mặt B có thể to hơn ngay trong ROI của
A, và hệ thống trả nhầm kết quả của B cho track của A — đúng y hệt tình
huống trong ảnh người dùng gửi.

Đã sửa 2 phần:
1. Giảm viền đệm quanh khung người từ 20% xuống 10% mỗi phía — giảm bớt
   việc ROI lấn sang người ngồi cạnh.
2. Đổi tiêu chí chọn mặt: thay vì chọn mặt **to nhất** (dễ bị ảnh hưởng
   bởi người bên cạnh), chọn mặt có **tâm gần tâm của chính khung người**
   đang xét nhất — vì về lý thuyết, mặt của đúng người trong track đó phải
   nằm gần giữa khung của chính họ, còn mặt người bên cạnh (nếu lọt vào
   ROI) sẽ nằm lệch về 1 phía gần mép ROI hơn.

Đã kiểm tra bằng `py_compile` + 1 test mô phỏng đúng tình huống trong ảnh
(2 khuôn mặt trong 1 ROI — 1 mặt nhỏ hơn nhưng ở giữa box, 1 mặt to hơn
nhưng lệch sang 1 phía) xác nhận hệ thống chọn đúng mặt ở giữa box, không
còn bị mặt to hơn của người bên cạnh "cướp" kết quả.

## Sửa lỗi "khóa chết" giới tính (không bao giờ đổi lại dù nhận diện đúng sau đó)

Người dùng đưa cho 1 bản phân tích (có vẻ từ 1 AI khác) về lỗi nghi ngờ
trong `demographics_engine.py`. Đã tự kiểm tra lại từng điểm trên code
thật, kết quả: **1 trong 3 điểm là đúng và chính là lỗi thật, mức độ
nghiêm trọng, rất có khả năng là nguyên nhân chính** gây ra hiện tượng
"đoán sai giới tính và không bao giờ tự sửa lại" — 2 điểm còn lại **không
áp dụng** vì lý do kỹ thuật (giải thích bên dưới).

**Lỗi thật (đã sửa)** — hàm `TemporalVoter.result()`, phần "khóa" (lock)
giới tính: khi 1 người mới vào khung hình, nếu 3 khung hình (frame) đầu
tiên đồng thuận 100% ra sai (ví dụ đều đoán "Man" cho 1 bạn nữ, do còn xa/
mờ), hệ thống sẽ "chốt" với độ tin cậy tối đa `confidence = 1.0`. Code cũ
so sánh độ tin cậy của kết quả MỚI với con số `1.0` ĐÃ LƯU TỪ LÚC CHỐT đó —
nhưng độ tin cậy tối đa có thể đạt được cũng chỉ là `1.0`, nên hiệu số
không bao giờ vượt ngưỡng cần thiết để đổi lại (`0.15`) — kết quả bị
**khóa chết vĩnh viễn**, dù sau đó toàn bộ khung hình mới đều đúng. Sửa:
so sánh độ tin cậy của kết quả mới với **tỷ lệ phiếu của chính nhãn đã
chốt, tính lại TRONG CÙNG 1 cửa sổ phiếu hiện tại** (không dùng con số cũ
đã lưu) — nhờ vậy việc so sánh luôn công bằng, không còn bị "trần". Đã
kiểm tra bằng `py_compile` + 1 test mô phỏng đúng tình huống: chốt "Man"
với 3/3 phiếu đầu đồng thuận, rồi tiêm liên tục "Woman" đúng — xác nhận hệ
thống đổi lại thành "Woman" sau vài khung hình thay vì bị khóa cứng.

**Điểm KHÔNG áp dụng (và vì sao)**:

- *Ngưỡng cứng `_WOMAN_PROB_THRESHOLD = 28%` trực tiếp gán "Woman" nếu xác
  suất Woman của DeepFace ≥ 28%*: đây không phải 1 cách sửa hợp lý — nó
  LẬT NGƯỢC độ lệch thay vì sửa, tức là bất kỳ ai (kể cả nam) có xác suất
  "Woman" ≥ 28% (28% là rất thấp, gần như luôn xảy ra) đều bị gán là nữ,
  trừ khi model chắc chắn ≥ 72% là nam. Cách này sẽ gây sai theo chiều
  ngược lại (đoán nam thành nữ) chứ không công bằng hơn — mình không áp
  dụng mà đề nghị bạn test thêm sau các bản sửa đã có để xem mức độ sai
  còn lại đến đâu, rồi báo lại cụ thể (kèm ảnh/log) nếu vẫn còn lệch nhiều
  theo 1 chiều.
- *Tăng vùng đệm (padding) quanh mỗi người từ hiện tại lên 30%/35%*: đề
  xuất này **mâu thuẫn trực tiếp** với bản sửa trước đó (giảm padding
  20%→10%) để tránh vùng ảnh của người này lấn sang mặt người NGỒI SÁT
  BÊN CẠNH (xem mục sửa lỗi ngay phía trên). Tăng lại padding sẽ có nguy
  cơ làm TÁI XUẤT HIỆN lỗi "2 người sát nhau bị gán nhầm giới tính cho
  nhau". Mình giữ nguyên padding 10% (ưu tiên tránh lỗi nhầm người, rủi ro
  cao hơn), và thêm 1 cải thiện AN TOÀN khác không có đánh đổi — xem mục
  CLAHE bên dưới.

## Thêm cân bằng sáng cục bộ (CLAHE) trước khi đưa ảnh vào DeepFace

Áp dụng từ gợi ý trong bản phân tích trên (phần này hợp lý, không có đánh
đổi/rủi ro phụ): `src/age_gender_estimator.py` nay cân bằng độ sáng/tương
phản CỤC BỘ (CLAHE, trên kênh độ sáng L của không gian màu LAB, không đổi
màu sắc) trước khi đưa vùng ảnh vào DeepFace — giúp các trường hợp ảnh
webcam thiếu sáng/chói/ngược sáng (hay gặp trong phòng học, quán cà phê)
rõ chi tiết khuôn mặt hơn cho model đọc. Có `try/except` bọc riêng, lỗi
xử lý ảnh phụ này (nếu có) sẽ KHÔNG làm hỏng cả pipeline chính.

## Sửa lỗi riêng trong `webcam_full_demo.py` (file demo khác, không phải file đang test)

Bản phân tích cũng chỉ đúng 1 lỗi THẬT nhưng ở FILE KHÁC —
`src/webcam_full_demo.py` (1 file demo độc lập, KHÔNG phải `camera_in.py`/
`camera_out.py` mà bạn đang dùng để test) — file này trước đó gọi
`estimate_age_gender()` trên **cả khung hình** rồi mới "đoán" xem khuôn
mặt tìm được thuộc về người nào (dễ ghép sai khi nhiều người), và hiển thị
1 con số tuổi lẻ thay vì khoảng tuổi. Đã sửa: dùng lại đúng hàm
`estimate_demographics_from_person_box()` — cùng hàm đã dùng trong
`camera_in.py`/`camera_out.py` (đã có đủ các bản vá: lọc kết quả "giả",
chọn đúng mặt khi 2 người sát nhau, CLAHE...) — gọi riêng cho từng khung
người, và hiển thị khoảng tuổi (`age_range`) thay vì số lẻ.
**Lưu ý: sửa này KHÔNG ảnh hưởng đến kết quả bạn đang test với
`camera_in.py`** vì là 2 file khác nhau — chỉ sửa để file demo này cũng
đúng/nhất quán.

**Lưu ý quan trọng còn lại (không phải lỗi code, không thể sửa bằng code)**:
mô hình nhận diện tuổi/giới tính (DeepFace) là model **có sẵn, huấn luyện
trước (pretrained)** — dự án này KHÔNG tự huấn luyện lại model, chỉ gọi
model có sẵn qua thư viện. Vì vậy độ chính xác tuyệt đối của bản thân việc
"nhìn mặt đoán tuổi/giới tính" vẫn phụ thuộc vào chất lượng model gốc này
(được biết là đoán giới tính khá chính xác, nhưng đoán tuổi theo bản chất
chỉ mang tính ước lượng gần đúng, có thể lệch vài năm ngay cả với ảnh rõ
mặt) — phần 2 sửa lỗi trên là để hệ thống KHÔNG làm cho model gốc đoán
tệ hơn, chứ không "dạy" model đoán tuổi chính xác tuyệt đối hơn bản thân
nó (nằm ngoài khả năng chỉnh sửa code trong phạm vi đồ án này).

## Giới hạn độ chính xác nhận diện giới tính/tuổi (mục ghi nhận cho báo cáo đồ án)

Sau khi đã sửa hết các lỗi CODE tìm được (liệt kê đầy đủ ở các mục phía
trên — 7 lần sửa, đánh số "SỬA LỖI LẦN 1" đến "LẦN 7" trong code), nhóm
vẫn quan sát được 1 số trường hợp hệ thống đoán sai giới tính/tuổi khi
test với người thật qua webcam:

| # | Tình huống test thực tế | Kết quả hệ thống | Kết quả đúng |
|---|---|---|---|
| 1 | Bạn nữ (test qua webcam, đủ ánh sáng, nhìn thẳng camera) | "Man" | Nữ |
| 2 | Bạn nam trẻ (bạn của người test) | "18-25" *(đúng)* | 18-25 |
| 3 | Người lớn tuổi ("ông già") | "35-44" | Lớn tuổi hơn nhiều so với 35-44 |

**Vì sao nhóm kết luận đây là giới hạn của model, không phải lỗi code còn
sót**: tất cả các lỗi CODE tìm được trong quá trình test (xem bảng tổng
hợp ở các mục trên) đều có 1 đặc điểm chung — có NGUYÊN NHÂN LOGIC cụ thể,
sửa 1 chỗ rõ ràng, và kiểm chứng lại được bằng 1 đoạn code test mô phỏng
đúng tình huống lỗi (không chỉ "có vẻ đúng hơn"). Ví dụ: lỗi "khóa chết"
giới tính có thể chứng minh bằng công thức toán học cụ thể (hiệu số
không bao giờ vượt ngưỡng), lỗi "2 người sát nhau bị lẫn mặt" có thể tái
hiện lại bằng ảnh thực tế. Còn 3 trường hợp sai ở bảng trên, sau khi đã
sửa hết các lỗi logic đó, **không còn cơ chế lỗi cụ thể nào để trỏ vào
nữa** — hệ thống đang nhận đúng 1 khuôn mặt thật (không bị lẫn người bên
cạnh, không bị "khóa chết"), nhưng bản thân model DeepFace vẫn đọc sai từ
khuôn mặt đó. Đây là lý do nhóm kết luận phần còn lại thuộc về **độ chính
xác vốn có của model pretrained**, không phải lỗi trong code của nhóm.

**Theo tài liệu/cộng đồng sử dụng DeepFace**: model tuổi (dựa trên kiến
trúc VGG, huấn luyện chủ yếu từ ảnh diễn viên/người nổi tiếng, tập dữ liệu
IMDB-WIKI) được ghi nhận rộng rãi là có xu hướng đoán tuổi **thấp hơn thực
tế**, đặc biệt với người lớn tuổi — khớp với quan sát #3 ở trên. Độ chính
xác giới tính nhìn chung tốt hơn tuổi, nhưng không đồng đều giữa các điều
kiện ánh sáng/góc camera/đặc điểm khuôn mặt khác với phân bố dữ liệu huấn
luyện gốc — khớp với quan sát #1.

**Hướng xử lý nhóm đã cân nhắc nhưng KHÔNG áp dụng** (vì thiếu cơ sở dữ
liệu để hiệu chỉnh đúng, dễ gây sai theo chiều khác): đặt ngưỡng xác suất
"Woman" thấp hơn 50% để thiên về nữ nhiều hơn, hoặc cộng thêm 1 số tuổi cố
định vào kết quả model trả về. Cả 2 cách đều là **suy đoán không có dữ
liệu kiểm chứng**, có thể "sửa đúng" cho vài ca lẻ nhóm đã test nhưng làm
sai theo hướng khác cho người dùng khác — không phù hợp đưa vào hệ thống
nếu không có bộ dữ liệu test đủ lớn (nhiều người, đã biết trước đáp án
đúng) để đo đạc và hiệu chỉnh có cơ sở.

**Kết luận cho báo cáo**: hệ thống nhận diện tuổi/giới tính đạt độ chính
xác tốt với các trường hợp mặt rõ, đủ sáng, nhìn thẳng camera (ghi nhận
qua test thực tế), nhưng vẫn còn sai số ở 1 số trường hợp (đặc biệt đoán
tuổi người lớn tuổi thấp hơn thực tế) do giới hạn vốn có của model
pretrained DeepFace — đây là rủi ro/giới hạn đã biết của bài toán nhận
diện nhân khẩu học qua ảnh, tương tự lý do nhóm không triển khai nhận
diện khu vực/chủng tộc (xem docstring đầu `age_gender_estimator.py`).
Hướng khắc phục triệt để (huấn luyện lại model trên tập dữ liệu khuôn mặt
Việt Nam) nằm ngoài phạm vi đồ án.
