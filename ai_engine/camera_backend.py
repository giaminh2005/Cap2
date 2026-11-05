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
import threading
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


_IP_RE = r"^\d{1,3}(\.\d{1,3}){3}(:\d+)?$"
PHONE_APPS = {   # ung dung bien dien thoai thanh camera qua Wi-Fi -> (cong mac dinh, duong dan luong video)
    "phone": (8080, "/video"),        # "IP Webcam" (Android)
    "ipwebcam": (8080, "/video"),
    "droidcam": (4747, "/video"),     # DroidCam (Android / iPhone)
}


def resolve_source(source):
    """Chuan hoa --source:
        "0", "1"                       -> webcam so 0, 1 (webcam laptop thuong la 0, webcam USB la 1)
        "phone:192.168.1.5"            -> http://192.168.1.5:8080/video   (ung dung IP Webcam)
        "droidcam:192.168.1.5"         -> http://192.168.1.5:4747/video   (ung dung DroidCam)
        "192.168.1.5:8080"             -> http://192.168.1.5:8080/video
        "http://...", "rtsp://...", duong dan video  -> giu nguyen
    """
    import re
    s = str(source).strip()
    if s.isdigit():
        return int(s)
    low = s.lower()
    for app, (port, path) in PHONE_APPS.items():
        if low.startswith(app + ":"):
            host = s.split(":", 1)[1].strip().strip("/")
            if ":" not in host:
                host = f"{host}:{port}"
            return f"http://{host}{path}"
    if re.match(_IP_RE, s):
        return f"http://{s if ':' in s else s + ':8080'}/video"
    return s


def is_network_source(source) -> bool:
    return isinstance(source, str) and source.lower().startswith(("http://", "https://", "rtsp://", "rtmp://"))


def open_camera(source, warmup_sec: float = 2.0, resolution=(1280, 720)) -> "cv2.VideoCapture":
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
        if cap.isOpened() and resolution:
            # webcam USB thuong mac dinh 640x480 -> xin 1280x720 (mat to hon, nhan dien Nam/Nu tot hon);
            # camera khong ho tro thi tu giu do phan giai cua no
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
    elif is_network_source(source):
        cap = cv2.VideoCapture(source, cv2.CAP_FFMPEG)     # luong video dien thoai / camera IP
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(source)
    else:
        cap = cv2.VideoCapture(source)

    if warmup_sec > 0:
        time.sleep(warmup_sec)
    return cap


class LatestFrameReader:
    """Doc webcam / RTSP o LUONG RIENG va chi giu khung hinh MOI NHAT.

    Khi xu ly AI cham hon toc do camera, VideoCapture thuong de don khung hinh
    trong bo dem -> hinh tren man hinh tre vai giay so voi thuc te ("lag").
    Lop nay bo cac khung cu, vong lap luon xu ly khung hinh vua chup.
    Dung giong VideoCapture: read(), isOpened(), release(), get(), set().
    """

    def __init__(self, cap):
        self.cap = cap
        try:
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        except cv2.error:
            pass
        self._frame, self._ok, self._seq, self._used = None, True, 0, 0
        self._cond = threading.Condition()
        self._stop = False
        self._t = threading.Thread(target=self._run, daemon=True, name="camera-reader")
        self._t.start()

    def _run(self):
        while not self._stop:
            ok, frame = self.cap.read()
            with self._cond:
                self._ok = ok
                if ok:
                    self._frame, self._seq = frame, self._seq + 1
                self._cond.notify_all()
            if not ok:
                time.sleep(0.05)
                if not self.cap.isOpened():
                    break

    def read(self, timeout: float = 2.0):
        with self._cond:
            if self._seq == self._used:
                self._cond.wait(timeout)
            if self._seq == self._used or not self._ok:
                return False, None
            self._used = self._seq
            return True, self._frame

    def isOpened(self):
        return self.cap.isOpened()

    def get(self, prop):
        return self.cap.get(prop)

    def set(self, prop, value):
        return self.cap.set(prop, value)

    def release(self):
        self._stop = True
        self.cap.release()


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
