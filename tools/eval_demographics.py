"""
tools/eval_demographics.py  —  Do do chinh xac NHAN DIEN cho nghiem thu FR-09 va NFR-08
========================================================================================
Chay CUNG ham nhan dien voi camera (age_gender_estimator.estimate_age_gender,
DeepFace) tren tap anh cong khai co nhan, roi tinh:

    FR-09 (BRD) / Sprint 0 Bang 8:
        - Gioi tinh dung            >= 85%
        - Nhom tuoi dung nhom       >= 55%
        - Nhom tuoi sai <= 1 nhom   >= 85%
    NFR-08: chenh lech do chinh xac gioi tinh giua cac nhom nhan khau <= 5 diem %
    Them: do phu (ty le anh tim thay mat), do chinh xac "trong nuoc / nuoc ngoai"
          (UOC LUONG: nhan that suy tu cot race - xem ghi chu ORIGIN_PROXY).

TAP DU LIEU HO TRO
  FairFace (https://github.com/joojs/fairface): thu muc anh + fairface_label_val.csv
      cot: file, age (0-2, 3-9, ..., more than 70), gender (Male/Female), race
      python tools/eval_demographics.py --dataset fairface --images D:/fairface --labels D:/fairface/fairface_label_val.csv --limit 2000
  UTKFace (https://susanqq.github.io/UTKFace/): ten tep "<tuoi>_<gioi>_<race>_<ngay>.jpg"
      gioi 0 = nam, 1 = nu; race 0 trang, 1 den, 2 chau A, 3 An Do, 4 khac
      python tools/eval_demographics.py --dataset utkface --images D:/UTKFace --limit 2000

Ket qua: bang tong hop + bang theo tung nhom -> tep .md va .csv (canh thu muc anh hoac --out).
Can cai deepface (pip install deepface tf-keras). Lan dau chay se tai model.
"""

import argparse
import csv
import os
import random
import sys
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "ai_engine"))

GENDER_MIN, AGE_EXACT_MIN, AGE_NEAR_MIN, FAIR_GAP_MAX = 85.0, 55.0, 85.0, 5.0

FAIRFACE_AGE = ["0-2", "3-9", "10-19", "20-29", "30-39", "40-49", "50-59", "60-69", "more than 70"]
FAIRFACE_EDGES = [(0, 2), (3, 9), (10, 19), (20, 29), (30, 39), (40, 49), (50, 59), (60, 69), (70, 200)]
PROJECT_AGE = ["0-5", "6-12", "13-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65-69", "70+"]
PROJECT_EDGES = [(0, 5), (6, 12), (13, 17), (18, 24), (25, 34), (35, 44), (45, 54), (55, 64), (65, 69), (70, 200)]
UTK_RACE = {"0": "White", "1": "Black", "2": "Asian", "3": "Indian", "4": "Others"}
# ORIGIN_PROXY: tap cong khai KHONG co quoc tich. Dung race lam nhan xap xi giong cach he thong suy
# "trong nuoc" (nhom Dong A) -> chi de tham khao, khong phai do chinh xac quoc tich.
DOMESTIC_RACES = {"East Asian", "Southeast Asian", "Asian"}


def age_bucket(age, edges) -> int:
    if age is None:
        return -1
    for i, (lo, hi) in enumerate(edges):
        if lo <= age <= hi:
            return i
    return -1


