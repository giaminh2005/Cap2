"""
tests/test_line_crossing.py  —  Kiem thu thuat toan vach ke vao/ra (F1.2, F1.3)
CHAY: pytest tests/test_line_crossing.py -q
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai_engine"))

from line_crossing import LineCrossingCounter, foot_point  # noqa: E402


def walk(counter, tid, ys, x=0.5, t0=0.0):
    """Cho 1 nguoi di qua cac toa do y lien tiep, tra ve danh sach su kien."""
    events = []
    for i, y in enumerate(ys):
        ev = counter.update(tid, (x, y), t0 + i * 0.1)
        if ev:
            events.append(ev)
    return events


def test_default_line_down_is_in_up_is_out():
    """Vach ngang giua hinh, phia cau = nua duoi: di xuong = VAO, di len = RA."""
    c = LineCrossingCounter()
    assert walk(c, 1, [0.2, 0.4, 0.6, 0.8]) == ["in"]
    assert walk(c, 2, [0.9, 0.6, 0.4, 0.1]) == ["out"]


def test_first_sighting_is_not_a_crossing():
    """Nguoi dang dung san o phia cau khi camera bat len -> khong dem."""
    c = LineCrossingCounter()
    assert walk(c, 1, [0.8, 0.85, 0.9]) == []


def test_jitter_on_the_line_counts_once():
    """Dung lac qua lac lai sat vach (trong vung dem) chi tinh 1 lan."""
    c = LineCrossingCounter(min_dist=0.03)
    ys = [0.3, 0.49, 0.51, 0.49, 0.52, 0.48, 0.51, 0.7]
    assert walk(c, 1, ys) == ["in"]


def test_in_then_back_out():
    c = LineCrossingCounter()
    assert walk(c, 1, [0.2, 0.7, 0.2]) == ["in", "out"]


def test_drawn_line_and_bridge_side_any_orientation():
    """Vach doc, phia cau ben PHAI: di tu trai sang phai = VAO."""
    c = LineCrossingCounter(p1=(0.5, 0.0), p2=(0.5, 1.0), bridge_point=(0.9, 0.5))
    events = [c.update(1, (x, 0.5), i) for i, x in enumerate([0.1, 0.3, 0.7, 0.9])]
    assert [e for e in events if e] == ["in"]
    # dao chieu 2 dau vach khong lam doi y nghia (phia cau van ben phai)
    c2 = LineCrossingCounter(p1=(0.5, 1.0), p2=(0.5, 0.0), bridge_point=(0.9, 0.5))
    events = [c2.update(1, (x, 0.5), i) for i, x in enumerate([0.1, 0.3, 0.7, 0.9])]
    assert [e for e in events if e] == ["in"]


def test_forget_old_tracks():
    c = LineCrossingCounter(forget_sec=5)
    c.update(1, (0.5, 0.2), 0)
    c.update(2, (0.5, 0.2), 10)        # sau 10 giay ID 1 bi xoa
    assert c.update(1, (0.5, 0.8), 10.1) is None   # ID 1 coi nhu nguoi moi


def test_invalid_line():
    with pytest.raises(ValueError):
        LineCrossingCounter(p1=(0.5, 0.5), p2=(0.5, 0.5))
    with pytest.raises(ValueError):
        LineCrossingCounter(bridge_point=(0.3, 0.5))   # diem nam tren vach


def test_save_and_load(tmp_path):
    c = LineCrossingCounter(p1=(0.1, 0.6), p2=(0.9, 0.4), bridge_point=(0.5, 0.95))
    path = str(tmp_path / "line_cam1.json")
    c.save(path)
    c2 = LineCrossingCounter.load(path)
    assert c2.to_dict() == c.to_dict()


def test_foot_point():
    assert foot_point((100, 50, 40, 200), 400, 500) == (0.3, 0.5)
