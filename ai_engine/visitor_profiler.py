"""
visitor_profiler.py  —  F3.2 Uoc luong gioi tinh, khoang tuoi, nhom khu vuc cho khach VAO cau
=============================================================================================
Phu trach: MINH.   Yeu cau: FR-09, NFR-05, BRULE-05, BRULE-06 (BRD Sprint 1).

Tach tu phan nhan khau hoc trong camera_in.py (YOLO-pose keypoints +
DemographicsEngine bo phieu theo thoi gian + luu ho so 1 lan + thong ke khu
vuc tong hop) de dung cho he thong 2 camera chan cau (camera_bridge.py).
Phan loi AI van nam o demographics_engine.py / age_gender_estimator.py /
region_mapping.py (khong doi).

Nang cap so voi camera_in.py:
  1. Chi lap ho so cho khach THUC SU VAO cau (qua vach ke) -> so ho so khop
     voi bien dem `dem`, khong lap ho so cho nguoi chi dung ngoai / di ngang.
  2. Bat dau bo phieu TU LUC khach con o phia ngoai dang di toi (luc do mat
     huong ve camera, nhin ro nhat) -> qua vach la thuong da du phieu.
  3. Gioi han tan suat goi DeepFace moi nguoi (``analyze_interval``) de
     camera khong bi giat khi dong nguoi.
  4. BRULE-06: khach da vao ma sau ``give_up_sec`` giay van chua du tin cay
     >= 70% -> van ghi 1 ho so "Khong xac dinh" (gender = None) de tong so
     ho so = tong luot vao, nhung KHONG dua vao ty le gioi tinh / tuoi.
  5. NFR-05: lam mo khuon mat tren man hinh hien thi (``blur_faces``). Anh
     goc chi dung de phan tich trong bo nho, khong luu ra dia.
  6. Nhom khu vuc (TUY CHON, mac dinh TAT): chi gui so dem TONG HOP theo
     gio qua /region_stats, khong gan vao ho so ca nhan (region_mapping.py).

LUU Y VE "QUOC TICH": camera KHONG xac dinh duoc quoc tich. DeepFace chi
uoc luong 4 nhom khu vuc rong (Dong A / Noi dia, Phuong Tay, Nam A, Khac)
va gop chung khach Viet voi khach Han, Nhat, Trung... Muon so "trong nuoc /
nuoc ngoai" chinh xac phai dung du lieu ve quoc te (FR-15) hoac QR check-in.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import cv2

GENDER_VI = {"Man": "Nam", "Woman": "Nu"}
UNKNOWN_AGE = "Khong xac dinh"

# Chi so khop COCO-pose cua vung mat: mui, 2 mat, 2 tai
_FACE_KPS = (0, 1, 2, 3, 4)


def extract_keypoints(results, idx):
    """(keypoints_xy, keypoints_conf) cua nguoi thu idx tu ket qua YOLO-pose,
    hoac (None, None) neu model khong co keypoints (model detect thuong)."""
    kp = getattr(results, "keypoints", None)
    if kp is None or kp.xy is None:
        return None, None
    try:
        xy = kp.xy[idx].tolist()
        conf = kp.conf[idx].tolist() if kp.conf is not None else [1.0] * len(xy)
        return xy, conf
    except (IndexError, TypeError):
        return None, None


def face_rect(box, keypoints=None, kp_conf=None, min_conf=0.3):
    """Vung mat (x0, y0, x1, y1) de lam mo. Uu tien keypoint mui/mat/tai cua
    YOLO-pose; khong co thi uoc luong = phan tren cung cua khung nguoi."""
    x, y, w, h = box
    if keypoints is not None and kp_conf is not None and len(keypoints) > 4:
        pts = [keypoints[i] for i in _FACE_KPS
               if kp_conf[i] >= min_conf and (keypoints[i][0] > 0 or keypoints[i][1] > 0)]
        if len(pts) >= 2:
            xs, ys = [p[0] for p in pts], [p[1] for p in pts]
            size = max(max(xs) - min(xs), max(ys) - min(ys), w * 0.25)
            cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
            half = size * 0.9
            return int(cx - half), int(cy - half * 1.2), int(cx + half), int(cy + half)
    head_h = min(h, max(w * 0.9, h * 0.22))
    return int(x + w * 0.1), int(y), int(x + w * 0.9), int(y + head_h)


def blur_faces(frame, rects):
    """NFR-05: lam mo cac vung mat tren frame HIEN THI (sua tai cho)."""
    fh, fw = frame.shape[:2]
    for x0, y0, x1, y1 in rects:
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(fw, x1), min(fh, y1)
        if x1 - x0 < 4 or y1 - y0 < 4:
            continue
        roi = frame[y0:y1, x0:x1]
        k = max(15, (min(x1 - x0, y1 - y0) // 3) | 1)
        frame[y0:y1, x0:x1] = cv2.GaussianBlur(roi, (k, k), 0)


@dataclass
class _Track:
    first_seen: float
    last_seen: float
    last_analyzed: float = -1e9
    entered_at: Optional[float] = None
    info: Optional[dict] = None
    done: bool = False
    saved: Optional[dict] = None


class VisitorProfiler:
    """Quan ly ho so nhan khau hoc theo track_id cho 1 camera chan cau.

    Cach dung trong vong lap camera:
        profiler.observe(tid, frame, box, now, keypoints, kp_conf)   # moi frame
        profiler.mark_entered(tid, now)                              # khi qua vach vao cau
        profiler.step(now)                                           # cuoi moi frame
        lines = profiler.label(tid)                                  # chu hien canh khung nguoi

    ``post(path, payload)`` la ham gui API (camera_bridge truyen vao), de
    module nay khong phu thuoc mang va de kiem thu.
    """

    def __init__(self, post: Callable[[str, dict], object], engine=None, enable_region: bool = False,
                 analyze_interval: float = 0.3, give_up_sec: float = 5.0,
                 gone_sec: float = 1.5, forget_sec: float = 30.0):
        if engine is None:
            from demographics_engine import DemographicsEngine
            engine = DemographicsEngine(enable_region=enable_region)
        self.engine = engine
        self.post = post
        self.enable_region = enable_region
        self.analyze_interval = analyze_interval
        self.give_up_sec = give_up_sec
        self.gone_sec = gone_sec
        self.forget_sec = forget_sec
        self._tracks: Dict[int, _Track] = {}
        self.saved_count = 0
        self.unknown_count = 0

    # ------------------------------------------------------------ vong lap
    def wants(self, tid: int) -> bool:
        """Con can phan tich nguoi nay khong (chua chot ho so)."""
        t = self._tracks.get(tid)
        return t is None or not t.done

    def observe(self, tid: int, frame, box, now: float, keypoints=None, kp_conf=None):
        t = self._tracks.get(tid)
        if t is None:
            t = self._tracks[tid] = _Track(first_seen=now, last_seen=now)
        t.last_seen = now
        if t.done or now - t.last_analyzed < self.analyze_interval:
            return
        t.last_analyzed = now
        t.info = self.engine.update(tid, frame, box, keypoints=keypoints, kp_conf=kp_conf)
        if t.entered_at is not None and t.info.get("ready"):
            self._save(tid, t)

    def mark_entered(self, tid: int, now: float):
        t = self._tracks.get(tid)
        if t is None:
            t = self._tracks[tid] = _Track(first_seen=now, last_seen=now)
        if t.done and t.saved is None:
            t.done = False          # da ra roi nay quay lai vao -> lap ho so tiep
        if t.done:
            return
        t.entered_at = now
        if t.info and t.info.get("ready"):
            self._save(tid, t)

    def mark_exited(self, tid: int):
        """Khach di RA (chua tung vao o camera nay) -> ngung phan tich, khong lap ho so."""
        t = self._tracks.get(tid)
        if t is not None and t.entered_at is None and not t.done:
            t.done = True
            self.engine.forget(tid)

    def step(self, now: float):
        for tid, t in list(self._tracks.items()):
            if t.entered_at is not None and not t.done:
                timed_out = now - t.entered_at >= self.give_up_sec
                gone = now - t.last_seen >= self.gone_sec
                if timed_out or gone:
                    self._save_unknown(tid, t)
            if now - t.last_seen > self.forget_sec:
                self.engine.forget(tid)
                del self._tracks[tid]

    # ---------------------------------------------------------- hien thi
    def label(self, tid: int) -> Optional[List[str]]:
        t = self._tracks.get(tid)
        if t is None:
            return None
        if t.saved is not None:
            if t.saved["gender"] is None:
                return [f"VAO - ID {tid}", "Khong xac dinh"]
            return [f"VAO - ID {tid}", GENDER_VI.get(t.saved["gender"], t.saved["gender"]),
                    t.saved["age_range"]]
        if t.info is not None:
            return [f"ID {tid}", f"dang xac dinh {t.info.get('n_votes', 0)}/3"]
        return None

    # ------------------------------------------------------------ ghi
    def _save(self, tid: int, t: _Track):
        info = t.info
        payload = {"track_id": tid, "age": info.get("age"),
                   "age_range": info.get("age_range") or UNKNOWN_AGE, "gender": info.get("gender")}
        self.post("/visit_events", payload)
        if self.enable_region and info.get("region") and info.get("region_confidence", 0) >= 0.5:
            # chi cong vao bo dem TONG HOP theo gio, khong gan vao ho so ca nhan
            self.post("/region_stats", {"region": info["region"]})
        t.saved, t.done = payload, True
        self.saved_count += 1
        self.engine.forget(tid)

    def _save_unknown(self, tid: int, t: _Track):
        """BRULE-06: chua du tin cay 70% -> 'Khong xac dinh', khong tinh vao ty le."""
        payload = {"track_id": tid, "age": None, "age_range": UNKNOWN_AGE, "gender": None}
        self.post("/visit_events", payload)
        t.saved, t.done = payload, True
        self.unknown_count += 1
        self.engine.forget(tid)
