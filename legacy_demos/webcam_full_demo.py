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

import sys
import time
import cv2

from crowd_counter import CrowdCounter
from camera_ui import draw_info_panel as _shared_draw_info_panel

ANALYSIS_INTERVAL_SEC = 1.0
MAX_PEOPLE_LABEL = 8

try:
    from age_gender_estimator import estimate_demographics_from_person_box
    DEEPFACE_OK = True
except Exception:
    DEEPFACE_OK = False


# SUA LOI #5 (nang cap Phase 1): ham draw_info_panel() truoc day bi LAP
# LAI y het logic cua camera_ui.draw_info_panel() (code trung lap - sua 1
# cho quen sua cho kia la nguyen nhan de phat sinh loi). Gio dung LAI ham
# dung chung trong camera_ui.py, chi doi mau mac dinh cho khop giao dien
# cu cua file nay (tim hong/magenta thay vi tim/do nhu camera_in.py).
def draw_info_panel(frame, person_box, lines, color=(255, 0, 255)):
    return _shared_draw_info_panel(frame, person_box, lines, color=color)


# SUA LOI LAN 7 (phat hien qua doi chieu voi file camera_in.py "chuan"):
# ham nay TRUOC DAY goi estimate_age_gender(frame) tren CA KHUNG HINH roi
# moi tim cach "ghep" lai (match_face_to_person) khuon mat vao dung khung
# nguoi - ngoai viec rac roi/de ghep sai khi nhieu nguoi, DeepFace voi
# enforce_detection=False tren CA khung hinh con de bi anh huong boi nen/do
# vat KHONG phai nguoi hon la tren 1 vung ROI rieng cho tung nguoi. Sua:
# dung LAI ham dung chung estimate_demographics_from_person_box() - CUNG 1
# ham da dung trong camera_in.py/camera_out.py (co loc ket qua "gia", co
# chon dung mat thuoc ve dung nguoi khi 2 nguoi dung sat nhau - xem "SUA
# LOI LAN 6" trong age_gender_estimator.py) - goi RIENG cho TUNG khung
# nguoi, khong con can buoc "ghep" nua vi da ro rang 1-1 theo chi so box.
def run_full_analysis(counter, frame):
    count, status, boxes, weights = counter.count_and_status(frame)
    infos = []
    if boxes and DEEPFACE_OK:
        infos = [estimate_demographics_from_person_box(frame, box) for box in boxes]
    return count, status, boxes, infos


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
    count, status, boxes, infos = 0, "OK", [], []

    print("Dang chay... nhan 'q' de thoat.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Khong doc duoc frame.")
            break

        now = time.time()
        if now - last_analysis_time >= ANALYSIS_INTERVAL_SEC:
            count, status, boxes, infos = run_full_analysis(counter, frame)
            last_analysis_time = now

        out = counter.annotate(frame, boxes, count, status)

        shown = 0
        for i, box in enumerate(boxes):
            if shown >= MAX_PEOPLE_LABEL:
                break
            info = infos[i] if i < len(infos) else None
            # SUA LOI LAN 7: hien KHOANG tuoi (age_range), KHONG con hien
            # 1 con so tuoi LE (vd "~24 tuoi") - 1 con so le tu 1 frame
            # webcam la khong dang tin, giong ly do da dung KHOANG tuoi o
            # camera_in.py/camera_out.py tu truoc (xem age_gender_estimator.py).
            if not info or not info.get("gender"):
                continue
            lines = [f"Nguoi #{i + 1}", info["gender"], info["age_range"]]
            draw_info_panel(out, box, lines)
            shown += 1

        cv2.imshow("SmartCau AI - Dem nguoi + Nhan khau hoc (nhan 'q' de thoat)", out)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
