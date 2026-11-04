"""
demo_run.py
------------
Script tong hop chay TOAN BO demo cho bao cao/thuyet trinh:
  1. Tao 1 anh test va chay module dem nguoi + canh bao (crowd_counter.py)
  2. Sinh du lieu mo phong 14 ngay (data_simulator.py)
  3. Xuat dashboard.html (generate_dashboard.py)

Chay: python demo_run.py
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
import cv2
import numpy as np

from crowd_counter import CrowdCounter, CameraThresholds
from data_simulator import simulate_visitors, compute_occupancy
from generate_dashboard import build_html

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..")
SAMPLE_DIR = os.path.join(ROOT, "sample_data")


def make_placeholder_test_image(path):
    """Tao mot anh nen don gian de kiem tra pipeline chay khong loi.
    LUU Y: day KHONG PHAI anh nguoi that -> detector se tra ve 0 nguoi,
    dung de kiem tra code, khong dung de danh gia do chinh xac AI."""
    img = np.full((480, 720, 3), (235, 235, 235), dtype=np.uint8)
    cv2.putText(img, "ANH TEST (khong co nguoi that)", (30, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 120, 120), 2, cv2.LINE_AA)
    cv2.putText(img, "Gui anh/video dong nguoi that de test AI detector", (30, 275),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2, cv2.LINE_AA)
    cv2.imwrite(path, img)


def step1_crowd_counter():
    print("== BUOC 1: Module dem nguoi + canh bao ==")
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    test_path = os.path.join(SAMPLE_DIR, "test_frame.jpg")
    make_placeholder_test_image(test_path)

    counter = CrowdCounter()
    img = cv2.imread(test_path)
    count, status, boxes, weights = counter.count_and_status(img)
    annotated = counter.annotate(img, boxes, count, status)
    out_path = os.path.join(SAMPLE_DIR, "test_frame_annotated.jpg")
    cv2.imwrite(out_path, annotated)

    print(f"  Phat hien: {count} nguoi -> trang thai {status}")
    print(f"  Da luu anh ket qua: {out_path}")
    print("  (Anh test khong chua nguoi that nen ket qua = 0 la dung ky vong;")
    print("   gui anh/video dong nguoi that de kiem tra do chinh xac AI.)\n")


def step2_simulate_data():
    print("== BUOC 2: Sinh du lieu mo phong 14 ngay ==")
    visitors = simulate_visitors(start_date="2026-09-08", num_days=14, base_daily_visitors=1500)
    occupancy = compute_occupancy(visitors)
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    visitors.to_csv(os.path.join(SAMPLE_DIR, "visitors.csv"), index=False)
    occupancy.to_csv(os.path.join(SAMPLE_DIR, "occupancy.csv"), index=False)

    n_alert = occupancy["status"].isin(["ALERT", "CRITICAL"]).sum()
    print(f"  {len(visitors)} luot khach, {len(occupancy)} moc occupancy 5-phut")
    print(f"  {n_alert} moc VUOT NGUONG ({n_alert/len(occupancy)*100:.1f}%)\n")
    return visitors, occupancy


def step3_dashboard(visitors, occupancy):
    print("== BUOC 3: Xuat dashboard.html ==")
    html = build_html(visitors, occupancy, CameraThresholds())
    out_path = os.path.join(ROOT, "dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Da tao: {out_path}\n")


if __name__ == "__main__":
    step1_crowd_counter()
    visitors, occupancy = step2_simulate_data()
    step3_dashboard(visitors, occupancy)
    print("HOAN TAT. Mo file dashboard.html bang trinh duyet de xem ket qua.")
