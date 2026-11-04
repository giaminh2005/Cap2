"""
camera_out.py
---------------
CAMERA RA (dat o cuoi cau) - phan con lai cua he thong 2-camera vao/ra.

Y TUONG: camera nay KHONG can nhan lai chinh xac "day la nguoi nao da vao"
(that ra la 1 bai toan Re-Identification kho, can may nhieu camera goc
nhin/mau sac khac nhau - ngoai pham vi do an mon hoc nay). Thay vao do,
camera nay chi can dem SO LUOT nguoi di NGANG QUA khu vuc RA cua no, va
moi lan phat hien 1 nguoi MOI (ID moi, theo tracking rieng cua CHINH NO)
thi bao cho server "co 1 nguoi VUA RA" (POST /exit) - server se TU DONG -1
vao so nguoi dang co mat tren cau (xem OccupancyState trong api_server.py).
Day chinh la co che "tu dong tru so luong khi khach ra khoi cau" ma de bai
yeu cau.

Camera nay KHONG luu ho so nhan khau hoc (da luu 1 lan luc VAO roi, o
camera_in.py) - chi lam nhiem vu dem RA.

BAT BUOC chay api_server.py TRUOC o 1 terminal khac:
    Terminal 1:  uvicorn api_server:app --reload --port 8000
    Terminal 2 (neu da chay camera_in.py):  python3 camera_out.py 1
    (hoac cach moi, ro nghia hon: python3 camera_out.py --camera-index 1)
    (dung SO WEBCAM KHAC voi camera_in.py neu chay dong thoi tren cung 1 may)

Neu server (api_server.py) co bat xac thuc (set SMARTCAU_API_KEY phia
server), set CUNG gia tri bien moi truong do o may chay script nay.

Nhan 'q' de thoat.
"""

import os
import sys
import time

import cv2
import requests

from crowd_counter import CameraThresholds, STATUS_COLOR_BGR, STATUS_LABEL_VI
from camera_backend import open_camera, parse_camera_source
from camera_ui import draw_person_box, draw_status_bar, draw_capacity_banner, draw_countdown

try:
    from ultralytics import YOLO
except ImportError:
    print("Chua cai ultralytics. Chay: pip install ultralytics")
    sys.exit(1)


API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")
API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
_API_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
OCCUPANCY_POLL_INTERVAL_SEC = 1.0
CONFIG_POLL_INTERVAL_SEC = 15.0   # NANG CAP (Admin Web): xem giai thich trong camera_in.py


def get_shared_occupancy():
    try:
        resp = requests.get(f"{API_BASE}/stats/occupancy", timeout=2)
        if resp.status_code == 200:
            return resp.json().get("current_count", 0)
    except Exception:
        pass
    return None


def get_remote_alert_threshold():
    """NANG CAP (Admin Web): xem giai thich chi tiet trong camera_in.py -
    camera RA cung doc nguong nay de hien dung "con X cho trong"/canh bao
    tren man hinh cua chinh no, dong bo voi camera VAO."""
    try:
        resp = requests.get(f"{API_BASE}/config", timeout=2)
        if resp.status_code == 200:
            return resp.json().get("alert_threshold")
    except Exception:
        pass
    return None


def post_exit():
    try:
        requests.post(f"{API_BASE}/exit", headers=_API_HEADERS, timeout=2)
    except Exception as e:
        print(f"[API] Khong gui duoc bao RA toi server (co the chua chay api_server.py): {e}")


def main():
    source = parse_camera_source(default=0, description="Camera RA - SmartCau AI")

    thresholds = CameraThresholds()
    _remote_alert = get_remote_alert_threshold()
    if _remote_alert is not None:
        thresholds = CameraThresholds.from_alert_threshold(_remote_alert)
        print(f"[CAMERA RA] Da doc nguong canh bao tu server: alert={thresholds.alert} "
              f"(warning={thresholds.warning}, critical={thresholds.critical}).")
    else:
        print("[CAMERA RA] Khong doc duoc nguong tu server luc khoi dong, dung nguong mac dinh "
              f"(warning={thresholds.warning}, alert={thresholds.alert}, critical={thresholds.critical}).")

    model = YOLO("yolov8n.pt")

    seen_ids = set()
    shared_count = 0
    last_poll_time = 0.0
    last_config_poll_time = 0.0
    api_reachable = True

    cap = open_camera(source)
    if not cap.isOpened():
        print(f"Khong mo duoc camera/video: {source}")
        sys.exit(1)

    print("CAMERA RA dang chay... nhan 'q' de thoat.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Khong doc duoc frame.")
            break

        results = model.track(frame, persist=True, classes=[0], conf=0.4, verbose=False)[0]

        boxes, ids = [], []
        if results.boxes is not None and results.boxes.id is not None:
            for box, tid in zip(results.boxes, results.boxes.id):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                boxes.append((int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
                ids.append(int(tid))

        out = frame.copy()
        for box, tid in zip(boxes, ids):
            color = STATUS_COLOR_BGR.get(thresholds.status_of(shared_count), (0, 200, 0))
            draw_person_box(out, box, tid, color)

            if tid not in seen_ids:
                seen_ids.add(tid)
                post_exit()   # bao ngay server -1, khong can doi phan tich gi them

        now = time.time()
        if now - last_poll_time >= OCCUPANCY_POLL_INTERVAL_SEC:
            result = get_shared_occupancy()
            api_reachable = result is not None
            if result is not None:
                shared_count = result
            last_poll_time = now

        if now - last_config_poll_time >= CONFIG_POLL_INTERVAL_SEC:
            _remote_alert = get_remote_alert_threshold()
            if _remote_alert is not None and _remote_alert != thresholds.alert:
                thresholds = CameraThresholds.from_alert_threshold(_remote_alert)
                print(f"[CAMERA RA] Admin da doi nguong canh bao -> ap dung nguong moi: "
                      f"warning={thresholds.warning}, alert={thresholds.alert}, critical={thresholds.critical}.")
            last_config_poll_time = now

        status = thresholds.status_of(shared_count)
        api_note = "" if api_reachable else " | MAT KET NOI SERVER"
        draw_status_bar(
            out,
            f"CAMERA RA | Dang co mat: {shared_count}/{thresholds.critical} | "
            f"{STATUS_LABEL_VI[status]} | Da ghi nhan {len(seen_ids)} luot ra{api_note}",
        )

        if shared_count >= thresholds.warning:
            draw_countdown(out, thresholds.critical - shared_count)

        if shared_count >= thresholds.critical:
            draw_capacity_banner(out, f"QUA TAI! {shared_count} nguoi tren cau (toi da {thresholds.critical})")

        cv2.imshow("SmartCau AI - CAMERA RA (nhan 'q' de thoat)", out)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Da ket thuc. So luot RA da ghi nhan trong phien nay: {len(seen_ids)}")


if __name__ == "__main__":
    main()
