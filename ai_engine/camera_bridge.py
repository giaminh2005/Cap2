"""
camera_bridge.py  —  Camera tai 1 CHAN CAU (dung chung cho camera 1 va camera 2)
================================================================================
Phu trach: MINH.   Chuc nang: F1.1, F1.2, F1.3, F2.1-F2.3 (FR-01..FR-06)

Moi chan cau dat 1 camera, quay tu cau RA chan cau, vuong goc voi cau. Tren
hinh ke 1 vach ngang qua loi di. Khi khach qua vach:
    tu phia ngoai vao phia cau -> "in"  -> server: num_k += 1, dem += 1
    tu phia cau ra phia ngoai  -> "out" -> server: num_k -= 1
Server tinh onbridge = num1 + num2 (xem backend/routers/bridge.py).

CHAY (tu THU MUC GOC Cap2/, backend phai chay truoc):
    python ai_engine/camera_bridge.py --camera-id 1 --source 0
    python ai_engine/camera_bridge.py --camera-id 2 --source 1
    python ai_engine/camera_bridge.py --camera-id 2 --source video_chan_cau_2.mp4
    python ai_engine/camera_bridge.py --camera-id 1 --source rtsp://user:pass@ip/stream

KE VACH (FR-01): lan dau chay se dung vach ngang giua hinh, phia cau = nua
duoi. Nhan phim 'l' de ve lai bang chuot:
    click 1, click 2 : 2 dau cua vach
    click 3          : 1 diem bat ky o PHIA CAU
Vach duoc luu vao ai_engine/config/line_cam<id>.json, lan sau tu doc lai.

Tuy chon:
    --no-alerts      tat gui canh bao (mac dinh CHI camera 1 gui canh bao
                     Vang/Do + Telegram de khong bi gui trung 2 lan)
    --demographics   uoc luong gioi tinh + khoang tuoi cho khach VAO cau
                     (can DeepFace, cham hon) - xem visitor_profiler.py.
                     Tu dung model pose yolov8n-pose.pt de lay vi tri mat.
    --region         (kem --demographics) uoc luong NHOM KHU VUC rong, chi
                     luu so dem tong hop theo gio. KHONG phai quoc tich.
    --no-blur        tat lam mo khuon mat tren man hinh (mac dinh BAT, NFR-05)
    --model          model YOLO (mac dinh yolov8n.pt, hoac yolov8n-pose.pt
                     khi bat --demographics)

Phim: 'q' thoat · 'l' ke lai vach · 'r' xoa vach da luu, ve vach mac dinh.
"""

import argparse
import os
import sys
import time

import cv2

try:
    import requests
except ImportError:
    print("Chua cai requests. Chay: pip install requests")
    sys.exit(1)

try:
    from ultralytics import YOLO
except ImportError:
    print("Chua cai ultralytics. Chay: pip install ultralytics")
    sys.exit(1)

from camera_backend import open_camera
from camera_ui import draw_capacity_banner, draw_info_panel, draw_person_box, draw_status_bar
from crowd_counter import AlertLevelTracker, CameraThresholds, STATUS_COLOR_BGR, STATUS_LABEL_VI
from line_crossing import LineCrossingCounter, foot_point
from telegram_alert import send_telegram_alert, trigger_buzzer_signal
from visitor_profiler import VisitorProfiler, blur_faces, extract_keypoints, face_rect

API_BASE = os.environ.get("SMARTCAU_API", "http://127.0.0.1:8000")
API_KEY = os.environ.get("SMARTCAU_API_KEY", "")
_HEADERS = {"X-API-Key": API_KEY} if API_KEY else {}
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")

STATE_POLL_SEC = 1.0      # doc onbridge (gom ca camera kia) moi 1 giay
CONFIG_POLL_SEC = 15.0    # doc nguong canh bao Admin dat
REPORT_SEC = 2.0          # gui so nguoi + muc canh bao cho dashboard (NFR-01)
ALERT_REPEAT_SEC = 180.0  # BRULE-04


