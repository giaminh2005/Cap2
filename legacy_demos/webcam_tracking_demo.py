"""
webcam_tracking_demo.py
--------------------------
Ban "1 CAMERA DUY NHAT" (fallback don gian, dung khi chi co 1 webcam de
test, hoac chua can dung 2 camera vao/ra) - dung YOLOv8 + TRACKING de dem
nguoi TRUC TIEP tu 1 camera duy nhat (khong tach vao/ra).

Neu can dung mo hinh 2 CAMERA VAO/RA tu dong tru/cong so nguoi (giong
kien truc thuc te se trien khai tai Chua Cau), dung camera_in.py (dat dau
cau) va camera_out.py (dat cuoi cau) thay cho file nay - 2 file do dung
CHUNG 1 so nguoi qua backend/.

DA SUA LOI (so voi ban truoc): nguyen nhan nhan dien SAI gioi tinh/tuoi
truoc day la vi DeepFace, khi khong tim thay khuon mat that, van tra ve 1
ket qua "gia" doan tu ca vung anh dua vao (co the la toc/ao/nen) thay vi
tu mat that. Ban nay dung ham dung chung
estimate_demographics_from_person_box() (xem age_gender_estimator.py) da
LOC BO cac ket qua "gia" do, va tra ve KHOANG tuoi (vd "25-34") thay vi 1
con so tuoi le khong dang tin.

YEU CAU CAI DAT (chay tren may ban, co Internet):
    pip install ultralytics deepface tf-keras requests

Neu co chay backend/ o 1 terminal khac, du lieu se duoc luu lai; neu
khong, script nay VAN CHAY BINH THUONG (chi khong luu duoc du lieu).

Nhan 'q' de thoat.
"""

# --- [To chuc lai thu muc - Sprint 3] file nay da duoc chuyen khoi src/.
# Dong duoi giup import cac module trong ai_engine/ (crowd_counter,
# camera_ui, ...) va tools/ ma KHONG can sua lai tung dong import cu.
import os as _os, sys as _sys
_ROOT = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
for _sub in ("ai_engine", "tools"):
    _p = _os.path.abspath(_os.path.join(_ROOT, _sub))
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# --- het phan them moi ---

import os
import sys
import time

import cv2
import requests

from crowd_counter import CameraThresholds, STATUS_COLOR_BGR, STATUS_LABEL_VI
from camera_backend import open_camera, parse_camera_source
from age_gender_estimator import estimate_demographics_from_person_box
from telegram_alert import send_telegram_alert
from camera_ui import draw_person_box, draw_info_panel, draw_status_bar, draw_capacity_banner

try:
    from ultralytics import YOLO
except ImportError:
    print("Chua cai ultralytics. Chay: pip install ultralytics")
    sys.exit(1)


API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")
API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
_API_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
OCCUPANCY_POST_INTERVAL_SEC = 5.0
ALERT_COOLDOWN_SEC = 60.0


def post_json(path: str, payload: dict):
    try:
        requests.post(f"{API_BASE}{path}", json=payload, headers=_API_HEADERS, timeout=2)
    except Exception as e:
        print(f"[API] Khong gui duoc du lieu toi {path} (co the chua chay backend/): {e}")


def main():
    source = parse_camera_source(default=0, description="Webcam 1-camera - SmartCau AI")

    thresholds = CameraThresholds()
    model = YOLO("yolov8n.pt")

    demographics_db = {}     # track_id -> {"age":.., "age_range":.., "gender":..}
    last_occupancy_post = 0.0
    last_alert_time = 0.0

    cap = open_camera(source)  # SUA LOI #4: tu dong chon dung backend camera theo he dieu hanh (xem camera_backend.py)

    if not cap.isOpened():
        print(f"Khong mo duoc camera/video: {source}")
        sys.exit(1)

    print("Dang chay (co tracking + demographics cache)... nhan 'q' de thoat.")
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

        count = len(boxes)
        status = thresholds.status_of(count)
        color = STATUS_COLOR_BGR[status]

        out = frame.copy()
        for box, tid in zip(boxes, ids):
            draw_person_box(out, box, tid, color)

            if tid not in demographics_db:
                info = estimate_demographics_from_person_box(frame, box)
                if info["gender"] is not None:
                    demographics_db[tid] = info
                    post_json("/visit_events", {
                        "track_id": tid,
                        "age": info["age"],
                        "age_range": info["age_range"],
                        "gender": info["gender"],
                    })

            info = demographics_db.get(tid)
            if info and info.get("gender"):
                draw_info_panel(out, box, [f"ID {tid}", info["gender"], info["age_range"]])
            else:
                cv2.putText(out, f"ID {tid} (dang tim mat...)", (box[0], max(0, box[1] - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)

        draw_status_bar(
            out,
            f"So nguoi: {count}/{thresholds.critical} | {STATUS_LABEL_VI[status]} | "
            f"Da luu {len(demographics_db)} ho so",
        )

        now = time.time()
        if now - last_occupancy_post >= OCCUPANCY_POST_INTERVAL_SEC:
            post_json("/occupancy", {"count": count, "status": status})
            last_occupancy_post = now

        if count >= thresholds.critical:
            draw_capacity_banner(out, f"QUA TAI! {count} nguoi tren cau (toi da {thresholds.critical})")
            if now - last_alert_time >= ALERT_COOLDOWN_SEC:
                send_telegram_alert(f"[SmartCau AI] Canh bao: {count} nguoi tren cau ({status}). Can kiem tra ngay!")
                last_alert_time = now

        cv2.imshow("SmartCau AI - Tracking + Demographics (nhan 'q' de thoat)", out)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Da ket thuc. Tong so nguoi (ID) da ghi nhan trong phien nay: {len(demographics_db)}")


if __name__ == "__main__":
    main()
