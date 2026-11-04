"""
poc_dem_nguoi_chua_cau.py
---------------------------
PoC (Proof of Concept) dem nguoi theo VUNG (zone) tai Chua Cau - phien ban
dung dung stack da CHOT trong bao cao Module 4/5 (Chuc_nang_va_Cong_nghe):

    YOLO11n/s (hoac YOLOv8n) + thu vien Supervision (zone counting + ByteTrack)

Khac voi webcam_tracking_demo.py / camera_in.py / camera_out.py trong thu
muc chuacau-ai-demo/src/ (ban cu, tu viet tracking + dem bang tay), file
nay la ban PoC DON GIAN HON, dung dung 2 thu vien ma nhom da chot de "chay
thu dem nguoi tren Chua Cau" (nhiem vu tuan 4-7 cua Minh) - khong tach
vao/ra, chi dem SO NGUOI DANG O TRONG 1 VUNG (zone) duoc ve san tren khung
hinh (vi du: long cau).

=== QUAN TRONG - MOI TRUONG CHAY THU (sandbox soan bao cao) KHONG CO
    Internet/GPU nen KHONG CAI DUOC ultralytics/supervision -> file nay
    MOI CHI duoc kiem tra cu phap (py_compile), CHUA duoc chay thuc te.
    Can chay lai va kiem thu tren may co cai dat day du (hoac Colab)
    truoc khi dung lam demo chinh thuc. ===

Cai dat (chay tren may ban, co Internet):
    pip install ultralytics supervision opencv-python requests

Chay vi du (webcam mac dinh, nguong canh bao 20 nguoi):
    python3 poc_dem_nguoi_chua_cau.py --source 0

Chay tren video co san, dinh nghia vung (zone) bang 4 diem (x,y):
    python3 poc_dem_nguoi_chua_cau.py --source video_chua_cau.mp4 \
        --zone "100,50 540,50 540,400 100,400" --threshold 20

Nhan 'q' de thoat khi xem truc tiep (--show, mac dinh BAT).

Cau truc code tach rieng ham run_counting() (generator, KHONG goi
cv2.imshow) de sau nay co the import truc tiep vao app Streamlit
(Module 5, F5 - Dashboard) ma khong can sua lai logic dem - Streamlit
app chi can lap (for) qua generator nay va tu ve lai frame bang
st.image() thay vi cv2.imshow().
"""

import argparse
import time
from dataclasses import dataclass, field
from typing import Generator, List, Optional, Tuple

import cv2
import numpy as np

# SUA LOI #5 (nang cap Phase 1): ham send_telegram_alert() o day truoc day
# la 1 BAN COPY y het telegram_alert.py (code trung lap). Dung LAI ham
# dung chung thay vi dinh nghia lai, de sau nay chi can sua 1 cho.
from telegram_alert import send_telegram_alert

try:
    from ultralytics import YOLO
    import supervision as sv
    _DEPS_OK = True
except ImportError as e:
    _DEPS_OK = False
    _IMPORT_ERR = e


DEFAULT_MODEL = "yolo11n.pt"       # fallback: "yolov8n.pt" neu chua co YOLO11
DEFAULT_THRESHOLD = 20             # suc chua toi da da chot trong bao cao Module 4/5
DEFAULT_CONF = 0.3
ALERT_COOLDOWN_SEC = 60.0
PERSON_CLASS_ID = 0                # "person" trong bo lop COCO


def parse_zone_arg(zone_str: Optional[str], frame_w: int, frame_h: int) -> np.ndarray:
    """Chuyen chuoi "x1,y1 x2,y2 x3,y3 x4,y4" thanh mang toa do da giac
    (polygon) dung cho sv.PolygonZone. Neu khong truyen --zone, mac dinh
    dung TOAN BO khung hinh (4 goc anh) lam vung dem."""
    if not zone_str:
        return np.array([[0, 0], [frame_w, 0], [frame_w, frame_h], [0, frame_h]])
    points = []
    for pair in zone_str.strip().split():
        x_str, y_str = pair.split(",")
        points.append([int(x_str), int(y_str)])
    if len(points) < 3:
        raise ValueError("Vung (--zone) can it nhat 3 diem (x,y) cach nhau boi dau cach.")
    return np.array(points)


@dataclass
class CountingResult:
    frame: np.ndarray
    count_in_zone: int
    status: str            # "OK" | "WARNING" | "ALERT" | "CRITICAL"
    track_ids: List[int] = field(default_factory=list)


