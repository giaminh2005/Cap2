"""
tools/tim_camera.py  —  Do tim camera dang co tren may (webcam laptop, webcam USB, dien thoai)
==============================================================================================
    python tools/tim_camera.py                       # thu webcam so 0..5, luu anh chup thu tung camera
    python tools/tim_camera.py phone:192.168.1.5     # thu camera dien thoai (ung dung IP Webcam)
    python tools/tim_camera.py droidcam:192.168.1.5  # thu DroidCam
    python tools/tim_camera.py rtsp://user:pass@192.168.1.20:554/stream1

In ra do phan giai, toc do khung hinh va LENH CHAY camera chan cau tuong ung.
Anh chup thu luu o thu muc tools/anh_camera/ de biet so nao la camera nao.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai_engine"))

import cv2  # noqa: E402

from camera_backend import is_network_source, open_camera, resolve_source  # noqa: E402

try:   # tat thong bao "Camera index out of range" cua OpenCV khi do so khong co camera
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
except AttributeError:
    pass

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anh_camera")


def probe(source, label):
    t0 = time.time()
    cap = open_camera(source, warmup_sec=0.8)
    if not cap.isOpened():
        cap.release()
        return None
    frames, first = 0, None
    t1 = time.time()
    while time.time() - t1 < 2.0:
        ok, f = cap.read()
        if not ok:
            break
        frames += 1
        if first is None:
            first = f
    cap.release()
    if first is None:
        return None
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{label}.jpg")
    cv2.imwrite(path, first)
    h, w = first.shape[:2]
    return {"w": w, "h": h, "fps": frames / 2.0, "open_s": t1 - t0, "snapshot": path}


def show(src_text, info):
    print(f"  ✓ {src_text}: {info['w']}x{info['h']}, khoảng {info['fps']:.0f} khung/giây "
          f"(mở mất {info['open_s']:.1f} giây) · ảnh thử: {info['snapshot']}")
    if info["w"] < 1280:
        print("    (độ phân giải thấp: mặt khách nhỏ, nhận diện Nam/Nữ kém hơn; nên dùng camera 720p trở lên)")


def main():
    if len(sys.argv) > 1:
        raw = sys.argv[1]
        src = resolve_source(raw)
        print(f"Thử {raw} -> {src}")
        info = probe(src, "mang" if is_network_source(src) else str(src).replace(os.sep, "_"))
        if info is None:
            print("  ✗ Không mở được. Kiểm tra: cùng mạng Wi-Fi, ứng dụng trên điện thoại đã bấm Start, "
                  "mở thử địa chỉ bằng trình duyệt; tường lửa / mạng trường có thể chặn.")
            return 1
        show(raw, info)
        print(f"\nLệnh chạy:  python ai_engine/camera_bridge.py --camera-id 2 --source {raw} --api http://<IP máy chủ>:8000")
        return 0

    print("Đang dò webcam số 0 đến 5 (camera đang bị ứng dụng khác dùng sẽ không mở được)...")
    found = []
    for i in range(6):
        info = probe(i, f"webcam_{i}")
        if info:
            show(f"Webcam số {i}", info)
            found.append(i)
    if not found:
        print("  ✗ Không thấy webcam nào. Tắt Zoom / Meet / ứng dụng Camera rồi thử lại.")
        return 1
    print(f"\nMở ảnh trong {OUT_DIR} để biết số nào là camera nào (laptop thường là 0, webcam USB là 1).")
    print("Ví dụ:")
    for cam, idx in zip((1, 2), found + found[:1]):
        print(f"  python ai_engine/camera_bridge.py --camera-id {cam} --source {idx} --api http://<IP máy chủ>:8000")
    print("Dùng điện thoại làm camera: python tools/tim_camera.py phone:<IP hiện trong ứng dụng IP Webcam>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