# ------------------------------------------------------------------ API
def _post(path, payload):
    try:
        r = requests.post(f"{API_BASE}{path}", json=payload, headers=_HEADERS, timeout=2)
        if r.status_code == 200:
            return r.json()
        print(f"[API] {path} tra ve {r.status_code}: {r.text[:120]}")
    except requests.RequestException as e:
        print(f"[API] Khong gui duoc {path}: {e}")
    return None


def _get(path):
    try:
        r = requests.get(f"{API_BASE}{path}", timeout=2)
        if r.status_code == 200:
            return r.json()
    except requests.RequestException:
        pass
    return None


# ------------------------------------------------------------- ke vach
def _line_path(camera_id):
    return os.path.join(CONFIG_DIR, f"line_cam{camera_id}.json")


def load_line(camera_id) -> LineCrossingCounter:
    path = _line_path(camera_id)
    if os.path.exists(path):
        try:
            line = LineCrossingCounter.load(path)
            print(f"[CAMERA {camera_id}] Da doc vach ke tu {path}")
            return line
        except Exception as e:
            print(f"[CAMERA {camera_id}] File vach ke loi ({e}) -> dung vach mac dinh.")
    print(f"[CAMERA {camera_id}] Dung vach mac dinh (ngang giua hinh, phia cau = nua duoi). "
          "Nhan 'l' de ke lai.")
    return LineCrossingCounter()


def draw_line_setup(cap, window, camera_id) -> LineCrossingCounter:
    """Cho nguoi dung click 3 diem tren hinh dang chay. Tra ve vach moi (da luu)."""
    clicks = []

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(clicks) < 3:
            clicks.append((x, y))

    cv2.setMouseCallback(window, on_mouse)
    hints = ["Click DAU 1 cua vach", "Click DAU 2 cua vach", "Click 1 diem o PHIA CAU"]
    frame = None
    while len(clicks) < 3:
        ok, f = cap.read()
        if ok:
            frame = f
        if frame is None:
            continue
        out = frame.copy()
        for p in clicks:
            cv2.circle(out, p, 6, (0, 255, 255), -1)
        if len(clicks) >= 2:
            cv2.line(out, clicks[0], clicks[1], (0, 255, 255), 2)
        draw_status_bar(out, f"KE VACH CAMERA {camera_id}: {hints[len(clicks)]}  (Esc = huy)")
        cv2.imshow(window, out)
        if cv2.waitKey(30) & 0xFF == 27:
            cv2.setMouseCallback(window, lambda *a: None)
            return None

    cv2.setMouseCallback(window, lambda *a: None)
    h, w = frame.shape[:2]
    p1, p2, b = [(x / w, y / h) for x, y in clicks]
    try:
        line = LineCrossingCounter(p1=p1, p2=p2, bridge_point=b)
    except ValueError as e:
        print(f"[CAMERA {camera_id}] Vach khong hop le: {e}")
        return None
    line.save(_line_path(camera_id))
    print(f"[CAMERA {camera_id}] Da luu vach ke vao {_line_path(camera_id)}")
    return line


def draw_line_overlay(frame, line: LineCrossingCounter):
    h, w = frame.shape[:2]
    p1 = (int(line.p1[0] * w), int(line.p1[1] * h))
    p2 = (int(line.p2[0] * w), int(line.p2[1] * h))
    cv2.line(frame, p1, p2, (0, 255, 255), 2)
    # mui ten chi huong VAO cau (vuong goc voi vach, ve phia cau)
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    length = max(1.0, (dx * dx + dy * dy) ** 0.5)
    nx, ny = -dy / length, dx / length
    probe = ((mx + nx * 10) / w, (my + ny * 10) / h)
    if line.signed_distance(probe) < 0:
        nx, ny = -nx, -ny
    tip = (int(mx + nx * 50), int(my + ny * 50))
    cv2.arrowedLine(frame, (int(mx), int(my)), tip, (0, 255, 255), 2, tipLength=0.3)
    cv2.putText(frame, "VAO CAU", (tip[0] + 6, tip[1]), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, (0, 255, 255), 2, cv2.LINE_AA)


