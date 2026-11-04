"""
webcam_full_demo.py
---------------------
Demo day du tu webcam: dem nguoi (da loc bot vat khong phai nguoi, xem
crowd_counter.py) + hien 1 O THONG TIN nhan khau hoc (gioi tinh, tuoi uoc
luong) ngay BEN CANH moi nguoi duoc phat hien.

Yeu cau: da cai deepface (xem huong dan trong age_gender_estimator.py):
    pip install deepface tf-keras

Cach chay:
    python3 webcam_full_demo.py            -> webcam mac dinh (index 0)
    python3 webcam_full_demo.py 1          -> webcam so 1
    python3 webcam_full_demo.py video.mp4  -> tu 1 file video co san

Nhan 'q' trong cua so video de thoat.

Luu y hieu nang: uoc luong tuoi/gioi tinh (DeepFace) kha nang hon nhieu so
voi dem nguoi, nen ca pipeline (dem nguoi + tuoi/gioi tinh) chi chay lai
DAY DU moi ANALYSIS_INTERVAL_SEC giay 1 lan; giua 2 lan do, hinh dung lai
ket qua gan nhat de khong bi giat/dung hinh. May cang manh co the giam
ANALYSIS_INTERVAL_SEC de cap nhat nhanh hon.
"""

import sys
import time
import cv2

from crowd_counter import CrowdCounter
from camera_ui import draw_info_panel as _shared_draw_info_panel

ANALYSIS_INTERVAL_SEC = 1.0
MAX_PEOPLE_LABEL = 8

try:
    from age_gender_estimator import estimate_age_gender
    DEEPFACE_OK = True
except Exception:
    DEEPFACE_OK = False


def match_face_to_person(face_region, person_boxes):
    """Gan 1 khuon mat (tu DeepFace) cho khung nguoi (tu HOG) gan nhat,
    dua tren gia dinh khuon mat nam o 1/3 tren cua khung nguoi."""
    fx = face_region.get("x", 0)
    fy = face_region.get("y", 0)
    fw = face_region.get("w", 0)
    fh = face_region.get("h", 0)
    fcx, fcy = fx + fw / 2, fy + fh / 2

    best_idx, best_dist = None, None
    for i, (px, py, pw, ph) in enumerate(person_boxes):
        if px - 15 <= fcx <= px + pw + 15 and py - 15 <= fcy <= py + ph * 0.6:
            dist = abs(fcx - (px + pw / 2))
            if best_dist is None or dist < best_dist:
                best_dist = dist
                best_idx = i
    return best_idx


# SUA LOI #5 (nang cap Phase 1): ham draw_info_panel() truoc day bi LAP
# LAI y het logic cua camera_ui.draw_info_panel() (code trung lap - sua 1
# cho quen sua cho kia la nguyen nhan de phat sinh loi). Gio dung LAI ham
# dung chung trong camera_ui.py, chi doi mau mac dinh cho khop giao dien
# cu cua file nay (tim hong/magenta thay vi tim/do nhu camera_in.py).
def draw_info_panel(frame, person_box, lines, color=(255, 0, 255)):
    return _shared_draw_info_panel(frame, person_box, lines, color=color)


def run_full_analysis(counter, frame):
    count, status, boxes, weights = counter.count_and_status(frame)
    faces = []
    if boxes and DEEPFACE_OK:
        faces = estimate_age_gender(frame)
    return count, status, boxes, faces


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else 0
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    if not DEEPFACE_OK:
        print("[Canh bao] Chua cai duoc deepface -> se CHI dem nguoi, khong hien tuoi/gioi tinh.")
        print("Cai bang: pip install deepface tf-keras\n")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Khong mo duoc nguon video/camera: {source}")
        sys.exit(1)

    counter = CrowdCounter()
    last_analysis_time = 0.0
    count, status, boxes, faces = 0, "OK", [], []

    print("Dang chay... nhan 'q' de thoat.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Khong doc duoc frame.")
            break

        now = time.time()
        if now - last_analysis_time >= ANALYSIS_INTERVAL_SEC:
            count, status, boxes, faces = run_full_analysis(counter, frame)
            last_analysis_time = now

        out = counter.annotate(frame, boxes, count, status)

        shown = 0
        for face in faces:
            if shown >= MAX_PEOPLE_LABEL:
                break
            idx = match_face_to_person(face.get("region", {}), boxes)
            if idx is None:
                continue
            lines = [f"Nguoi #{idx + 1}", f"{face['gender']}", f"~{face['age']} tuoi"]
            draw_info_panel(out, boxes[idx], lines)
            shown += 1

        cv2.imshow("SmartCau AI - Dem nguoi + Nhan khau hoc (nhan 'q' de thoat)", out)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
