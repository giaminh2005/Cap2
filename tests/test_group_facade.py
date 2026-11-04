"""
tests/test_group_facade.py  —  Kiem thu dem mat tien (F1.4, BRULE-10) va phat hien doan (F3.1, BRULE-03)
CHAY: pytest tests/test_group_facade.py -q
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai_engine"))

from group_detector import GroupDetector  # noqa: E402
from line_crossing import FacadeCounter  # noqa: E402


def test_facade_counts_passer_once_even_if_stops():
    fc = FacadeCounter(min_visible_sec=1.0, gone_sec=2.0)
    for i in range(50):                    # dung chup anh 5 giay o phia ngoai
        fc.update(1, outside=True, now=i * 0.1)
    assert fc.collect(5.0) == 0            # van con trong hinh
    assert fc.collect(7.5) == 1
    assert fc.collect(9.0) == 0            # khong dem lai


def test_facade_ignores_people_who_cross_or_flash_by():
    fc = FacadeCounter(min_visible_sec=1.0, gone_sec=2.0)
    for i in range(20):
        fc.update(1, outside=True, now=i * 0.1)
        fc.update(2, outside=True, now=i * 0.1)
    fc.mark_crossed(2)                     # nguoi 2 vao cau
    fc.update(3, outside=True, now=0.0)    # nguoi 3 chi thoang qua 0 giay
    fc.update(4, outside=False, now=0.0)   # nguoi 4 o phia cau
    assert fc.collect(10) == 1


def _crowd(n, t, y, spacing=0.03):
    """n nguoi dung sat nhau, cung di xuong (ve phia cau): signed distance = y - 0.5."""
    return [(i, 0.1 + i * spacing, y, 0.2, y - 0.5) for i in range(n)]


def test_group_of_12_alerts_after_10_seconds_once():
    g = GroupDetector(min_size=10, hold_sec=10, cooldown_sec=180)
    alerts = []
    for k in range(0, 140):                # 14 giay, 10 frame/giay
        t = k * 0.1
        r = g.update(_crowd(12, t, 0.05 + t * 0.02), t)
        if r:
            alerts.append((t, r))
    assert len(alerts) == 1 and alerts[0][1] == 12 and 10.5 <= alerts[0][0] <= 11.5


def test_small_group_or_spread_out_or_standing_no_alert():
    for people_fn in (lambda t: _crowd(8, t, 0.05 + t * 0.02),               # it nguoi
                      lambda t: _crowd(12, t, 0.05 + t * 0.02, spacing=0.5),  # cach xa nhau
                      lambda t: _crowd(12, t, 0.2)):                          # dung yen
        g = GroupDetector(min_size=10, hold_sec=10)
        assert not any(g.update(people_fn(k * 0.1), k * 0.1) for k in range(150))
