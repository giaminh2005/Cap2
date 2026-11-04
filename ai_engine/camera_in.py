"""
camera_in.py
--------------
CAMERA VAO (dat o dau cau) - phien ban NANG CAP (Phase 1 + 2 + 3 + 4):
  - Nhan dien nguoi bang YOLO-POSE + tracking (moi nguoi 1 ID rieng trong
    PHIEN LAM VIEC CUA CHINH CAMERA NAY - khong lien quan ID ben
    camera_out.py). Dung model POSE (khong phai model detect thuong) de
    co THEM toa do khop xuong (keypoints) lam tin hieu phu cho Demographics
    Engine (xem demographics_engine.py).
  - Voi moi nguoi MOI xuat hien: phan tich khoang tuoi + gioi tinh qua
    DemographicsEngine (gop DeepFace + ty le vai/hong + bo phieu theo
    thoi gian - Phase 2), CHI luu HO SO khi ket qua da "san sang" (do tin
    cay >= 70%) - luu MOT LAN duy nhat (POST /entry).
  - Man hinh hien SO NGUOI DANG CO MAT tren cau lay TU SERVER (dung chung
    voi camera_out.py) - de 2 man hinh luon khop nhau.
  - KIEM SOAT CONG TU DONG (Phase 4): khi dang co mat >= nguong "alert"
    (mac dinh 20), hien banner "CHO - CAU DANG DAY" + dem nguoc "Con X
    cho trong"; khi >= nguong "critical" (mac dinh 25), hien canh bao do
    lon + gui Telegram + kich hoat tin hieu buzzer (co cooldown chong
    spam) + ghi lai su kien vao server (xem SystemEvent trong backend/).

BAT BUOC chay backend TRUOC o 1 terminal khac (moi lenh chay tu THU MUC GOC Cap2/):
    Terminal 1:  uvicorn backend.main:app --reload --port 8000
    Terminal 2:  python3 ai_engine/camera_in.py 0
    (hoac cach moi, ro nghia hon: python3 ai_engine/camera_in.py --camera-index 0)

Neu chi co 1 webcam de test ca 2 script (camera_in.py va camera_out.py)
cung luc: dung SO KHAC NHAU cho 2 lenh, vi du "python3 camera_in.py 0" va
"python3 camera_out.py --camera-index 1"; hoac chi test 1 script tai 1
thoi diem va tu go /exit, /entry qua trang http://127.0.0.1:8000/docs de
mo phong camera con lai.

=== CHE DO DEMO 1 CAMERA (SMARTCAU_SOLO_DEMO) ===
Mac dinh (KHONG set bien nay), so "dang co mat" LAY TU SERVER (cong don
VAO tru RA giua CA 2 camera - dung kien truc that cho trien khai 2 camera
that tai Chua Cau). Neu chi chay DUY NHAT camera_in.py (khong co camera
RA nao dang chay de bao "co nguoi vua roi di"), con so nay se CHI TANG
chu khong bao gio giam, du nguoi trong khung hinh da doi lien tuc - day
KHONG PHAI loi, ma la vi thieu mat camera RA de tru lai.
De demo nhanh VOI DUY NHAT 1 webcam va muon so "dang co mat" phan anh
DUNG so nguoi dang trong khung hinh NGAY LUC NAY (tu dong giam khi co
nguoi roi khoi khung hinh, khong can camera thu 2), set bien moi truong
nay TRUOC khi chay:
    export SMARTCAU_SOLO_DEMO=1
Khi bat, ho so nhan khau hoc (gioi tinh/tuoi) VAN duoc luu vao backend
binh thuong (qua /visit_events) de xem lai sau, nhung KHONG con cong don
vao bo dem "dang co mat" chung cua server nua - con so hien tren man
hinh se la SO NGUOI DANG CO TRONG KHUNG HINH HIEN TAI (tinh truc tiep tu
ket qua nhan dien moi frame), dung cho DEMO/THUYET TRINH; trien khai that
2 camera tai Chua Cau thi KHONG bat bien nay (de dung co che VAO/RA that).

Cai dat (chay tren may ban, co Internet):
    pip install -r ../requirements.txt

Tinh nang TUY CHON "phan nhom khu vuc" (Phase 3, mac dinh TAT - doc ky
region_mapping.py TRUOC khi bat): set bien moi truong SMARTCAU_ENABLE_
REGION=1 TRUOC khi chay script nay.

Neu server (backend/) co bat xac thuc (set SMARTCAU_API_KEY phia
server), set CUNG gia tri bien moi truong do o may chay script nay de
cac request khong bi tu choi (401).

Nhan 'q' de thoat.
"""

