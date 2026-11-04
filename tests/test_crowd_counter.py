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
from crowd_counter import AlertLevelTracker, CrowdCounter, CameraThresholds


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
    """TC-02: Nguong tuc thoi theo BRD (BRULE-02): Vang tu 15, toi da 20."""
    th = CameraThresholds()
    assert (th.warning, th.alert) == (15, 20)
    cases = {0: "OK", 10: "OK", 14: "OK", 15: "WARNING", 19: "WARNING",
             20: "WARNING", 21: "ALERT", 40: "ALERT"}
    for count, expected in cases.items():
        got = th.status_of(count)
        assert got == expected, f"count={count}: ky vong {expected}, duoc {got}"
    assert CameraThresholds.from_alert_threshold(20).warning == 15
    print("TC-02 PASS: logic nguong dung cho tat ca cac moc kiem tra")


def test_TC04_red_needs_15_seconds_and_clears_after_15_seconds():
    """TC-04 (FR-04, AC-02.2, BRULE-04): Do khi N=21 LIEN TUC 15 giay;
    ve Binh thuong khi N<=15 lien tuc 15 giay."""
    tr = AlertLevelTracker()
    assert tr.update(15, 0) == "WARNING"          # N = 15 -> Vang
    assert tr.update(21, 1) == "ALERT"            # vuot nhung chua du 15s
    assert tr.update(21, 15.9) == "ALERT"
    assert tr.update(21, 16) == "CRITICAL"        # du 15 giay -> Do
    assert tr.update(18, 20) == "CRITICAL"        # giam con 18 van giu Do
    assert tr.update(15, 21) == "CRITICAL"        # bat dau dem 15s de dong
    assert tr.update(15, 35.9) == "CRITICAL"
    assert tr.update(15, 36) == "WARNING"         # du 15s <= 15 -> het Do
    assert tr.update(10, 37) == "OK"
    # vuot nguong bi ngat quang thi dem lai tu dau
    tr2 = AlertLevelTracker()
    tr2.update(21, 0); tr2.update(20, 10); tr2.update(21, 11)
    assert tr2.update(21, 20) == "ALERT"
    assert tr2.update(21, 26) == "CRITICAL"


def test_TC05_notifications_no_repeat_within_3_minutes():
    """TC-05 (FR-06, AC-02.1, AC-02.2, BRULE-04): Vang gui 1 tin khi len
    Vang; Do gui ngay khi vao Do, nhac lai toi da 1 lan / 3 phut."""
    tr = AlertLevelTracker(repeat_sec=180)
    tr.update(15, 0)
    assert tr.pop_notification(0) == "WARNING"
    tr.update(14, 5); tr.update(15, 6)             # dao dong 14 <-> 15
    assert tr.pop_notification(6) is None          # khong gui lap trong 3 phut
    tr.update(21, 10); tr.update(21, 25)
    assert tr.pop_notification(25) == "CRITICAL"
    tr.update(22, 100)
    assert tr.pop_notification(100) is None
    tr.update(22, 205)
    assert tr.pop_notification(205) == "CRITICAL"  # nhac lai sau 3 phut
    tr.update(22, 300)
    assert tr.pop_notification(300) is None


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
    test_TC04_red_needs_15_seconds_and_clears_after_15_seconds()
    test_TC05_notifications_no_repeat_within_3_minutes()
    print("\nTat ca test co ban da PASS.")
