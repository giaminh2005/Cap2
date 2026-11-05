"""
line_crossing.py  —  F1.2 / F1.3 Xac dinh khach DI VAO hay DI RA cau qua 1 vach ke
====================================================================================
Phu trach: MINH.   Yeu cau: FR-02, FR-03 (BRD Sprint 1).

Bo tri camera (moi chan cau 1 camera):
    Camera dat tren cau, quay tu cau RA chan cau, vuong goc voi cau. Tren
    khung hinh ke 1 VACH vuong goc voi huong di cua khach. Vach chia khung
    hinh thanh 2 phia:
        - "phia cau"  : phia gan cau (thuong la NUA DUOI khung hinh, gan camera)
        - "phia ngoai": phia chan cau / duong pho
    Khach di tu phia ngoai SANG phia cau  -> "in"  (vao cau)
    Khach di tu phia cau SANG phia ngoai  -> "out" (ra khoi cau)

Thuat toan (vector):
    Vach la doan P1 -> P2. Voi diem chan cua khach Q, tinh tich co huong
        d = ((P2 - P1) x (Q - P1)) / |P2 - P1|
    = khoang cach co dau tu Q toi vach. Dau cua d cho biet Q o phia nao.
    Phia cau la phia co cung dau voi 1 diem mau B (do nguoi dung chon).
    Moi track_id nho "phia da xac nhan" gan nhat; khi phia doi dau thi
    sinh 1 su kien in/out.

Chong dem sai:
    - Dung DIEM CHAN (giua canh duoi khung nguoi) thay vi tam khung, vi
      vach ke nam tren mat dat.
    - Vung dem (``min_dist``): chi xac nhan phia khi diem chan cach vach
      >= min_dist (theo ty le khung hinh). Nguoi dung ngay tren vach,
      lac qua lac lai, khong bi dem nhieu lan.
    - Lan dau thay 1 track_id chi GHI NHO phia, khong sinh su kien (nguoi
      dang dung san o 1 phia khi camera bat len khong bi tinh la vua qua vach).
    - ``forget_sec``: xoa track khong con xuat hien de giai phong bo nho.

Toa do dung dang CHUAN HOA 0..1 (x / rong, y / cao) de cau hinh vach khong
phu thuoc do phan giai camera.
"""

import json
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

Point = Tuple[float, float]


@dataclass
class _TrackSide:
    side: int          # +1 = phia cau, -1 = phia ngoai
    last_seen: float


@dataclass
class LineCrossingCounter:
    p1: Point = (0.0, 0.5)
    p2: Point = (1.0, 0.5)
    bridge_point: Point = (0.5, 1.0)   # 1 diem bat ky nam o PHIA CAU
    min_dist: float = 0.03             # vung dem quanh vach (3% khung hinh)
    forget_sec: float = 5.0
    _tracks: Dict[int, _TrackSide] = field(default_factory=dict, repr=False)

    def __post_init__(self):
        if self._length() == 0:
            raise ValueError("Vach ke phai co 2 diem khac nhau.")
        if abs(self._raw_distance(self.bridge_point)) < 1e-9:
            raise ValueError("Diem 'phia cau' khong duoc nam tren vach ke.")
        self._bridge_sign = 1 if self._raw_distance(self.bridge_point) > 0 else -1

    # ------------------------------------------------------------ hinh hoc
    def _length(self) -> float:
        dx, dy = self.p2[0] - self.p1[0], self.p2[1] - self.p1[1]
        return (dx * dx + dy * dy) ** 0.5

    def _raw_distance(self, q: Point) -> float:
        (x1, y1), (x2, y2) = self.p1, self.p2
        cross = (x2 - x1) * (q[1] - y1) - (y2 - y1) * (q[0] - x1)
        return cross / self._length()

    def signed_distance(self, q: Point) -> float:
        """> 0: Q o phia cau; < 0: Q o phia ngoai (don vi: ty le khung hinh)."""
        return self._raw_distance(q) * self._bridge_sign

    # ------------------------------------------------------------- dem
    def update(self, track_id: int, foot: Point, now: float) -> Optional[str]:
        """Goi moi frame cho moi nguoi dang theo doi.
        Tra ve "in", "out" hoac None (chua qua vach)."""
        d = self.signed_distance(foot)
        event = None
        if abs(d) >= self.min_dist:
            side = 1 if d > 0 else -1
            prev = self._tracks.get(track_id)
            if prev is not None and prev.side != side:
                event = "in" if side == 1 else "out"
            self._tracks[track_id] = _TrackSide(side=side, last_seen=now)
        elif track_id in self._tracks:
            self._tracks[track_id].last_seen = now
        self._forget(now)
        return event

    def _forget(self, now: float):
        stale = [t for t, s in self._tracks.items() if now - s.last_seen > self.forget_sec]
        for t in stale:
            del self._tracks[t]

    # ------------------------------------------------------ luu cau hinh
    def to_dict(self) -> dict:
        return {"p1": list(self.p1), "p2": list(self.p2),
                "bridge_point": list(self.bridge_point), "min_dist": self.min_dist}

    def save(self, path: str):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "LineCrossingCounter":
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls(p1=tuple(d["p1"]), p2=tuple(d["p2"]),
                   bridge_point=tuple(d["bridge_point"]), min_dist=d.get("min_dist", 0.03))


def foot_point(box, frame_w: int, frame_h: int) -> Point:
    """Diem chan (giua canh duoi) cua khung nguoi (x, y, w, h), chuan hoa 0..1."""
    x, y, w, h = box
    return ((x + w / 2) / frame_w, (y + h) / frame_h)


class FacadeCounter:
    """F1.4 / BRULE-10 - dem luot di qua VUNG MAT TIEN (phia ngoai vach) ma
    KHONG vao cau. Moi track_id chi tinh 1 lan khi roi khoi khung hinh, ke ca
    dung lai chup anh lau; nguoi da qua vach (vao hoac ra cau) khong tinh.

        fc.update(tid, outside=True/False, now)   # moi frame
        fc.mark_crossed(tid)                      # khi qua vach
        n = fc.collect(now)                       # so luot mat tien vua ket thuc
    """

    def __init__(self, min_visible_sec: float = 1.0, gone_sec: float = 2.0):
        self.min_visible_sec, self.gone_sec = min_visible_sec, gone_sec
        self._t: Dict[int, dict] = {}

    def update(self, tid: int, outside: bool, now: float):
        t = self._t.setdefault(tid, {"first": now, "last": now, "outside": True, "crossed": False})
        t["last"] = now
        if not outside:
            t["outside"] = False

    def mark_crossed(self, tid: int):
        if tid in self._t:
            self._t[tid]["crossed"] = True

    def collect(self, now: float) -> int:
        n = 0
        for tid, t in list(self._t.items()):
            if now - t["last"] >= self.gone_sec:
                if t["outside"] and not t["crossed"] and t["last"] - t["first"] >= self.min_visible_sec:
                    n += 1
                del self._t[tid]
        return n