# ------------------------------------------------------------------ main
def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Camera chan cau - SmartCau AI")
    ap.add_argument("--camera-id", type=int, choices=(1, 2), required=True)
    ap.add_argument("--source", default="0", help="So webcam (0, 1...) hoac duong dan video/RTSP")
    ap.add_argument("--no-alerts", action="store_true", help="Khong gui canh bao tu camera nay")
    ap.add_argument("--demographics", action="store_true", help="Uoc luong gioi tinh/tuoi khach VAO")
    ap.add_argument("--region", action="store_true", help="Kem --demographics: thong ke nhom khu vuc tong hop")
    ap.add_argument("--no-blur", action="store_true", help="Khong lam mo khuon mat tren man hinh")
    ap.add_argument("--model", default=None)
    args = ap.parse_args(argv)
    if args.region and not args.demographics:
        ap.error("--region can di kem --demographics")
    if args.model is None:
        args.model = "yolov8n-pose.pt" if args.demographics else "yolov8n.pt"
    args.source = int(args.source) if args.source.isdigit() else args.source
    args.send_alerts = (args.camera_id == 1) and not args.no_alerts
    return args


def main():
    args = parse_args()
    cam = args.camera_id
    window = f"SmartCau AI - CAMERA CHAN CAU {cam} ('q' thoat, 'l' ke vach)"

    thresholds = CameraThresholds()
    remote = (_get("/config") or {}).get("alert_threshold")
    if remote:
        thresholds = CameraThresholds.from_alert_threshold(remote)
    tracker = AlertLevelTracker(thresholds, repeat_sec=ALERT_REPEAT_SEC)

    profiler = None
    if args.demographics:
        profiler = VisitorProfiler(post=_post, enable_region=args.region)
        print(f"[CAMERA {cam}] Uoc luong gioi tinh/tuoi: BAT"
              f"{' + nhom khu vuc (tong hop)' if args.region else ''}.")

    model = YOLO(args.model)
    line = load_line(cam)

    cap = open_camera(args.source)
    if not cap.isOpened():
        print(f"Khong mo duoc camera/video: {args.source}")
        sys.exit(1)
    cv2.namedWindow(window)

    state = _get("/bridge/state") or {"num1": 0, "num2": 0, "onbridge": 0, "dem": 0}
    api_ok = bool(_get("/health"))
    last_state_poll = last_cfg_poll = last_report = 0.0
    local_in = local_out = 0

    print(f"CAMERA CHAN CAU {cam} dang chay. Canh bao: {'BAT' if args.send_alerts else 'TAT'}.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Khong doc duoc frame (het video hoac mat tin hieu camera).")
            break
        now = time.time()
        fh, fw = frame.shape[:2]

        results = model.track(frame, persist=True, classes=[0], conf=0.4, verbose=False)[0]
        out = frame.copy()
        draw_line_overlay(out, line)

        people = []   # (tid, box, keypoints, kp_conf)
        if results.boxes is not None and results.boxes.id is not None:
            for i, (box, tid) in enumerate(zip(results.boxes, results.boxes.id)):
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                b = (int(x1), int(y1), int(x2 - x1), int(y2 - y1))
                kp_xy, kp_conf = extract_keypoints(results, i)
                people.append((int(tid), b, kp_xy, kp_conf))

        # NFR-05: lam mo mat tren anh HIEN THI truoc khi ve chu/khung len
        if not args.no_blur:
            blur_faces(out, [face_rect(b, kp, kc) for _, b, kp, kc in people])

        for tid, b, kp_xy, kp_conf in people:
            fx, fy = foot_point(b, fw, fh)
            on_bridge_side = line.signed_distance((fx, fy)) > 0
            side_color = (0, 200, 0) if on_bridge_side else (200, 120, 0)
            draw_person_box(out, b, tid, side_color)
            cv2.circle(out, (int(fx * fw), int(fy * fh)), 4, side_color, -1)

            event = line.update(tid, (fx, fy), now)
            if event:
                if event == "in":
                    local_in += 1
                    if profiler is not None:
                        profiler.mark_entered(tid, now)
                else:
                    local_out += 1
                    if profiler is not None:
                        profiler.mark_exited(tid)
                res = _post("/bridge/crossing", {"camera_id": cam, "direction": event, "track_id": tid})
                api_ok = res is not None
                if res:
                    state = res
                print(f"[CAMERA {cam}] ID {tid} {'VAO' if event == 'in' else 'RA'} cau"
                      f" -> tren cau: {state.get('onbridge')}")

            if profiler is not None:
                # Phan tich khach dang di TOI cau (phia ngoai, mat huong ve camera)
                # va khach vua vao chua chot ho so; bo qua nguoi da o tren cau tu truoc.
                if profiler.wants(tid) and (not on_bridge_side or event == "in"
                                            or profiler.label(tid) is not None):
                    profiler.observe(tid, frame, b, now, kp_xy, kp_conf)
                lines = profiler.label(tid)
                if lines:
                    draw_info_panel(out, b, lines)

        if profiler is not None:
            profiler.step(now)

        if now - last_state_poll >= STATE_POLL_SEC:
            s = _get("/bridge/state")
            api_ok = s is not None
            if s:
                state = s
            last_state_poll = now

        if now - last_cfg_poll >= CONFIG_POLL_SEC:
            remote = (_get("/config") or {}).get("alert_threshold")
            if remote and remote != thresholds.alert:
                thresholds = CameraThresholds.from_alert_threshold(remote)
                tracker.set_thresholds(thresholds)
                print(f"[CAMERA {cam}] Nguong moi: Vang tu {thresholds.warning}, toi da {thresholds.alert}.")
            last_cfg_poll = now

        onbridge = int(state.get("onbridge", 0))
        level = tracker.update(onbridge, now)

        if args.send_alerts:
            if now - last_report >= REPORT_SEC:
                _post("/occupancy", {"count": onbridge, "status": level})
                last_report = now
            kind = tracker.pop_notification(now)
            if kind:
                stamp = time.strftime("%H:%M:%S %d/%m/%Y")
                if kind == "CRITICAL":
                    msg = (f"[SmartCau AI] CANH BAO DO - QUA TAI: {onbridge} nguoi dang tren cau "
                           f"(toi da {thresholds.alert}), vuot nguong lien tuc "
                           f"{int(thresholds.red_hold_sec)} giay. Thoi diem: {stamp}.")
                    trigger_buzzer_signal(msg)
                    _post("/system_events", {"event_type": "CRITICAL_ALERT", "count": onbridge, "message": msg})
                else:
                    msg = (f"[SmartCau AI] CANH BAO VANG - CAU SAP DAY: {onbridge} nguoi dang tren cau "
                           f"(toi da {thresholds.alert}). Thoi diem: {stamp}.")
                    _post("/system_events", {"event_type": "WARNING", "count": onbridge, "message": msg})
                send_telegram_alert(msg)

        api_note = "" if api_ok else " | MAT KET NOI SERVER"
        draw_status_bar(out, f"CAM {cam} | num{cam}={state.get(f'num{cam}', 0)} | Tren cau: "
                             f"{onbridge}/{thresholds.alert} | Hom nay: {state.get('dem', 0)} luot | "
                             f"{STATUS_LABEL_VI[level]}{api_note}")
        cv2.putText(out, f"Camera nay: vao {local_in} / ra {local_out}", (10, fh - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, STATUS_COLOR_BGR[level], 2, cv2.LINE_AA)
        if level == "CRITICAL":
            draw_capacity_banner(out, f"QUA TAI! {onbridge} nguoi tren cau (toi da {thresholds.alert})")

        cv2.imshow(window, out)
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord("l"):
            new_line = draw_line_setup(cap, window, cam)
            if new_line is not None:
                line = new_line
        if key == ord("r"):
            try:
                os.remove(_line_path(cam))
            except FileNotFoundError:
                pass
            line = LineCrossingCounter()
            print(f"[CAMERA {cam}] Da ve lai vach mac dinh.")

    cap.release()
    cv2.destroyAllWindows()
    print(f"Ket thuc camera {cam}: ghi nhan {local_in} luot vao, {local_out} luot ra.")
    if profiler is not None:
        print(f"Ho so nhan khau hoc: {profiler.saved_count} da xac dinh, "
              f"{profiler.unknown_count} 'Khong xac dinh' (do tin cay < 70%).")


if __name__ == "__main__":
    main()