def evaluate(records):
    """records: list dict {group, true_gender (Man/Woman), true_age (chi so nhom), true_origin,
    pred_gender (Man/Woman/None), pred_age (chi so nhom, -1 neu khong co), pred_origin}.
    pred_gender None = khong tim thay mat / khong xac dinh -> tinh vao do phu, KHONG tinh vao do chinh xac."""
    n = len(records)
    found = [r for r in records if r["pred_gender"] in ("Man", "Woman")]

    def acc(rows, ok):
        return round(sum(1 for r in rows if ok(r)) / len(rows) * 100, 1) if rows else None

    with_age = [r for r in found if r["pred_age"] >= 0 and r["true_age"] >= 0]
    with_origin = [r for r in found if r.get("pred_origin") and r.get("true_origin")]
    overall = {
        "n_images": n, "n_found": len(found), "coverage_pct": round(len(found) / n * 100, 1) if n else None,
        "gender_acc": acc(found, lambda r: r["pred_gender"] == r["true_gender"]),
        "age_exact_acc": acc(with_age, lambda r: r["pred_age"] == r["true_age"]),
        "age_within1_acc": acc(with_age, lambda r: abs(r["pred_age"] - r["true_age"]) <= 1),
        "origin_acc": acc(with_origin, lambda r: r["pred_origin"] == r["true_origin"]),
        "n_origin": len(with_origin),
    }
    groups = {}
    for r in found:
        groups.setdefault(r["group"], []).append(r)
        groups.setdefault(f"Giới tính thật: {'Nam' if r['true_gender'] == 'Man' else 'Nữ'}", []).append(r)
    by_group = {g: {"n": len(rows), "gender_acc": acc(rows, lambda r: r["pred_gender"] == r["true_gender"])}
                for g, rows in sorted(groups.items())}
    eth = [v["gender_acc"] for g, v in by_group.items() if not g.startswith("Giới tính") and v["n"] >= 20]
    gap = round(max(eth) - min(eth), 1) if len(eth) >= 2 else None
    verdict = {
        "gender_pass": overall["gender_acc"] is not None and overall["gender_acc"] >= GENDER_MIN,
        "age_exact_pass": overall["age_exact_acc"] is not None and overall["age_exact_acc"] >= AGE_EXACT_MIN,
        "age_within1_pass": overall["age_within1_acc"] is not None and overall["age_within1_acc"] >= AGE_NEAR_MIN,
        "fairness_gap_pct": gap,
        "fairness_pass": gap is not None and gap <= FAIR_GAP_MAX,
    }
    return {"overall": overall, "by_group": by_group, "verdict": verdict}


