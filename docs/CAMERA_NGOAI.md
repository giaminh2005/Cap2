# Dùng webcam USB hoặc điện thoại làm camera chân cầu

Mỗi chân cầu cần 1 camera **riêng**. Webcam của laptop chỉ dùng được cho 1 chân cầu; chân cầu còn lại dùng **webcam cắm USB** hoặc **camera điện thoại**. Mọi cách đều chỉ khác nhau ở tham số `--source`.

| Loại camera | `--source` | Ví dụ |
|---|---|---|
| Webcam laptop | `0` | `--source 0` |
| Webcam USB | `1` (hoặc `2`) | `--source 1` |
| Điện thoại Android, ứng dụng **IP Webcam** | `phone:<IP>` | `--source phone:192.168.1.23` |
| Điện thoại Android / iPhone, ứng dụng **DroidCam** | `droidcam:<IP>` | `--source droidcam:192.168.1.23` |
| Camera IP / camera an ninh (RTSP) | địa chỉ `rtsp://...` | `--source rtsp://admin:matkhau@192.168.1.40:554/stream1` |
| Tệp video quay sẵn | đường dẫn tệp | `--source D:\video\chan_cau_2.mp4` |

## 1. Webcam USB
1. Cắm webcam vào laptop.
2. Dò số của từng camera (tắt Zoom / Meet / ứng dụng Camera trước):
   ```
   python tools/tim_camera.py
   ```
   Công cụ in độ phân giải, tốc độ khung hình và lưu ảnh chụp thử vào `tools/anh_camera/` (`webcam_0.jpg`, `webcam_1.jpg`...) để biết số nào là camera nào.
3. Chạy hai chân cầu trên cùng một laptop (2 cửa sổ lệnh):
   ```
   python ai_engine/camera_bridge.py --camera-id 1 --source 0 --api http://127.0.0.1:8000
   python ai_engine/camera_bridge.py --camera-id 2 --source 1 --api http://127.0.0.1:8000
   ```

## 2. Điện thoại Android — ứng dụng IP Webcam (miễn phí)
1. Cài **IP Webcam** (tác giả Pavel Khlebovich) từ CH Play.
2. Điện thoại và laptop vào **cùng một mạng Wi-Fi** (hoặc laptop bắt điểm phát của chính điện thoại đó).
3. Trong ứng dụng: *Video preferences → Video resolution* chọn **1280x720**; kéo xuống cuối bấm **Start server**. Màn hình hiện địa chỉ, ví dụ `http://192.168.1.23:8080`.
4. Kiểm tra trên laptop: mở `http://192.168.1.23:8080` bằng trình duyệt, thấy hình là được. Hoặc:
   ```
   python tools/tim_camera.py phone:192.168.1.23
   ```
5. Chạy camera chân cầu 2 bằng điện thoại:
   ```
   python ai_engine/camera_bridge.py --camera-id 2 --source phone:192.168.1.23 --api http://127.0.0.1:8000
   ```

## 3. iPhone hoặc Android — ứng dụng DroidCam
1. Cài **DroidCam** trên điện thoại (App Store / CH Play), mở ứng dụng, ghi lại **WiFi IP** (ví dụ `192.168.1.23`) và cổng (mặc định `4747`).
2. Cùng Wi-Fi với laptop như trên.
3. Chạy:
   ```
   python ai_engine/camera_bridge.py --camera-id 2 --source droidcam:192.168.1.23 --api http://127.0.0.1:8000
   ```
   Nếu cài thêm **DroidCam Client** trên Windows thì điện thoại trở thành một webcam thường (`--source 1` hoặc `2`), có thể cắm cáp USB cho ổn định hơn Wi-Fi.

## Đặt camera thế nào cho đếm và nhận diện tốt
- Dùng **giá đỡ / chân máy**, giữ điện thoại cố định, **cắm sạc** (truyền video rất hao pin), tắt tự khóa màn hình.
- Đặt ở chân cầu, quay về phía khách đi tới, cao khoảng **1,6–2 m**, hơi chúc xuống; khách cách camera **1,5–4 m** để mặt đủ to (nhận diện Nam/Nữ cần thấy rõ mắt, mũi).
- Tránh quay ngược sáng (cửa sổ, mặt trời sau lưng khách).
- Sau khi đặt xong, nhấn **L** trên cửa sổ camera để kẻ lại vạch cho đúng lối đi (vạch lưu riêng cho từng chân cầu).
- Độ phân giải nên từ **1280x720**; webcam USB được tự xin 1280x720 (`--cam-res`, đổi được, vd `--cam-res 1920x1080`).

## Lỗi thường gặp
| Hiện tượng | Cách xử lý |
|---|---|
| `Không mở được camera/video: http://...` | Khác mạng Wi-Fi, ứng dụng chưa bấm Start server, sai IP; mạng trường có thể chặn máy nói chuyện với nhau → dùng điểm phát điện thoại |
| `Không mở được camera/video: 1` | Webcam USB chưa nhận / đang bị ứng dụng khác giữ; chạy `python tools/tim_camera.py` để xem số đúng |
| Hình điện thoại giật, trễ | Wi-Fi yếu: để điện thoại gần bộ phát, giảm độ phân giải trong ứng dụng xuống 1280x720, hoặc dùng DroidCam qua cáp USB |
| Điện thoại mất kết nối giữa chừng | Camera tự thử kết nối lại mỗi 3 giây và báo "mất tín hiệu" về máy chủ; kiểm tra pin, khóa màn hình, Wi-Fi |
| Hình bị xoay ngang / ngược | Chỉnh hướng quay trong ứng dụng điện thoại (IP Webcam: *Video orientation*) |
