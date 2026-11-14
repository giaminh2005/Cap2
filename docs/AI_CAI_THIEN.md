# Phân tích và phương án cải thiện độ chính xác AI — SmartCau

Tài liệu này rà soát toàn bộ chuỗi xử lý AI, chỉ ra điểm yếu gây sai số, ghi lại những gì **đã làm trong code** và đề xuất các phương án tiếp theo theo mức công sức. Mọi con số nghiệm thu phải đo bằng `tools/eval_counting.py` và `tools/eval_demographics.py` trên dữ liệu của nhóm, không lấy số công bố của mô hình làm kết quả.

## 1. Chuỗi xử lý hiện tại

| Bước | Thành phần | Điểm yếu chính |
|---|---|---|
| Phát hiện người | YOLOv8n (bản nhỏ nhất), ảnh 640 px | Bỏ sót người ở xa, người bị che khi đông |
| Theo dõi | BoT-SORT | Đổi ID khi hai người đi sát nhau → đếm lặp hoặc bỏ sót lượt qua vạch |
| Đếm vào/ra | Điểm chân qua vạch, có vùng đệm | Phụ thuộc vị trí vạch và góc camera |
| Tìm mặt | Cắt mặt theo 2 mắt + mũi của YOLO-pose (không cần dò mặt); dự phòng: DeepFace + YuNet khi model không có keypoint | Mặt nhỏ, nghiêng, nhòe: đã có cổng chất lượng mặt chặn lại (mục 2) |
| Giới tính, tuổi | **InsightFace (buffalo_s ONNX)** [Mặc định] + **DeepFace (VGG-Face)** [Dự phòng] | Tối ưu cho người châu Á qua ONNX Runtime (~4 ms/mặt), tự fallback DeepFace nếu thiếu ONNX |
| Trong / ngoài nước | DeepFace race → nhóm khu vực | **Không thể** suy ra quốc tịch từ khuôn mặt; khách Việt, Hàn, Nhật, Trung bị gộp |

## 2. Đã làm trong code (dùng ngay)

1. **Tích hợp mô hình InsightFace ONNX chuyên biệt** (`ai_engine/age_gender_estimator.py`, `_load_insightface`, `_predict_genderage_insightface`):
   - Sử dụng model `genderage.onnx` (thuộc bộ `buffalo_s` của InsightFace) thực thi bằng `onnxruntime` CPU (~4 ms/khung mặt).
   - Cắt và căn chỉnh khuôn mặt riêng theo tỷ lệ chuẩn 96×96 (`align_face_for_insightface`, trường nhìn rộng hơn với khoảng cách 2 mắt `eye_span=0.26`, vị trí mắt `eye_y=0.40`).
   - Tự động fallback về DeepFace (`DEMOGRAPHICS_BACKEND="deepface"`) nếu máy chưa có mô hình ONNX.
2. **Cổng chất lượng khuôn mặt** (`ai_engine/visitor_profiler.py`, `face_quality`): chỉ đưa khung hình vào phân tích khi khoảng cách hai mắt ≥ 18 px (mặt đủ to), mũi nằm giữa hai mắt (nhìn gần thẳng), độ nét Laplacian ≥ 45.0 và chiều cao khung người ≥ 130 px. Trên camera hiện gợi ý *Lại gần camera hơn / Chờ nhìn thẳng / Hình bị nhòe*. Tắt bằng `--no-face-gate`.
3. **Bỏ phiếu theo thời gian có trọng số** (`ai_engine/demographics_engine.py`):
   - Cửa sổ bỏ phiếu 8 phiếu gần nhất (`VOTE_WINDOW = 8`), cần tối thiểu 4 phiếu chất lượng (`MIN_VOTES_BEFORE_READY = 4`).
   - Ngưỡng chốt kết quả tin cậy nâng lên 75% (`CONFIDENCE_THRESHOLD = 0.75`), dưới mức này ghi "Không xác định" (BRULE-06).
   - Trọng số phiếu tính theo công thức `(độ chắc - 50%) / 50%` để triệt tiêu ảnh hưởng của khung hình mờ/nghiêng.
