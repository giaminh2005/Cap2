"""
group_detector.py  —  F3.1 Phat hien doan khach lon dang di toi cau (FR-08, BRULE-03)
====================================================================================
Phu trach: MINH.

BRULE-03: doan khach lon = nhom tu 10 nguoi di CUNG HUONG (ve phia cau),
khoang cach giua cac thanh vien khong qua 2 m, duy tri it nhat 10 giay.

Camera khong do duoc met, nen 2 m duoc quy doi theo CHIEU CAO KHUNG NGUOI:
nguoi lon cao ~1,6-1,7 m -> 2 m ~ 1,2 lan chieu cao khung nguoi (``gap_factor``).
Hai nguoi "gan nhau" neu khoang cach 2 diem chan <= gap_factor x chieu cao
trung binh cua 2 khung. Nhom = thanh phan lien thong cua do thi "gan nhau".

"Di ve phia cau" = khoang cach co dau toi vach (LineCrossingCounter.
signed_distance) tang dan trong ~1 giay gan nhat va nguoi dang o phia ngoai.
"""

from collections import deque
from typing import Dict, List, Optional, Tuple


class GroupDetector:
    def __init__(self, min_size: int = 10, hold_sec: float = 10.0, gap_factor: float = 1.2,
                 cooldown_sec: float = 180.0, min_speed: float = 0.01, history_sec: float = 1.0):
        self.min_size, self.hold_sec, self.gap_factor = min_size, hold_sec, gap_factor
        self.cooldown_sec, self.min_speed, self.history_sec = cooldown_sec, min_speed, history_sec
        self._hist: Dict[int, deque] = {}
        self._since: Optional[float] = None
        self._last_alert: Optional[float] = None
        self.current_size = 0

    def _approaching(self, tid: int, d: float, now: float) -> bool:
        h = self._hist.setdefault(tid, deque())
        h.append((now, d))
        while h and now - h[0][0] > self.history_sec:
            h.popleft()
        if len(h) < 2 or h[-1][0] - h[0][0] < self.history_sec * 0.5:
            return False
        speed = (h[-1][1] - h[0][1]) / (h[-1][0] - h[0][0])   # ty le khung hinh / giay, > 0 = ve phia cau
        return d < 0 and speed >= self.min_speed

    @staticmethod
    def _largest_cluster(points: List[Tuple[float, float, float]], gap_factor: float) -> int:
        n = len(points)
        parent = list(range(n))

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for i in range(n):
            xi, yi, hi = points[i]
            for j in range(i + 1, n):
                xj, yj, hj = points[j]
                if ((xi - xj) ** 2 + (yi - yj) ** 2) ** 0.5 <= gap_factor * (hi + hj) / 2:
                    parent[find(i)] = find(j)
        sizes: Dict[int, int] = {}
        for i in range(n):
            r = find(i)
            sizes[r] = sizes.get(r, 0) + 1
        return max(sizes.values()) if sizes else 0

    def update(self, people, now: float) -> Optional[int]:
        """people: list (tid, foot_x, foot_y, box_h, signed_distance) toa do chuan hoa 0..1.
        Tra ve so nguoi trong doan khi CAN canh bao (1 lan / cooldown), nguoc lai None."""
        seen = set()
        moving = []
        for tid, fx, fy, bh, d in people:
            seen.add(tid)
            if self._approaching(tid, d, now):
                moving.append((fx, fy, bh))
        for tid in [t for t in self._hist if t not in seen]:
            del self._hist[tid]

        size = self._largest_cluster(moving, self.gap_factor) if len(moving) >= self.min_size else 0
        self.current_size = size
        if size >= self.min_size:
            if self._since is None:
                self._since = now
            held = now - self._since >= self.hold_sec
            cooled = self._last_alert is None or now - self._last_alert >= self.cooldown_sec
            if held and cooled:
                self._last_alert = now
                return size
        else:
            self._since = None
        return None
