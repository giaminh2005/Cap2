"""
tests/test_face_align.py  —  Cat mat theo keypoint YOLO-pose + phan tich mat khong can tim mat (DeepFace gia)
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "ai_engine"))

import age_gender_estimator as age  # noqa: E402
import demographics_engine as de  # noqa: E402


def _frame_with_eyes(l, r, nose):
    f = np.zeros((480, 640, 3), np.uint8)
    for (x, y) in (l, r):
        f[int(y) - 2:int(y) + 3, int(x) - 2:int(x) + 3] = 255
    return f, [nose, l, r], [0.9, 0.9, 0.9]


def test_align_puts_eyes_level_at_standard_position():
    # mat nghieng ~20 do, khoang cach 2 mat 40 px
    cx, cy, d, a = 320, 200, 40, math.radians(20)
    l = (cx - d / 2 * math.cos(a), cy - d / 2 * math.sin(a))
    r = (cx + d / 2 * math.cos(a), cy + d / 2 * math.sin(a))
    f, kp, conf = _frame_with_eyes(l, r, (cx, cy + 15))
    face = age.align_face_from_keypoints(f, kp, conf)
    assert face.shape == (224, 224, 3)
    ys, xs = np.where(face[:, :, 0] > 120)
    left, right = xs < 112, xs >= 112
    # 2 mat nam ngang (cung hang), o ~38% chieu cao, cach nhau ~33% chieu rong
    assert abs(ys[left].mean() - ys[right].mean()) < 3
    assert abs(ys.mean() - 0.38 * 224) < 4
    assert abs((xs[right].mean() - xs[left].mean()) - 0.33 * 224) < 5


def test_align_rejects_unreliable_keypoints():
    f, kp, _ = _frame_with_eyes((300, 200), (340, 200), (320, 215))
    assert age.align_face_from_keypoints(f, kp, [0.9, 0.2, 0.9]) is None
    assert age.align_face_from_keypoints(f, None, None) is None


class FakeDF:
    def __init__(self, man=60.0):
        self.calls, self.man = [], man

    def analyze(self, img_path, actions, detector_backend, **kw):
        self.calls.append((tuple(actions), detector_backend))
        flipped = len(self.calls) % 2 == 0
        m = (self.man + 30) if flipped else self.man        # anh lat cho ket qua chac hon
        return [{"gender": {"Man": m, "Woman": 100 - m}, "age": 30, "race": {"asian": 80, "white": 20}}]


def test_aligned_face_skips_detector_and_flips_when_unsure(monkeypatch):
    fake = FakeDF(man=60.0)
    monkeypatch.setattr(age, "_load_deepface", lambda: fake)
    r = age.estimate_from_aligned_face(np.zeros((224, 224, 3), np.uint8))
    assert all(b == "skip" for _, b in fake.calls)                 # khong chay buoc tim mat
    assert len(fake.calls) == 2 and fake.calls[1][0] == ("gender",)  # 60% < 85% -> phan tich them anh lat
    assert r["gender"] == "Man" and r["gender_confidence"] == 75.0  # trung binh 60 va 90
    sure = FakeDF(man=95.0)
    monkeypatch.setattr(age, "_load_deepface", lambda: sure)
    age.estimate_from_aligned_face(np.zeros((224, 224, 3), np.uint8))
    assert len(sure.calls) == 1                                    # da chac -> khong lat


def test_engine_uses_keypoint_path_weights_confidence_and_stops_race(monkeypatch):
    fake = FakeDF(man=97.0)
    monkeypatch.setattr(age, "_load_deepface", lambda: fake)
    eng = de.DemographicsEngine(enable_region=True)
    f, kp, conf = _frame_with_eyes((300, 200), (340, 200), (320, 215))
    for _ in range(6):
        res = eng.update(1, f, (250, 150, 140, 300), keypoints=kp, kp_conf=conf)
    assert eng.last_path == "keypoint" and res["gender"] == "Man" and res["ready"]
    race_calls = [a for a, _ in fake.calls if "race" in a]
    assert len(race_calls) == de.RACE_VOTES                       # du phieu khu vuc thi thoi chay race
    # phieu 55% gan nhu khong co trong so
    eng.voter.add_vote(2, "Woman", (55 - 50) / 50)
    assert eng.voter.tally(2)[0] == "Woman" and abs(sum(w for _, w in eng.voter._state(2).votes) - 0.1) < 1e-9
