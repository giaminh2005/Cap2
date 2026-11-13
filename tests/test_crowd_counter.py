"""
test_crowd_counter.py
----------------------
Kiem thu nguong canh bao Vang / Do (CameraThresholds, AlertLevelTracker).
Tuong ung voi tai lieu "Test Plan / Test Case" (Module 9 hoc phan).

Chay: pytest tests/test_crowd_counter.py -v
"""

import os as _os
import sys as _sys

_sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "ai_engine"))

from crowd_counter import AlertLevelTracker, CameraThresholds


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
