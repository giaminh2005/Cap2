"""
tests/test_visitor_profiler.py  —  Kiem thu lap ho so nhan khau hoc (F3.2, FR-09, BRULE-06, NFR-05)
Dung engine GIA (khong can DeepFace) de kiem tra logic.
CHAY: pytest tests/test_visitor_profiler.py -q
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai_engine"))

from visitor_profiler import VisitorProfiler, blur_faces, face_rect  # noqa: E402


class FakeEngine:
    """Tra ve 'san sang' sau `ready_after` lan goi update (gia lap bo phieu 3/3)."""

    def __init__(self, ready_after=3, gender="Woman", age_range="25-34", region=None):
        self.calls, self.ready_after = {}, ready_after
        self.gender, self.age_range, self.region = gender, age_range, region
        self.forgotten = []

    def update(self, tid, frame, box, keypoints=None, kp_conf=None):
        n = self.calls[tid] = self.calls.get(tid, 0) + 1
        ready = self.ready_after is not None and n >= self.ready_after
        return {"gender": self.gender if ready else None, "ready": ready, "age": 28,
                "age_range": self.age_range, "n_votes": n,
                "region": self.region, "region_confidence": 0.8}

    def forget(self, tid):
        self.forgotten.append(tid)


def make(engine, **kw):
    posts = []
    p = VisitorProfiler(post=lambda path, payload: posts.append((path, payload)),
                        engine=engine, analyze_interval=0.0, **kw)
    return p, posts


FRAME = np.zeros((10, 10, 3), np.uint8)
BOX = (0, 0, 5, 5)


def test_profile_saved_only_after_entering():
    """Du phieu khi con o ngoai nhung CHUA vao cau -> chua luu; vao cau -> luu ngay 1 lan."""
    p, posts = make(FakeEngine(ready_after=3))
    for t in range(5):
        p.observe(1, FRAME, BOX, t)
    assert posts == []
    p.mark_entered(1, 5)
    assert posts == [("/visit_events", {"track_id": 1, "age": 28, "age_range": "25-34", "gender": "Woman"})]
    p.observe(1, FRAME, BOX, 6)
    p.mark_entered(1, 7)
    assert len(posts) == 1                      # khong luu lap
    assert p.label(1) == ["VAO - ID 1", "Nu", "25-34"]


def test_unknown_when_confidence_never_reached():
    """BRULE-06: vao cau ma 5 giay van chua du tin cay -> 'Khong xac dinh'."""
    p, posts = make(FakeEngine(ready_after=None), give_up_sec=5)
    p.observe(2, FRAME, BOX, 0)
    p.mark_entered(2, 1)
    for t in (2, 3, 4, 5):
        p.observe(2, FRAME, BOX, t)
        p.step(t)
    assert posts == []
    p.step(6)
    assert posts == [("/visit_events", {"track_id": 2, "age": None, "age_range": "Khong xac dinh", "gender": None})]
    assert p.label(2) == ["VAO - ID 2", "Khong xac dinh"]


def test_unknown_when_person_leaves_view_before_ready():
    p, posts = make(FakeEngine(ready_after=None), give_up_sec=99, gone_sec=1.5)
    p.observe(3, FRAME, BOX, 0)
    p.mark_entered(3, 0.5)
    p.step(1.0)
    assert posts == []
    p.step(2.1)                                 # khong thay nua > 1.5 giay
    assert posts[0][1]["gender"] is None


def test_exit_stops_analysis_and_reentry_resumes():
    p, posts = make(FakeEngine(ready_after=2))
    p.observe(4, FRAME, BOX, 0)
    p.mark_exited(4)
    assert not p.wants(4)
    p.mark_entered(4, 1)                        # quay lai vao cau
    assert p.wants(4)
    p.observe(4, FRAME, BOX, 2)
    assert posts and posts[0][1]["gender"] == "Woman"


def test_region_only_as_aggregate_when_enabled():
    p, posts = make(FakeEngine(ready_after=1, region="Phuong Tay"), enable_region=True)
    p.observe(5, FRAME, BOX, 0)
    p.mark_entered(5, 1)
    assert ("/region_stats", {"region": "Phuong Tay"}) in posts
    assert "region" not in posts[0][1]          # ho so ca nhan KHONG co khu vuc
    p2, posts2 = make(FakeEngine(ready_after=1, region="Phuong Tay"), enable_region=False)
    p2.observe(5, FRAME, BOX, 0)
    p2.mark_entered(5, 1)
    assert all(path != "/region_stats" for path, _ in posts2)


def test_analyze_interval_limits_deepface_calls():
    eng = FakeEngine(ready_after=None)
    p = VisitorProfiler(post=lambda *a: None, engine=eng, analyze_interval=0.3)
    for i in range(30):                         # 30 frame trong 1 giay
        p.observe(6, FRAME, BOX, i / 30)
    assert eng.calls[6] <= 4


def test_face_blur_uses_pose_keypoints_and_changes_only_face():
    frame = np.zeros((200, 200, 3), np.uint8)
    frame[::2, :] = 255                         # soc ngang de lam mo co tac dung
    before = frame.copy()
    kps = [[100, 40], [95, 35], [105, 35], [90, 38], [110, 38]] + [[0, 0]] * 12
    conf = [0.9] * 5 + [0.0] * 12
    rect = face_rect((60, 20, 80, 170), kps, conf)
    x0, y0, x1, y1 = rect
    assert x0 < 90 and x1 > 110 and y0 < 35 and y1 > 40
    blur_faces(frame, [rect])
    assert not np.array_equal(frame[y0:y1, x0:x1], before[y0:y1, x0:x1])
    assert np.array_equal(frame[y1 + 5:, :], before[y1 + 5:, :])


def test_face_rect_fallback_without_keypoints():
    x0, y0, x1, y1 = face_rect((50, 20, 40, 160))
    assert y0 == 20 and 20 < y1 <= 20 + 160 * 0.5 and 50 <= x0 < x1 <= 90