def status_of(count: int, threshold: int) -> str:
    if count >= threshold:
        return "CRITICAL"
    if count >= int(threshold * 0.9):
        return "ALERT"
    if count >= int(threshold * 0.7):
        return "WARNING"
    return "OK"


STATUS_COLOR_BGR = {
    "OK": (60, 180, 75),
    "WARNING": (0, 165, 255),
    "ALERT": (0, 0, 255),
    "CRITICAL": (0, 0, 200),
}


class _TrackerAdapter:
    """NANG CAP (ban 2): tu phien ban supervision>=0.31 (phat hanh sau khi
    file nay duoc viet), thu vien `supervision` da GO HAN ByteTrack ra
    khoi thu vien, chuyen sang 1 goi RIENG ten `trackers`
    (xem https://trackers.roboflow.com) - vi vay sv.ByteTrack() khong con
    ton tai nua ("AttributeError: module supervision has no attribute
    ByteTrack"), VA ten method cap nhat cung doi: ban cu goi
    `update_with_detections(detections)`, ban moi (`trackers`) goi
    `update(detections)`.

    Adapter nay BOC lai ca 2 kieu tracker thanh CHUNG 1 cach goi
    `.update_with_detections(detections)` de phan code ben duoi
    (run_counting) KHONG can biet/quan tam dang chay ban supervision nao -
    tu dong hoat dong dung tren CA 2 kieu may (may cai supervision cu CO
    ByteTrack, va may cai supervision moi (>=0.31) PHAI cai them goi
    `trackers`)."""

    def __init__(self, impl, is_legacy: bool):
        self._impl = impl
        self._is_legacy = is_legacy

    def update_with_detections(self, detections):
        if self._is_legacy:
            return self._impl.update_with_detections(detections)
        return self._impl.update(detections)


def _create_tracker() -> _TrackerAdapter:
    """Tao tracker ByteTrack, tu dong chon dung "ban" (cu trong sv, hoac
    moi tu goi `trackers`) theo thu vien dang co san tren may - xem
    _TrackerAdapter o tren. Neu khong tim thay o dau ca, bao loi RO RANG
    kem phien ban dang cai + lenh can chay, thay vi 1 dong AttributeError
    kho hieu nhu truoc."""
    if hasattr(sv, "ByteTrack"):
        return _TrackerAdapter(sv.ByteTrack(), is_legacy=True)

    try:
        try:
            from trackers import ByteTrackTracker as _ByteTrackCls  # type: ignore
        except ImportError:
            from trackers import ByteTrack as _ByteTrackCls  # type: ignore
        return _TrackerAdapter(_ByteTrackCls(), is_legacy=False)
    except ImportError:
        pass

    installed_ver = getattr(sv, "__version__", "khong ro")
    raise RuntimeError(
        f"Thu vien 'supervision' (dang cai ban {installed_ver}) KHONG co ByteTrack.\n"
        f"Neu ban {installed_ver} la >= 0.31: ban supervision moi da GO ByteTrack ra\n"
        "khoi thu vien, chuyen qua 1 goi RIENG ten 'trackers'. Cach sua - cai them goi\n"
        "do (KHONG can sua code gi them, script nay tu nhan dung):\n"
        "    pip install trackers\n"
        "roi chay lai lenh cu.\n\n"
        f"Neu ban {installed_ver} la CU (duoi 0.19): ByteTrack chua ton tai trong ban\n"
        "do, can nang cap:\n"
        '    pip install -U "supervision>=0.21"\n\n'
        "Kiem tra lai sau khi sua bang:\n"
        "    python3 -c \"import supervision as sv; print(sv.__version__); "
        "print(hasattr(sv, 'ByteTrack'))\"\n"
        "    python3 -c \"import trackers; print([x for x in dir(trackers) if 'Track' in x])\"\n"
        "Neu da lam dung ma van loi, co the do CHAY NHAM python/pip ben ngoai venv -\n"
        "kiem tra bang 'which python3' va 'which pip' xem co dang tro vao thu muc\n"
        "venv/ cua du an khong."
    )


