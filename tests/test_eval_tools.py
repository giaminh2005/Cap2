"""
tests/test_eval_tools.py  —  Kiem thu phan TINH TOAN cua 2 script nghiem thu (khong can YOLO / DeepFace)
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

import eval_counting as ec  # noqa: E402
import eval_demographics as ed  # noqa: E402


def test_error_pct_and_verdict():
    assert ec.error_pct(9, 10) == 10.0 and ec.error_pct(0, 0) == 0.0 and ec.error_pct(3, 0) == 100.0
    rows = [{"video": "a", "true_in": 20, "pred_in": 18, "true_out": 10, "pred_out": 10},
            {"video": "b", "true_in": 50, "pred_in": 56, "true_out": 40, "pred_out": 37},
            {"video": "c", "true_in": 10, "pred_in": 12, "true_out": 10, "pred_out": 11}]
    s = ec.summarize(rows, ["in", "out"])
    assert s["in"]["total_error_pct"] == round(abs(86 - 80) / 80 * 100, 1)
    assert s["in"]["mean_error_pct"] == round((10 + 12 + 20) / 3, 1)
    assert s["verdict"]["mvp_pass"] and not s["verdict"]["acceptance_pass"] and s["verdict"]["n_videos"] == 3


def test_age_bucket():
    assert ed.age_bucket(25, ed.PROJECT_EDGES) == ed.PROJECT_AGE.index("25-34")
    assert ed.age_bucket(2, ed.FAIRFACE_EDGES) == 0 and ed.age_bucket(85, ed.FAIRFACE_EDGES) == 8
    assert ed.age_bucket(None, ed.PROJECT_EDGES) == -1


def _rec(group, tg, pg, ta=4, pa=4):
    return {"group": group, "true_gender": tg, "pred_gender": pg, "true_age": ta, "pred_age": pa,
            "true_origin": "Trong nuoc", "pred_origin": "Trong nuoc"}


def test_evaluate_metrics_and_fairness():
    recs = ([_rec("East Asian", "Man", "Man")] * 45 + [_rec("East Asian", "Man", "Woman")] * 5      # 90%
            + [_rec("White", "Woman", "Woman")] * 40 + [_rec("White", "Woman", "Man")] * 10         # 80%
            + [_rec("Black", "Man", None, pa=-1)] * 10)                                              # khong thay mat
    r = ed.evaluate(recs)
    o, v = r["overall"], r["verdict"]
    assert o["n_images"] == 110 and o["n_found"] == 100 and o["coverage_pct"] == 90.9
    assert o["gender_acc"] == 85.0 and v["gender_pass"]
    assert r["by_group"]["East Asian"]["gender_acc"] == 90.0 and r["by_group"]["White"]["gender_acc"] == 80.0
    assert v["fairness_gap_pct"] == 10.0 and not v["fairness_pass"]
    assert o["age_exact_acc"] == 100.0 and v["age_within1_pass"]


def test_utkface_loader(tmp_path):
    for fn in ("25_1_2_20170116.jpg", "8_0_0_2017.jpg", "bad.jpg", "30_9_1_x.jpg"):
        (tmp_path / fn).write_bytes(b"")
    rows, edges = ed.load_utkface(str(tmp_path), 0, 1)
    assert len(rows) == 2 and edges is ed.PROJECT_EDGES
    asian = next(r for r in rows if r["group"] == "Asian")
    assert asian["true_gender"] == "Woman" and asian["true_origin"] == "Trong nuoc"


def test_fit_age_calibration_fixes_regression_to_mean():
    # DeepFace don tuoi ve giua: tuoi doan = 0.5 * that + 15
    recs = [{"true_age_value": t, "pred_age_value": 0.5 * t + 15} for t in range(5, 80, 2)]
    cal = ed.fit_age_calibration(recs)
    assert abs(cal["a"] - 2.0) < 1e-6 and abs(cal["b"] + 30) < 1e-6
    assert cal["mae_after"] < 0.01 < cal["mae_before"]
    assert ed.fit_age_calibration(recs[:10]) is None