4. **Hiệu chỉnh tuổi** (`age_gender_estimator.calibrate_age`): học hệ số `tuổi = a × tuổi_DeepFace + b` trên ảnh có nhãn rồi camera tự áp dụng.
   ```bash
   python tools/eval_demographics.py --dataset utkface --images D:/UTKFace --limit 3000 --save-calibration
   ```
   Hệ số được lưu ở `ai_engine/calibration/age_calibration.json`. Sau khi học, đo lại trên **tập ảnh khác** để có số nghiệm thu trung thực.
5. **Chọn bộ tìm mặt** `--face-detector retinaface`: chính xác hơn YuNet với mặt nghiêng, nhỏ, nhưng chậm hơn vài lần.
6. **Phát hiện người tốt hơn**: thêm `--imgsz 960` (hoặc 1280) và `--model yolov8s.pt` / `yolo11s.pt` (bản pose: `yolov8s-pose.pt`).
7. **Bộ theo dõi chỉnh riêng cho dòng người đi bộ** (`ai_engine/trackers/smartcau_botsort.yaml`): giữ ID tới khoảng 4 giây khi bị che, ngưỡng tạo ID mới cao hơn để giảm ID ảo. Đây là cấu hình mặc định.

### Cấu hình khuyến nghị theo máy

| Máy | Lệnh camera |
|---|---|
| Laptop thường, không GPU | `--imgsz 640` (mặc định, nhận diện bật sẵn) |
| Laptop có GPU NVIDIA | `--model yolov8s-pose.pt --imgsz 960 --face-detector retinaface` |
| Chỉ cần đếm, ưu tiên tốc độ | thêm `--no-demographics` |

## 3. Bố trí camera (ảnh hưởng lớn nhất, không tốn tiền)

- Đặt camera **cao 2,5–3 m**, nhìn xuống **15–30°**, quay về phía khách **đi tới** (thấy mặt khi vào cầu).
- Lối đi chiếm phần lớn khung hình. Mặt người lúc qua vạch nên rộng **≥ 60–80 px** (độ phân giải 1080p).
- Kẻ vạch **vuông góc với hướng đi**, ở chỗ người đi thành hàng (không ở chỗ đứng chụp ảnh). Tránh đặt vạch sát mép hình.
- Tránh ngược sáng; buổi tối cần đèn chiếu vào mặt khách, vì DeepFace kém rõ rệt khi thiếu sáng.

## 4. Phương án nâng cấp tiếp theo

| # | Phương án | Cải thiện | Công sức | Ghi chú |
|---|---|---|---|---|
| A1 | YOLO bản `s`/`m` + `imgsz 960` | Đếm người đông, ở xa | Thấp (đã có cờ) | Cần GPU để giữ ≥ 15 khung/giây (NFR-07) |
| A2 | Bật `with_reid: true` trong tệp tracker | Giảm đổi ID khi đông | Thấp | Chậm hơn; đo lại bằng `eval_counting.py` |
| A3 | Tinh chỉnh YOLO trên 300–500 khung hình quay tại Chùa Cầu (gán nhãn bằng Roboflow/CVAT) | Đếm sát thực tế hiện trường | Trung bình | Cách chắc chắn nhất để đạt sai số ≤ 10% khi nghiệm thu |
| B1 | Thay DeepFace bằng **InsightFace (buffalo_s, genderage.onnx)** | Giới tính, tuổi; nhanh hơn (~4ms) | **Đã hoàn thành** | Chạy ONNX Runtime, tự động fallback DeepFace |
| B2 | **MiVOLO** (dùng cả mặt và dáng người) | Tốt hơn hẳn khi mặt nhỏ / che một phần, đúng bối cảnh camera đám đông | Trung bình–cao | Mô hình trên Hugging Face; cần GPU |
| B3 | Mô hình huấn luyện cân bằng chủng tộc (**FairFace ResNet34**) | Giảm chênh lệch giữa nhóm khách (NFR-08) | Trung bình | Đúng tập FairFace mà Sprint 0 đã chọn |
| B4 | Tinh chỉnh trên ảnh khách Việt có đồng ý (mô hình đa nhiệm theo Sprint 0) | Tốt nhất cho khách Việt | Cao | Cần quy trình xin đồng ý, không lưu ảnh sau huấn luyện |
| C1 | Lấy tỷ lệ khách quốc tế từ **số vé quốc tế** (FR-15) hoặc **QR khai báo** | Số trong/ngoài nước **đúng** | Thấp–trung bình | Khuyến nghị thay cho ước lượng từ khuôn mặt |