def run_counting(
    source,
    model_path: str = DEFAULT_MODEL,
    threshold: int = DEFAULT_THRESHOLD,
    conf: float = DEFAULT_CONF,
    zone_str: Optional[str] = None,
) -> Generator[CountingResult, None, None]:
    """Generator: moi lan goi next() se doc 1 khung hinh moi, chay YOLO +
    ByteTrack (qua Supervision), dem so nguoi dang o TRONG vung (zone), va
    yield lai 1 CountingResult (frame da ve annotation + so nguoi + trang
    thai). KHONG tu mo cua so hien thi (cv2.imshow) - de main() hoac 1 app
    Streamlit rieng quyet dinh cach hien thi."""
    if not _DEPS_OK:
        raise RuntimeError(
            "Thieu thu vien ultralytics/supervision. Chay:\n"
            "    pip install ultralytics supervision\n"
            f"(Loi import goc: {_IMPORT_ERR})"
        )

    model = YOLO(model_path)
    tracker = _create_tracker()
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Khong mo duoc nguon video: {source}")

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or 640
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 480
    zone_polygon = parse_zone_arg(zone_str, frame_w, frame_h)
    zone = sv.PolygonZone(polygon=zone_polygon)
    zone_annotator = sv.PolygonZoneAnnotator(zone=zone, color=sv.Color.WHITE, thickness=2)

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            result = model(frame, verbose=False, conf=conf)[0]
            detections = sv.Detections.from_ultralytics(result)
            detections = detections[detections.class_id == PERSON_CLASS_ID]
            detections = tracker.update_with_detections(detections)

            in_zone_mask = zone.trigger(detections=detections)
            count_in_zone = int(in_zone_mask.sum())
            status = status_of(count_in_zone, threshold)
            color = STATUS_COLOR_BGR[status]

            track_ids = (
                detections.tracker_id[in_zone_mask].tolist()
                if detections.tracker_id is not None
                else []
            )

            labels = [f"ID {tid}" for tid in (detections.tracker_id or [])]
            out = box_annotator.annotate(scene=frame.copy(), detections=detections)
            out = label_annotator.annotate(scene=out, detections=detections, labels=labels)
            out = zone_annotator.annotate(scene=out)

            bar_h = 46
            overlay = out.copy()
            cv2.rectangle(overlay, (0, 0), (out.shape[1], bar_h), (25, 25, 25), -1)
            out = cv2.addWeighted(overlay, 0.75, out, 0.25, 0)
            text = f"So nguoi trong vung: {count_in_zone}/{threshold}  |  Trang thai: {status}"
            cv2.putText(out, text, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2, cv2.LINE_AA)

            yield CountingResult(frame=out, count_in_zone=count_in_zone, status=status, track_ids=track_ids)
    finally:
        cap.release()


def main():
    parser = argparse.ArgumentParser(description="PoC dem nguoi theo vung tai Chua Cau (YOLO + Supervision).")
    parser.add_argument("--source", default="0", help="So webcam (vd 0) hoac duong dan/RTSP video.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Duong dan/weight YOLO (mac dinh yolo11n.pt).")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD, help="Suc chua toi da (mac dinh 20).")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF, help="Nguong do tin cay YOLO (mac dinh 0.3).")
    parser.add_argument("--zone", default=None, help='Vung dem, vd "100,50 540,50 540,400 100,400" (mac dinh: toan khung hinh).')
    parser.add_argument("--no-show", action="store_true", help="Khong mo cua so hien thi (chay nen).")
    parser.add_argument("--save", default=None, help="Duong dan file video de luu ket qua (tuy chon).")
    args = parser.parse_args()

    source = int(args.source) if args.source.isdigit() else args.source

    writer = None
    last_alert_time = 0.0

    for result in run_counting(source, model_path=args.model, threshold=args.threshold,
                                conf=args.conf, zone_str=args.zone):
        frame = result.frame

        if args.save and writer is None:
            h, w = frame.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(args.save, fourcc, 20.0, (w, h))
        if writer is not None:
            writer.write(frame)

        if result.status == "CRITICAL":
            now = time.time()
            if now - last_alert_time >= ALERT_COOLDOWN_SEC:
                send_telegram_alert(
                    f"[SmartCau AI - PoC] CANH BAO QUA TAI: {result.count_in_zone} nguoi "
                    f"trong vung giam sat (toi da {args.threshold}). Can kiem tra ngay!"
                )
                last_alert_time = now

        if not args.no_show:
            cv2.imshow("SmartCau AI - PoC dem nguoi (nhan 'q' de thoat)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    if writer is not None:
        writer.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    if not _DEPS_OK:
        print("Chua cai du thu vien. Chay: pip install ultralytics supervision opencv-python requests")
        print(f"(Loi import goc: {_IMPORT_ERR})")
    else:
        main()