import os
import sys
import time

import cv2
import requests

from crowd_counter import CameraThresholds, STATUS_COLOR_BGR, STATUS_LABEL_VI
from camera_backend import open_camera, parse_camera_source
from demographics_engine import DemographicsEngine
from telegram_alert import send_telegram_alert, trigger_buzzer_signal
from camera_ui import (
    draw_person_box, draw_info_panel, draw_status_bar, draw_capacity_banner,
    draw_gate_banner, draw_countdown,
)

try:
    from ultralytics import YOLO
except ImportError:
    print("Chua cai ultralytics. Chay: pip install ultralytics")
    sys.exit(1)


API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")
API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
_API_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}

ENABLE_REGION = os.environ.get("SMARTCAU_ENABLE_REGION", "").strip() in ("1", "true", "True", "yes")
SOLO_DEMO = os.environ.get("SMARTCAU_SOLO_DEMO", "").strip() in ("1", "true", "True", "yes")

OCCUPANCY_POLL_INTERVAL_SEC = 1.0   # hoi server "hien co bao nhieu nguoi" moi 1 giay
CONFIG_POLL_INTERVAL_SEC = 15.0     # NANG CAP (Admin Web): hoi server "nguong canh bao hien tai" moi 15 giay
ALERT_COOLDOWN_SEC = 60.0


def get_shared_occupancy(default=0):
    try:
        resp = requests.get(f"{API_BASE}/stats/occupancy", timeout=2)
        if resp.status_code == 200:
            return resp.json().get("current_count", default)
    except Exception:
        pass
    return None  # None = khong ket noi duoc server


def get_remote_alert_threshold():
    """NANG CAP (Admin Web): doc nguong canh bao hien tai tu server (endpoint
    CONG KHAI GET /config - xem backend/) - de khi admin doi so tren
    trang Admin Web, camera VAO cap nhat lai nguong ma KHONG can restart
    script hay sua code. Tra ve None neu khong ket noi duoc server (giu
    nguyen nguong dang dung, khong lam gi ca)."""
    try:
        resp = requests.get(f"{API_BASE}/config", timeout=2)
        if resp.status_code == 200:
            return resp.json().get("alert_threshold")
    except Exception:
        pass
    return None


def post_entry(payload: dict):
    try:
        requests.post(f"{API_BASE}/entry", json=payload, headers=_API_HEADERS, timeout=2)
    except Exception as e:
        print(f"[API] Khong gui duoc du lieu VAO toi server (co the chua chay backend/): {e}")


def post_visit_event(payload: dict):
    """CHE DO DEMO 1 CAMERA (SMARTCAU_SOLO_DEMO): giong post_entry() nhung
    goi /visit_events thay vi /entry - VAN luu ho so nhan khau hoc vao
    backend (de xem lai qua Admin Web/Google Sheets), nhung KHONG cong
    them vao occupancy_state chung cua server (vi che do nay tu tinh so
    "dang co mat" truc tiep tu khung hinh hien tai, xem main())."""
    try:
        requests.post(f"{API_BASE}/visit_events", json=payload, headers=_API_HEADERS, timeout=2)
    except Exception as e:
        print(f"[API] Khong gui duoc du lieu VAO toi server (co the chua chay backend/): {e}")


def post_system_event(event_type: str, count: int = None, message: str = None):
    try:
        requests.post(
            f"{API_BASE}/system_events",
            json={"event_type": event_type, "count": count, "message": message},
            headers=_API_HEADERS, timeout=2,
        )
    except Exception as e:
        print(f"[API] Khong ghi duoc su kien he thong: {e}")


def post_region_stat(region: str):
    try:
        requests.post(f"{API_BASE}/region_stats", json={"region": region}, headers=_API_HEADERS, timeout=2)
    except Exception as e:
        print(f"[API] Khong ghi duoc thong ke khu vuc: {e}")


def _extract_keypoints(results, idx):
    """Lay (keypoints_xy, keypoints_conf) cho nguoi thu `idx` tu ket qua
    YOLO-pose, hoac (None, None) neu model khong co keypoints (vd lo dung
    nham model detect thuong thay vi model pose)."""
    kp = getattr(results, "keypoints", None)
    if kp is None or kp.xy is None:
        return None, None
    try:
        xy = kp.xy[idx].tolist()
        conf = kp.conf[idx].tolist() if kp.conf is not None else [1.0] * len(xy)
        return xy, conf
    except (IndexError, TypeError):
        return None, None


