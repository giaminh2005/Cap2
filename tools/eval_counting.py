"""
tools/eval_counting.py  —  Do sai so DEM NGUOI de nghiem thu NFR-02 / O2 (Sprint 0 Bang 8)
==========================================================================================
Chay CUNG thuat toan voi camera that (YOLO tracking + vach ke LineCrossingCounter)
tren cac doan video thu, so voi so DEM TAY.

    NFR-02: sai so <= 15% o MVP, <= 10% khi nghiem thu thuc te.
    Sprint 0 Bang 8: it nhat 3 doan video voi mat do khac nhau.

1) Che do LUOT QUA VACH (mac dinh) - tep CSV:
       video,true_in,true_out,line
       video/thua.mp4,23,19,
       video/dong.mp4,61,55,ai_engine/config/line_cam1.json
   (cot line de trong = vach mac dinh ngang giua hinh, phia cau = nua duoi)

2) Che do SO NGUOI TRONG KHUNG HINH (--presence) - tep CSV:
       video,second,true_count
       video/dong.mp4,10,14
       video/dong.mp4,40,22
   So nguoi YOLO phat hien tai giay do so voi so dem tay tren khung hinh dung yen.

CHAY (tu thu muc goc):
    python tools/eval_counting.py --truth sample_data/eval_counting.csv
    python tools/eval_counting.py --truth sample_data/eval_presence.csv --presence
Ket qua in ra man hinh va ghi them tep .md + .csv canh tep --truth (hoac --out).
"""

import argparse
import csv
import os
import sys
from datetime import datetime

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "ai_engine"))

MVP_LIMIT, ACCEPT_LIMIT = 15.0, 10.0


def error_pct(pred: int, true: int) -> float:
    """Sai so tuong doi (%) so voi dem tay. true = 0 -> 0% neu pred = 0, nguoc lai 100%."""
    if true == 0:
        return 0.0 if pred == 0 else 100.0
    return abs(pred - true) / true * 100


def summarize(rows, keys):
    """rows: list dict co cac cot pred_<k>, true_<k>. Tra ve sai so tong hop moi khoa
    (sai so tren TONG so luot, va trung binh sai so tung video) + ket luan dat/khong dat."""
    out = {}
    for k in keys:
        tp = sum(r[f"pred_{k}"] for r in rows)
        tt = sum(r[f"true_{k}"] for r in rows)
        per = [error_pct(r[f"pred_{k}"], r[f"true_{k}"]) for r in rows]
        out[k] = {"pred": tp, "true": tt, "total_error_pct": round(error_pct(tp, tt), 1),
                  "mean_error_pct": round(sum(per) / len(per), 1) if per else 0.0,
                  "max_error_pct": round(max(per), 1) if per else 0.0}
    worst = max((v["mean_error_pct"] for v in out.values()), default=0.0)
    out["verdict"] = {"mvp_pass": worst <= MVP_LIMIT, "acceptance_pass": worst <= ACCEPT_LIMIT,
                      "worst_mean_error_pct": worst, "n_videos": len({r["video"] for r in rows})}
    return out


def _resolve(path, base):
    return path if os.path.isabs(path) else os.path.normpath(os.path.join(base, path))


