"""
crowd_counter.py  —  Nguong canh bao Vang / Do co dieu kien thoi gian (FR-04, FR-06, BRULE-01/02/04)
=================================================================================================
Dung boi camera_bridge.py (camera chan cau 1 quyet dinh muc canh bao).
    CameraThresholds     suc chua (20) va nguong Vang (75% suc chua = 15)
    AlertLevelTracker    Do khi vuot suc chua lien tuc 15 giay, het Do khi <= nguong Vang 15 giay,
                         quyet dinh khi nao gui tin (Do nhac lai toi da 1 lan / 3 phut)
"""

from dataclasses import dataclass


@dataclass
class CameraThresholds:
    """Nguong canh bao THEO BRD Sprint 1 (BRULE-01, BRULE-02, BRULE-04).

    - Suc chua toi da tren cau: 20 nguoi (``alert``, Admin doi duoc qua /config).
    - Canh bao VANG: so nguoi tu 15 (``warning``).
    - Canh bao DO: so nguoi TREN 20 LIEN TUC 15 giay (``red_hold_sec``).
    - Ve Binh thuong: so nguoi <= 15 LIEN TUC 15 giay (``clear_hold_sec``).

    ``status_of`` chi xet SO NGUOI TUC THOI (khong co thoi gian) nen khong bao
    gio tra ve "CRITICAL"; muc Do can dieu kien thoi gian -> dung
    ``AlertLevelTracker`` ben duoi.

    Ma trang thai (giu nguyen ten cu de giao dien/CSDL khong phai sua):
        OK       = Binh thuong
        WARNING  = Vang (15..20 nguoi)
        ALERT    = Vang - da vuot 20 nhung CHUA du 15 giay (dang xac nhan)
        CRITICAL = Do (vuot 20 lien tuc >= 15 giay)
    """
    warning: int = 15
    alert: int = 20
    red_hold_sec: float = 15.0
    clear_hold_sec: float = 15.0

    def status_of(self, count: int) -> str:
        if count > self.alert:
            return "ALERT"
        if count >= self.warning:
            return "WARNING"
        return "OK"

    @classmethod
    def from_alert_threshold(cls, alert: int) -> "CameraThresholds":
        """Trang Admin chi cho doi 1 so - suc chua toi da (alert_threshold
        trong bang SystemConfig). Nguong Vang suy ra theo dung ty le BRD
        15/20 = 0.75. Vi du: alert=20 -> warning=15; alert=30 -> warning=22."""
        alert = max(1, int(alert))
        warning = min(alert, max(1, round(alert * 0.75)))
        return cls(warning=warning, alert=alert)


class AlertLevelTracker:
    """Xac dinh muc canh bao co DIEU KIEN THOI GIAN + quyet dinh khi nao gui
    tin nhan (FR-04, FR-06, BRULE-02, BRULE-04).

    Cach dung (moi vong lap camera):
        level = tracker.update(count, now)      # "OK"/"WARNING"/"ALERT"/"CRITICAL"
        kind = tracker.pop_notification(now)    # None / "WARNING" / "CRITICAL"

    Quy tac:
      - Vao Do khi count > alert lien tuc red_hold_sec giay.
      - Da Do thi GIU Do (ke ca khi giam xuong 16-20) cho toi khi
        count <= warning lien tuc clear_hold_sec giay -> ve muc tuc thoi.
      - Tin nhan Vang: gui khi chuyen tu Binh thuong len Vang.
      - Tin nhan Do: gui ngay khi vao Do; neu van Do thi nhac lai toi da
        1 lan moi ``repeat_sec`` (mac dinh 180 giay = 3 phut).
      - Moi loai tin nhan khong gui lap qua 1 lan trong ``repeat_sec``.
    """

    def __init__(self, thresholds: CameraThresholds = None, repeat_sec: float = 180.0):
        self.thresholds = thresholds or CameraThresholds()
        self.repeat_sec = repeat_sec
        self.red = False
        self.level = "OK"
        self._over_since = None
        self._clear_since = None
        self._pending = None
        self._last_sent = {"WARNING": None, "CRITICAL": None}

    def set_thresholds(self, thresholds: CameraThresholds):
        """Admin doi nguong -> ap dung o chu ky dem ke tiep, giu nguyen trang thai."""
        self.thresholds = thresholds

    def update(self, count: int, now: float) -> str:
        th = self.thresholds
        prev = self.level

        if count > th.alert:
            if self._over_since is None:
                self._over_since = now
        else:
            self._over_since = None

        if self.red:
            if count <= th.warning:
                if self._clear_since is None:
                    self._clear_since = now
                if now - self._clear_since >= th.clear_hold_sec:
                    self.red = False
                    self._clear_since = None
            else:
                self._clear_since = None
        elif self._over_since is not None and now - self._over_since >= th.red_hold_sec:
            self.red = True
            self._clear_since = None
            self._last_sent["CRITICAL"] = None   # su co MOI -> gui ngay
            self._pending = "CRITICAL"

        self.level = "CRITICAL" if self.red else th.status_of(count)

        if self.level == "CRITICAL":
            last = self._last_sent["CRITICAL"]
            if last is not None and now - last >= self.repeat_sec:
                self._pending = "CRITICAL"       # nhac lai sau 3 phut
        elif prev == "OK" and self.level in ("WARNING", "ALERT"):
            last = self._last_sent["WARNING"]
            if last is None or now - last >= self.repeat_sec:
                self._pending = "WARNING"
        return self.level

    def pop_notification(self, now: float):
        """Tra ve loai tin nhan can gui ngay (va danh dau da gui), hoac None."""
        kind, self._pending = self._pending, None
        if kind is not None:
            self._last_sent[kind] = now
        return kind