def main():
    source = parse_camera_source(default=0, description="Camera VAO - SmartCau AI")

    thresholds = CameraThresholds()
    # NANG CAP (Admin Web): thu doc nguong canh bao TU SERVER ngay luc khoi
    # dong - neu Admin da doi tren trang web TRUOC khi camera chay, camera
    # se ap dung dung nguong moi nay ngay tu dau (khong con phai doi den
    # lan poll dinh ky dau tien). Neu server chua chay/khong ket noi duoc,
    # tu dong dung nguong mac dinh (18/20/25) nhu cu, khong bao loi.
    _remote_alert = get_remote_alert_threshold()
    if _remote_alert is not None:
        thresholds = CameraThresholds.from_alert_threshold(_remote_alert)
        print(f"[CAMERA VAO] Da doc nguong canh bao tu server: alert={thresholds.alert} "
              f"(warning={thresholds.warning}, critical={thresholds.critical}).")
    else:
        print("[CAMERA VAO] Khong doc duoc nguong tu server luc khoi dong, "
              f"dung nguong mac dinh (warning={thresholds.warning}, alert={thresholds.alert}, "
              f"critical={thresholds.critical}).")

    model = YOLO("yolov8n-pose.pt")  # model POSE: co ca box + khop xuong (keypoints) cho tin hieu phu

    engine = DemographicsEngine(enable_region=ENABLE_REGION)
    saved_ids = set()         # track_id da LUU ho so roi (tranh luu lap)
    # SUA LOI (man hinh chi hien "(da ghi nhan)" trong trong, KHONG con
    # thay gioi tinh/tuoi sau khi da ghi nhan): ban truoc CHI dung set()
    # de nho "tid nao da luu", khong nho LAI ket qua (gioi tinh/tuoi) da
    # doan duoc. Vi vay frame DAU TIEN info["ready"]=True co hien gioi
    # tinh/tuoi that, nhung do la video truc tiep nen frame do troi qua
    # trong 1/30 giay, nguoi dung khong kip thay - tu frame SAU do tro di,
    # code chi biet "tid nay da luu roi" (saved_ids) ma KHONG con nho ket
    # qua la gi, nen chi hien duoc "(da ghi nhan)" chung chung. Sua: them
    # dict nho lai gioi tinh/tuoi cho tung track_id NGAY luc "chot" ket
    # qua, de cac frame sau van hien TIEP TUC dung thong tin do.
    saved_info = {}            # track_id -> {"gender":.., "age_range":..}
    region_logged_ids = set() # track_id da ghi thong ke khu vuc tong hop roi (tranh dem lap)
    shared_count = 0          # so nguoi dang co mat, lay tu server
    last_poll_time = 0.0
    last_config_poll_time = 0.0
    last_alert_time = 0.0
    last_gate_event_time = 0.0
    api_reachable = True
    gate_was_closed = False

    cap = open_camera(source)
    if not cap.isOpened():
        print(f"Khong mo duoc camera/video: {source}")
        sys.exit(1)

    print("CAMERA VAO dang chay (Pose + Demographics Engine)... nhan 'q' de thoat.")
    if ENABLE_REGION:
        print("[CAMERA VAO] Tinh nang 'phan nhom khu vuc' (Phase 3) DANG BAT.")
    if SOLO_DEMO:
        print(
            "[CAMERA VAO] CHE DO DEMO 1 CAMERA (SMARTCAU_SOLO_DEMO) DANG BAT: so 'dang co mat' "
            "se tinh TRUC TIEP tu khung hinh hien tai (tu dong giam khi nguoi roi khung hinh), "
            "KHONG dung so luy ke tu server. Ho so van duoc luu vao backend binh thuong."
        )

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
        for i, (box, tid) in enumerate(zip(boxes, ids)):
            color = STATUS_COLOR_BGR.get(thresholds.status_of(shared_count), (0, 200, 0))
            draw_person_box(out, box, tid, color)

            if tid not in saved_ids:
                kp_xy, kp_conf = _extract_keypoints(results, i)
                info = engine.update(tid, frame, box, keypoints=kp_xy, kp_conf=kp_conf)

                if info["ready"]:
                    saved_ids.add(tid)
                    saved_info[tid] = {"gender": info["gender"], "age_range": info["age_range"]}
                    entry_payload = {
                        "track_id": tid,
                        "age": info["age"],
                        "age_range": info["age_range"],
                        "gender": info["gender"],
                    }
                    if SOLO_DEMO:
                        # Luu ho so vao backend nhung KHONG cong vao occupancy_state
                        # chung (xem post_visit_event() + giai thich o dau file).
                        post_visit_event(entry_payload)
                    else:
                        post_entry(entry_payload)
                    if ENABLE_REGION and info.get("region") and info.get("region_confidence", 0) >= 0.5:
                        if tid not in region_logged_ids:
                            region_logged_ids.add(tid)
                            post_region_stat(info["region"])
                    label = [f"VAO - ID {tid}", info["gender"], info["age_range"]]
                    draw_info_panel(out, box, label)
                else:
                    cv2.putText(out, f"ID {tid} (dang xac dinh... {info['n_votes']}/3)",
                                (box[0], max(0, box[1] - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 1, cv2.LINE_AA)
            else:
                info = saved_info.get(tid)
                if info:
                    draw_info_panel(out, box, [f"ID {tid}", info["gender"], info["age_range"]])
                else:
                    # Phong hy huu: tid nam trong saved_ids nhung khong co trong
                    # saved_info (vd du lieu cu tu phien chay truoc) - van hien
                    # duoc, chi khong co gioi tinh/tuoi kem theo.
                    draw_info_panel(out, box, [f"ID {tid}", "(da ghi nhan)"])

        now = time.time()
        if SOLO_DEMO:
            # CHE DO DEMO 1 CAMERA: so "dang co mat" = so nguoi dang duoc
            # YOLO theo doi NGAY TRONG khung hinh hien tai (tu dong giam
            # khi co nguoi roi khoi khung hinh, vi luc do YOLO khong con
            # tra ve box cho ID do nua) - khong can hoi server, khong can
            # camera RA de tru lai (xem giai thich day du o dau file).
            shared_count = len(boxes)
            api_reachable = True
        elif now - last_poll_time >= OCCUPANCY_POLL_INTERVAL_SEC:
            result = get_shared_occupancy()
            api_reachable = result is not None
            if result is not None:
                shared_count = result
            last_poll_time = now

        # NANG CAP (Admin Web): dinh ky kiem tra lai nguong canh bao (phong
        # truong hop admin doi cau hinh SAU khi camera da chay roi) - khong
        # can poll moi frame vi nguong hiem khi doi lien tuc, 15 giay/lan
        # la du nhanh ma khong lam qua tai server.
        if now - last_config_poll_time >= CONFIG_POLL_INTERVAL_SEC:
            _remote_alert = get_remote_alert_threshold()
            if _remote_alert is not None and _remote_alert != thresholds.alert:
                thresholds = CameraThresholds.from_alert_threshold(_remote_alert)
                print(f"[CAMERA VAO] Admin da doi nguong canh bao -> ap dung nguong moi: "
                      f"warning={thresholds.warning}, alert={thresholds.alert}, critical={thresholds.critical}.")
            last_config_poll_time = now

        status = thresholds.status_of(shared_count)
        if SOLO_DEMO:
            api_note = " | DEMO 1 CAMERA (dem khung hinh hien tai)"
        else:
            api_note = "" if api_reachable else " | MAT KET NOI SERVER"
        draw_status_bar(
            out,
            f"CAMERA VAO | Dang co mat: {shared_count}/{thresholds.critical} | "
            f"{STATUS_LABEL_VI[status]}{api_note}",
        )

        # --- Phase 4: kiem soat cong tu dong ---
        gate_closed = shared_count >= thresholds.alert
        if shared_count >= thresholds.warning:
            draw_countdown(out, thresholds.critical - shared_count)
        if gate_closed:
            draw_gate_banner(out, f"CHO - CAU DANG DAY ({shared_count}/{thresholds.alert})")
            if not gate_was_closed and now - last_gate_event_time >= 5.0:
                post_system_event("GATE_CLOSED", count=shared_count, message="Dat nguong cho vao")
                last_gate_event_time = now
        elif gate_was_closed and now - last_gate_event_time >= 5.0:
            post_system_event("GATE_REOPENED", count=shared_count, message="Da co cho tro lai")
            last_gate_event_time = now
        gate_was_closed = gate_closed

        if shared_count >= thresholds.critical:
            draw_capacity_banner(out, f"QUA TAI! {shared_count} nguoi tren cau (toi da {thresholds.critical})")
            if now - last_alert_time >= ALERT_COOLDOWN_SEC:
                msg = (
                    f"[SmartCau AI] CANH BAO QUA TAI: {shared_count} nguoi dang tren cau "
                    f"(toi da {thresholds.critical}). Can kiem tra ngay!"
                )
                send_telegram_alert(msg)
                trigger_buzzer_signal(msg)
                post_system_event("CRITICAL_ALERT", count=shared_count, message=msg)
                last_alert_time = now

        cv2.imshow("SmartCau AI - CAMERA VAO (nhan 'q' de thoat)", out)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
    print(f"Da ket thuc. So luot VAO da ghi nhan trong phien nay: {len(saved_ids)}")


if __name__ == "__main__":
    main()