def count_crossings(video, line_file, model_name, conf=0.4):
    import cv2
    from line_crossing import LineCrossingCounter, foot_point
    from ultralytics import YOLO

    model = YOLO(model_name)        # model moi cho moi video -> bo theo doi bat dau lai tu dau
    line = LineCrossingCounter.load(line_file) if line_file else LineCrossingCounter()
    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise RuntimeError(f"Không mở được video {video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 15
    n_in = n_out = frame_i = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        t = frame_i / fps
        frame_i += 1
        res = model.track(frame, persist=True, classes=[0], conf=conf, verbose=False)[0]
        if res.boxes is None or res.boxes.id is None:
            continue
        h, w = frame.shape[:2]
        for box, tid in zip(res.boxes, res.boxes.id):
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            ev = line.update(int(tid), foot_point((x1, y1, x2 - x1, y2 - y1), w, h), t)
            if ev == "in":
                n_in += 1
            elif ev == "out":
                n_out += 1
    cap.release()
    return n_in, n_out


def count_presence(video, second, model, conf=0.4):
    import cv2
    cap = cv2.VideoCapture(video)
    cap.set(cv2.CAP_PROP_POS_MSEC, float(second) * 1000)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        raise RuntimeError(f"Không đọc được giây {second} của {video}")
    return len(model(frame, classes=[0], conf=conf, verbose=False)[0].boxes)


def write_report(path_base, mode, rows, summary, model_name):
    keys = ["in", "out"] if mode == "crossing" else ["count"]
    with open(path_base + ".csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    v = summary["verdict"]
    lines = ["# Kết quả đo sai số đếm người (NFR-02)", "",
             f"- Thời điểm: {datetime.now():%H:%M %d/%m/%Y} · mô hình: `{model_name}` · chế độ: "
             f"{'lượt qua vạch' if mode == 'crossing' else 'số người trong khung hình'}",
             f"- Số video: {v['n_videos']} (Sprint 0 yêu cầu ≥ 3 video mật độ khác nhau)", "",
             "| Video | " + " | ".join(f"Đếm tay {k} | Hệ thống {k} | Sai số {k}" for k in keys) + " |",
             "|---|" + "---|---|---|" * len(keys)]
    for r in rows:
        name = os.path.basename(r["video"]) + (f" @ {r['second']}s" if "second" in r else "")
        lines.append(f"| {name} | " + " | ".join(
            f"{r[f'true_{k}']} | {r[f'pred_{k}']} | {error_pct(r[f'pred_{k}'], r[f'true_{k}']):.1f}%" for k in keys) + " |")
    lines += ["", "| Chỉ số | " + " | ".join(keys) + " |", "|---|" + "---|" * len(keys)]
    for label, key in (("Sai số trên tổng", "total_error_pct"), ("Sai số trung bình mỗi video", "mean_error_pct"),
                       ("Sai số lớn nhất", "max_error_pct")):
        lines.append(f"| {label} | " + " | ".join(f"{summary[k][key]}%" for k in keys) + " |")
    lines += ["", f"**MVP (≤ {MVP_LIMIT:.0f}%): {'ĐẠT' if v['mvp_pass'] else 'CHƯA ĐẠT'}** · "
                  f"**Nghiệm thu thực tế (≤ {ACCEPT_LIMIT:.0f}%): {'ĐẠT' if v['acceptance_pass'] else 'CHƯA ĐẠT'}**"]
    with open(path_base + ".md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Đo sai số đếm người so với đếm tay (NFR-02)")
    ap.add_argument("--truth", required=True, help="Tệp CSV số đếm tay")
    ap.add_argument("--presence", action="store_true", help="So số người trong khung hình thay vì lượt qua vạch")
    ap.add_argument("--model", default="yolov8n.pt")
    ap.add_argument("--conf", type=float, default=0.4)
    ap.add_argument("--out", default=None, help="Đường dẫn tệp kết quả (không có đuôi)")
    args = ap.parse_args(argv)

    from ultralytics import YOLO
    model = YOLO(args.model) if args.presence else None
    base = os.path.dirname(os.path.abspath(args.truth))
    rows = []
    with open(args.truth, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            video = _resolve(r["video"].strip(), base)
            if args.presence:
                pred = count_presence(video, r["second"], model, args.conf)
                rows.append({"video": video, "second": r["second"], "true_count": int(r["true_count"]),
                             "pred_count": pred})
            else:
                line = r.get("line", "").strip()
                p_in, p_out = count_crossings(video, _resolve(line, ROOT) if line else None, args.model, args.conf)
                rows.append({"video": video, "true_in": int(r["true_in"]), "true_out": int(r["true_out"]),
                             "pred_in": p_in, "pred_out": p_out})
            print(f"  ✓ {os.path.basename(video)}: {rows[-1]}")
    if not rows:
        print("Tệp CSV không có dòng nào.")
        return 1
    mode = "presence" if args.presence else "crossing"
    summary = summarize(rows, ["count"] if args.presence else ["in", "out"])
    out = args.out or os.path.splitext(os.path.abspath(args.truth))[0] + "_ketqua"
    print("\n" + write_report(out, mode, rows, summary, args.model))
    print(f"\nĐã lưu {out}.md và {out}.csv")
    return 0 if summary["verdict"]["mvp_pass"] else 2


if __name__ == "__main__":
    sys.exit(main())
