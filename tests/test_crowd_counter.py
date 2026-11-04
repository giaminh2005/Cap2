"""
test_crowd_counter.py
----------------------
Bo test co ban cho module dem nguoi + canh bao nguong.
Tuong ung voi tai lieu "Test Plan / Test Case" (Module 9 hoc phan).

Chay: python -m pytest test_crowd_counter.py -v
Hoac: python test_crowd_counter.py
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

import numpy as np
from crowd_counter import CrowdCounter, CameraThresholds


def make_blank_frame(w=640, h=480, color=(200, 200, 200)):
    frame = np.full((h, w, 3), color, dtype=np.uint8)
    return frame


def test_TC01_blank_image_gives_zero_and_ok():
    """TC-01: Anh trong (khong co nguoi) -> count = 0, status = OK."""
    counter = CrowdCounter()
    frame = make_blank_frame()
    count, status, boxes, weights = counter.count_and_status(frame)
    assert count == 0
    assert status == "OK"
    print("TC-01 PASS: anh trong -> 0 nguoi, status OK")


def test_TC02_threshold_boundaries():
    """TC-02: Kiem tra logic nguong 18/20/25 dung nhu BRD da mo ta."""
    th = CameraThresholds(warning=18, alert=20, critical=25)
    cases = {0: "OK", 10: "OK", 17: "OK", 18: "WARNING", 19: "WARNING",
             20: "ALERT", 24: "ALERT", 25: "CRITICAL", 40: "CRITICAL"}
    for count, expected in cases.items():
        got = th.status_of(count)
        assert got == expected, f"count={count}: ky vong {expected}, duoc {got}"
    print("TC-02 PASS: logic nguong dung cho tat ca cac moc kiem tra")


def test_TC03_annotate_does_not_crash_and_keeps_shape():
    """TC-03: Ham annotate tra ve anh cung kich thuoc, khong loi."""
    counter = CrowdCounter()
    frame = make_blank_frame()
    count, status, boxes, weights = counter.count_and_status(frame)
    annotated = counter.annotate(frame, boxes, count, status)
    assert annotated.shape == frame.shape
    print("TC-03 PASS: annotate() chay on dinh, giu nguyen kich thuoc anh")


if __name__ == "__main__":
    test_TC01_blank_image_gives_zero_and_ok()
    test_TC02_threshold_boundaries()
    test_TC03_annotate_does_not_crash_and_keeps_shape()
    print("\nTat ca test co ban da PASS.")
