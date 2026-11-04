"""
visitor_profiler.py  —  F3.2 Uoc luong gioi tinh, khoang tuoi, trong nuoc / nuoc ngoai cho khach VAO cau
=========================================================================================================
Phu trach: MINH.   Yeu cau: FR-09, BRULE-05, BRULE-06 (BRD Sprint 1).

Tach tu phan nhan khau hoc trong camera_in.py (YOLO-pose keypoints +
DemographicsEngine bo phieu theo thoi gian + luu ho so 1 lan) de dung cho he
thong 2 camera chan cau (camera_bridge.py). Loi AI van nam o
demographics_engine.py / age_gender_estimator.py / region_mapping.py.

Hien tren camera (giong camera_in.py): "Nam/Nu · khoang tuoi · Trong nuoc/Nuoc ngoai"
ngay khi bo phieu du tin cay >= 70%, ke ca truoc khi khach qua vach.

Luu vao CSDL (POST /visit_events) CHI khi khach thuc su VAO cau, 1 lan / nguoi:
  - du tin cay -> gioi tinh, khoang tuoi, nguon khach
  - vao cau ma sau ``give_up_sec`` giay van chua du tin cay -> "Khong xac dinh"
    (BRULE-06: van tinh 1 luot, khong dua vao ty le)

TRONG NUOC / NUOC NGOAI la UOC LUONG tu nhom khu vuc rong cua DeepFace:
    "Dong A / Noi dia" -> Trong nuoc;  Phuong Tay, Nam A, Khac -> Nuoc ngoai
DeepFace KHONG phan biet duoc khach Viet voi khach Han / Nhat / Trung, nen
khach Dong A deu bi tinh la "Trong nuoc". Con so chi dung de xem xu huong.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

GENDER_VI = {"Man": "Nam", "Woman": "Nữ"}
ORIGIN_VI = {"Trong nuoc": "Trong nước", "Nuoc ngoai": "Nước ngoài"}
UNKNOWN_AGE = "Khong xac dinh"
REGION_TO_ORIGIN = {"Dong A / Noi dia": "Trong nuoc", "Phuong Tay": "Nuoc ngoai",
                    "Nam A": "Nuoc ngoai", "Khac": "Nuoc ngoai"}
ORIGIN_MIN_SHARE = 0.55   # nhom khu vuc phai chiem >= 55% trong so phieu moi ket luan


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


@dataclass
class _Track:
    first_seen: float
    last_seen: float
    last_analyzed: float = -1e9
    entered_at: Optional[float] = None
    info: Optional[dict] = None
    region_votes: Dict[str, float] = field(default_factory=dict)
    done: bool = False
    saved: Optional[dict] = None


class VisitorProfiler:
    """Quan ly nhan khau hoc theo track_id cho 1 camera chan cau.

        profiler.observe(tid, frame, box, now, keypoints, kp_conf)   # moi frame
        profiler.mark_entered(tid, now)                              # qua vach VAO cau
        profiler.mark_exited(tid)                                    # qua vach RA
        profiler.step(now)                                           # cuoi moi frame
        lines = profiler.label(tid)                                  # chu hien canh khung nguoi
    """

    def __init__(self, post: Callable[[str, dict], object], engine=None, with_origin: bool = True,
                 camera_id: Optional[int] = None, analyze_interval: float = 0.3, give_up_sec: float = 5.0,
                 gone_sec: float = 1.5, forget_sec: float = 30.0):
        if engine is None:
            from demographics_engine import DemographicsEngine
            engine = DemographicsEngine(enable_region=with_origin)
        self.engine, self.post, self.with_origin, self.camera_id = engine, post, with_origin, camera_id
        self.analyze_interval, self.give_up_sec = analyze_interval, give_up_sec
        self.gone_sec, self.forget_sec = gone_sec, forget_sec
        self._tracks: Dict[int, _Track] = {}
        self.saved_count = 0
        self.unknown_count = 0

    # ----------------------------------------------------------- vong lap
    def wants(self, tid: int) -> bool:
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
        region, conf = t.info.get("region"), float(t.info.get("region_confidence") or 0)
        if region:
            t.region_votes[region] = t.region_votes.get(region, 0.0) + max(conf, 0.05)
        if t.entered_at is not None and t.info.get("ready"):
            self._save(tid, t)

    def mark_entered(self, tid: int, now: float):
        t = self._tracks.get(tid)
        if t is None:
            t = self._tracks[tid] = _Track(first_seen=now, last_seen=now)
        if t.done and t.saved is None:
            t.done = False                     # da ra roi quay lai vao -> lap ho so tiep
        if t.done:
            return
        t.entered_at = now
        if t.info and t.info.get("ready"):
            self._save(tid, t)

    def mark_exited(self, tid: int):
        """Di RA (chua vao o camera nay) -> ngung phan tich, khong lap ho so."""
        t = self._tracks.get(tid)
        if t is not None and t.entered_at is None and not t.done:
            t.done = True
            self.engine.forget(tid)

    def step(self, now: float):
        for tid, t in list(self._tracks.items()):
            if t.entered_at is not None and not t.done:
                if now - t.entered_at >= self.give_up_sec or now - t.last_seen >= self.gone_sec:
                    self._save_unknown(tid, t)
            if now - t.last_seen > self.forget_sec:
                self.engine.forget(tid)
                del self._tracks[tid]

    # ---------------------------------------------------------- ket qua
    def origin_of(self, tid: int) -> Optional[str]:
        t = self._tracks.get(tid)
        if t is None or not self.with_origin or not t.region_votes:
            return None
        total = sum(t.region_votes.values())
        best = max(t.region_votes, key=t.region_votes.get)
        if t.region_votes[best] / total < ORIGIN_MIN_SHARE:
            return None
        return REGION_TO_ORIGIN.get(best)

    def label(self, tid: int) -> Optional[List[str]]:
        """Dong chu hien tren camera (co dau tieng Viet)."""
        t = self._tracks.get(tid)
        if t is None:
            return None
        head = f"VÀO CẦU · ID {tid}" if t.entered_at is not None else f"ID {tid}"
        res = t.saved if t.saved is not None else (t.info if t.info and t.info.get("ready") else None)
        if t.saved is not None and t.saved["gender"] is None:
            return [head, "Không xác định"]
        if res is not None:
            lines = [head, f"{GENDER_VI.get(res['gender'], res['gender'])} · {res.get('age_range') or '?'}"]
            if self.with_origin:
                origin = res.get("origin") if t.saved is not None else self.origin_of(tid)
                lines.append(ORIGIN_VI.get(origin, "Chưa rõ trong/ngoài nước"))
            return lines
        if t.info is not None and not t.done:
            return [head, f"Đang nhận diện {min(t.info.get('n_votes', 0), 3)}/3"]
        return None

    # -------------------------------------------------------------- ghi
    def _save(self, tid: int, t: _Track):
        info = t.info
        payload = {"track_id": tid, "age": info.get("age"),
                   "age_range": info.get("age_range") or UNKNOWN_AGE, "gender": info.get("gender"),
                   "origin": self.origin_of(tid), "camera_id": self.camera_id}
        self.post("/visit_events", payload)
        t.saved, t.done = payload, True
        self.saved_count += 1
        self.engine.forget(tid)

    def _save_unknown(self, tid: int, t: _Track):
        payload = {"track_id": tid, "age": None, "age_range": UNKNOWN_AGE, "gender": None,
                   "origin": None, "camera_id": self.camera_id}
        self.post("/visit_events", payload)
        t.saved, t.done = payload, True
        self.unknown_count += 1
        self.engine.forget(tid)