# ------------------------------------------------------------------ du lieu
def load_fairface(images, labels, limit, seed):
    rows = []
    with open(labels, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({"path": os.path.join(images, r["file"]), "group": r["race"],
                         "true_gender": "Man" if r["gender"] == "Male" else "Woman",
                         "true_age": FAIRFACE_AGE.index(r["age"]) if r["age"] in FAIRFACE_AGE else -1,
                         "true_origin": "Trong nuoc" if r["race"] in DOMESTIC_RACES else "Nuoc ngoai"})
    return _sample(rows, limit, seed), FAIRFACE_EDGES


def load_utkface(images, limit, seed):
    rows = []
    for fn in os.listdir(images):
        parts = fn.split("_")
        if len(parts) < 4 or not parts[0].isdigit() or parts[1] not in ("0", "1") or parts[2] not in UTK_RACE:
            continue
        race = UTK_RACE[parts[2]]
        rows.append({"path": os.path.join(images, fn), "group": race,
                     "true_gender": "Man" if parts[1] == "0" else "Woman",
                     "true_age": age_bucket(int(parts[0]), PROJECT_EDGES),
                     "true_origin": "Trong nuoc" if race in DOMESTIC_RACES else "Nuoc ngoai"})
    return _sample(rows, limit, seed), PROJECT_EDGES


def _sample(rows, limit, seed):
    if limit and len(rows) > limit:
        random.Random(seed).shuffle(rows)
        rows = rows[:limit]
    return rows


def deepface_predictor(with_origin):
    import cv2
    from age_gender_estimator import estimate_age_gender
    from region_mapping import classify_region_from_deepface_race
    from visitor_profiler import REGION_TO_ORIGIN

    def predict(path):
        img = cv2.imread(path)
        faces = estimate_age_gender(img, include_race=with_origin) if img is not None else []
        if not faces:
            return None, None, None
        f = max(faces, key=lambda x: x["region"].get("w", 0) * x["region"].get("h", 0))
        origin = None
        if with_origin:
            region, conf = classify_region_from_deepface_race(f.get("race_probs"))
            origin = REGION_TO_ORIGIN.get(region) if region and conf >= 0.5 else None
        return f["gender"], f["age"], origin
    return predict


def write_report(base, dataset, result, model_note):
    o, v, g = result["overall"], result["verdict"], result["by_group"]

    def fmt(x):
        return "–" if x is None else f"{x}%"

    def ok(b):
        return "ĐẠT" if b else "CHƯA ĐẠT"

    lines = ["# Kết quả đo độ chính xác nhận diện (FR-09, NFR-08)", "",
             f"- Thời điểm: {datetime.now():%H:%M %d/%m/%Y} · tập dữ liệu: **{dataset}** · {model_note}",
             f"- Số ảnh: {o['n_images']} · tìm thấy khuôn mặt: {o['n_found']} ({fmt(o['coverage_pct'])})", "",
             "| Chỉ tiêu | Kết quả | Yêu cầu | Đánh giá |", "|---|---|---|---|",
             f"| Giới tính đúng | {fmt(o['gender_acc'])} | ≥ {GENDER_MIN:.0f}% | {ok(v['gender_pass'])} |",
             f"| Nhóm tuổi đúng nhóm | {fmt(o['age_exact_acc'])} | ≥ {AGE_EXACT_MIN:.0f}% | {ok(v['age_exact_pass'])} |",
             f"| Nhóm tuổi sai không quá 1 nhóm | {fmt(o['age_within1_acc'])} | ≥ {AGE_NEAR_MIN:.0f}% | {ok(v['age_within1_pass'])} |",
             f"| Chênh lệch giới tính giữa các nhóm (NFR-08) | {fmt(v['fairness_gap_pct'])} | ≤ {FAIR_GAP_MAX:.0f} điểm % | {ok(v['fairness_pass'])} |",
             f"| Trong nước / nước ngoài (tham khảo) | {fmt(o['origin_acc'])} | – | nhãn suy từ chủng tộc, không phải quốc tịch |",
             "", "## Độ chính xác giới tính theo nhóm", "", "| Nhóm | Số ảnh | Giới tính đúng |", "|---|---|---|"]
    lines += [f"| {k} | {x['n']} | {fmt(x['gender_acc'])} |" for k, x in g.items()]
    lines += ["", "Ảnh không tìm thấy khuôn mặt được tính vào độ phủ, không tính vào độ chính xác "
                  "(tương ứng BRULE-06: kết quả không chắc chắn ghi là “Không xác định”). "
                  "Nhóm dưới 20 ảnh không dùng để tính chênh lệch NFR-08."]
    text = "\n".join(lines)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(text + "\n")
    with open(base + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["nhom", "so_anh", "gioi_tinh_dung_pct"])
        for k, x in g.items():
            w.writerow([k, x["n"], x["gender_acc"]])
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="Đo độ chính xác giới tính / tuổi / công bằng (FR-09, NFR-08)")
    ap.add_argument("--dataset", choices=("fairface", "utkface"), required=True)
    ap.add_argument("--images", required=True, help="Thư mục ảnh")
    ap.add_argument("--labels", help="Tệp nhãn CSV (bắt buộc với FairFace)")
    ap.add_argument("--limit", type=int, default=1000, help="Số ảnh lấy ngẫu nhiên (0 = tất cả)")
    ap.add_argument("--seed", type=int, default=50)
    ap.add_argument("--no-origin", action="store_true", help="Bỏ đo trong/ngoài nước (nhanh hơn)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    if args.dataset == "fairface":
        if not args.labels:
            ap.error("FairFace cần --labels (vd fairface_label_val.csv)")
        rows, edges = load_fairface(args.images, args.labels, args.limit, args.seed)
    else:
        rows, edges = load_utkface(args.images, args.limit, args.seed)
    if not rows:
        print("Không tìm thấy ảnh có nhãn hợp lệ.")
        return 1
    predict = deepface_predictor(with_origin=not args.no_origin)
    records = []
    for i, r in enumerate(rows, 1):
        g, age, origin = predict(r["path"])
        records.append({**r, "pred_gender": g, "pred_age": age_bucket(age, edges) if g else -1, "pred_origin": origin})
        if i % 50 == 0 or i == len(rows):
            print(f"  {i}/{len(rows)} ảnh")
    result = evaluate(records)
    out = args.out or os.path.join(os.path.abspath(args.images), f"ketqua_nhan_dien_{args.dataset}")
    print("\n" + write_report(out, args.dataset, result, "DeepFace + age_gender_estimator.py của dự án"))
    print(f"\nĐã lưu {out}.md và {out}.csv")
    v = result["verdict"]
    return 0 if v["gender_pass"] and v["age_exact_pass"] and v["age_within1_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