Khuyến nghị cho học kỳ: làm **A1 + cổng chất lượng + hiệu chỉnh tuổi** (đã có), đo bằng 2 script, rồi chọn **B1 hoặc B3** nếu giới tính chưa đạt 85%. Với "trong/ngoài nước", nên ghi rõ trong báo cáo đây là ước lượng minh họa và đề xuất **C1** cho giai đoạn triển khai.

## 5. Quy trình đo để nghiệm thu

1. Quay **≥ 3 video** tại hai chân cầu: vắng, trung bình, đông (mỗi video 3–5 phút).
2. Hai người **đếm tay độc lập** lượt vào/ra mỗi video, lấy trung bình. Ghi vào `dem_tay.csv`.
3. Chạy `python tools/eval_counting.py --truth dem_tay.csv` với từng cấu hình (mặc định, `--imgsz 960`, model `s`), chọn cấu hình tốt nhất trong giới hạn tốc độ.
4. Tải FairFace (tập val) và UTKFace, chạy `tools/eval_demographics.py` (trước và sau hiệu chỉnh tuổi), dán bảng `.md` vào báo cáo.
5. Ghi lại cấu hình đã chọn (model, imgsz, face-detector, vị trí vạch) để vận hành thử dùng đúng cấu hình đó.


## Cập nhật: tích hợp InsightFace và nhận diện Nam/Nữ nhanh, chính xác

| Vấn đề cũ | Nguyên nhân | Đã cải tiến trong code |
|---|---|---|
| Chậm khi dùng DeepFace | DeepFace phải tự tìm mặt trong cả khung người mỗi lần; chạy 3 mô hình (tuổi, giới tính, chủng tộc) mỗi lần | Tích hợp **InsightFace genderage.onnx** qua ONNX Runtime (~4 ms/khung). Cắt mặt sẵn 96×96 theo 2 mắt + mũi; mô hình chủng tộc DeepFace chỉ chạy tối đa 4 lần mỗi người; đã chốt kết quả thì phân tích thưa lại (1,5 giây) |
| Lấy nhầm mặt người bên cạnh | Chọn mặt "gần tâm khung người", mà tâm khung người nằm ngang bụng | Mặt cắt đúng theo keypoints của chính người đó |
| Mặt nghiêng, nhỏ → đoán sai | Mặt không được căn chỉnh đúng trường nhìn | Căn chỉnh affine xoay 2 mắt nằm ngang, cắt chuẩn 96×96 (InsightFace) hoặc 224×224 (DeepFace) |
| Một khung "55%" kéo sai kết quả | Trọng số phiếu = độ chắc (55% ≈ 99%) | Trọng số = (độ chắc − 50%) / 50%, cửa sổ 8 phiếu, cần ≥ 4 phiếu, ngưỡng tin cậy 75% |
| Ảnh mơ hồ | — | Dưới 85% chắc chắn thì phân tích thêm ảnh lật gương (TTA), lấy trung bình |

Thanh dưới cửa sổ camera hiện `mặt xx ms`: thời gian một lần phân tích mặt. Hệ thống mặc định ưu tiên sử dụng InsightFace ONNX để đạt độ chính xác cao cho khách châu Á và tự động chuyển sang DeepFace khi môi trường chưa có mô hình ONNX.
