"""
camera_backend.py  —  Mo nguon hinh cho camera chan cau
========================================================
    resolve_source(s)     "0"/"1" -> webcam; "phone:<IP>", "droidcam:<IP>", "<IP>:<cong>" -> luong video dien thoai;
                          http(s)://, rtsp://, duong dan tep -> giu nguyen
    open_camera(src)      chon dung backend OpenCV theo he dieu hanh (Windows CAP_DSHOW, Linux CAP_V4L2,
                          macOS CAP_AVFOUNDATION); webcam xin 1280x720; luong mang mo bang FFmpeg
    LatestFrameReader     doc camera o luong rieng, luon tra khung MOI NHAT (het tre hinh khi AI cham)
"""

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

