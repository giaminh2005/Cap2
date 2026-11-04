"""
camera_backend.py
--------------------
Ham DUNG CHUNG de MO CAMERA cho tat ca script (camera_in.py, camera_out.py,
webcam_tracking_demo.py) - tach rieng ra file nay de sua 1 cho duy nhat.

SUA LOI #4 (nang cap Phase 1): ban truoc HARDCODE cv2.CAP_AVFOUNDATION khi
mo camera bang so (vd `cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)`), day la
backend CHI CO tren macOS. Tren Windows/Linux, dong nay van "chay" (khong
crash) nhung co the mo SAI camera, cham bat thuong, hoac khong mo duoc tuy
driver - vi flag do khong co y nghia gi voi OpenCV tren he dieu hanh khac.
Sua: tu dong chon dung backend theo he dieu hanh dang chay (Windows ->
CAP_DSHOW, Linux -> CAP_V4L2, macOS -> CAP_AVFOUNDATION), va neu van khong
mo duoc thi tu dong thu lai bang backend mac dinh truoc khi bao loi.

SUA LOI #3 (nang cap Phase 1): them cach doc nguon camera qua co
--camera-index (hoac --source) RO RANG HON, thay vi chi dua vao vi tri
tham so dong lenh (positional) nhu truoc - van GIU LAI cach cu de tuong
thich nguoc (khong lam hong cac lenh nguoi dung da quen):
    python3 camera_in.py 0                  (cach cu - van chay duoc)
    python3 camera_in.py --camera-index 0    (cach moi - ro nghia hon)
    python3 camera_out.py --camera-index 1
"""

import argparse
import platform
import time

import cv2


def _pick_backend_for_platform():
    """Tra ve flag backend OpenCV phu hop voi he dieu hanh dang chay.
    Linux/Windows/macOS deu co backend rieng; cac he dieu hanh khac (hiem
    gap) dung cv2.CAP_ANY de OpenCV tu quyet dinh."""
    system = platform.system()
    if system == "Darwin":
        return cv2.CAP_AVFOUNDATION
    if system == "Windows":
        return cv2.CAP_DSHOW
    if system == "Linux":
        return cv2.CAP_V4L2
    return cv2.CAP_ANY


def open_camera(source, warmup_sec: float = 2.0) -> "cv2.VideoCapture":
    """Mo camera (so webcam) hoac video/RTSP (duong dan), tu dong chon
    dung backend OpenCV theo he dieu hanh. Co warmup (cho vai giay) de 1
    so webcam (dac biet tren macOS) kip khoi dong truoc khi doc frame dau
    tien, tranh frame dau bi den/loi."""
    if isinstance(source, int):
        backend = _pick_backend_for_platform()
        cap = cv2.VideoCapture(source, backend)
        if not cap.isOpened():
            # Mot so may khong ho tro backend rieng cua he dieu hanh (vd
            # driver camera ao, may ao hoa...) - thu lai bang backend mac
            # dinh cua OpenCV truoc khi ket luan la "khong mo duoc camera".
            cap.release()
            cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(source)

    if warmup_sec > 0:
        time.sleep(warmup_sec)
    return cap


def parse_camera_source(argv=None, default=0, description: str = "Camera SmartCau AI"):
    """Doc nguon camera tu dong lenh, ho tro CA 2 cach (tuong thich nguoc):
      1) Kieu CU (positional): python3 camera_in.py 0
      2) Kieu MOI (co ten):     python3 camera_in.py --camera-index 0

    Tra ve int (so webcam) hoac str (duong dan file/RTSP)."""
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "source_positional", nargs="?", default=None,
        help="So webcam (vd 0) hoac duong dan video/RTSP - cach cu, van dung duoc.",
    )
    parser.add_argument(
        "--camera-index", "--source", dest="camera_index", default=None,
        help="So webcam (vd 0, 1...) hoac duong dan video/RTSP - cach moi, ro nghia hon khi chay nhieu camera.",
    )
    args = parser.parse_args(argv)

    raw = args.camera_index if args.camera_index is not None else args.source_positional
    if raw is None:
        return default
    if isinstance(raw, str) and raw.lstrip("-").isdigit():
        return int(raw)
    return raw
