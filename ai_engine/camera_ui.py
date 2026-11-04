"""
camera_ui.py
--------------
Cac ham VE GIAO DIEN (overlay) tren khung hinh camera - dung chung cho
webcam_tracking_demo.py, camera_in.py, camera_out.py de khong lap code
va de sua 1 cho khi can chinh giao dien.
"""

import cv2


def draw_person_box(frame, box, tid, color):
    x, y, w, h = box
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    cv2.putText(frame, f"ID {tid}", (x, max(0, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)


def draw_info_panel(frame, person_box, lines, color=(200, 0, 150)):
    """Ve 1 o (panel) thong tin nam BEN CANH khung nguoi (uu tien ben phai,
    tu dong doi sang trai neu cham vien anh)."""
    x, y, w, h = person_box
    line_h = 20
    panel_w = 170
    panel_h = line_h * len(lines) + 15

    fh_img, fw_img = frame.shape[:2]
    panel_x = x + w + 10
    panel_y = max(0, min(y, fh_img - panel_h))
    if panel_x + panel_w > fw_img:
        panel_x = max(0, x - panel_w - 10)

    overlay = frame.copy()
    cv2.rectangle(overlay, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), color, -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, dst=frame)
    cv2.rectangle(frame, (panel_x, panel_y), (panel_x + panel_w, panel_y + panel_h), (255, 255, 255), 1)

    for i, line in enumerate(lines):
        font_scale = 0.55 if i == 0 else 0.5
        thickness = 2 if i == 0 else 1
        cv2.putText(frame, line, (panel_x + 8, panel_y + 20 + i * line_h),
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

    anchor_x = x + w if panel_x > x else x
    cv2.line(frame, (anchor_x, y + int(h / 4)), (panel_x, panel_y + 15), (255, 255, 255), 1)


def draw_status_bar(frame, text):
    bar_h = 40
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (frame.shape[1], bar_h), (25, 25, 25), -1)
    cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, dst=frame)
    cv2.putText(frame, text, (10, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2, cv2.LINE_AA)


def draw_capacity_banner(frame, message):
    """Banner do lon giua man hinh khi VUOT QUA suc chua toi da - de nhan
    ra ngay tu xa khi trinh bay/demo."""
    fh, fw = frame.shape[:2]
    banner_h = 70
    y0 = fh // 2 - banner_h // 2
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, y0), (fw, y0 + banner_h), (0, 0, 255), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, dst=frame)
    cv2.rectangle(frame, (0, y0), (fw, y0 + banner_h), (255, 255, 255), 2)
    text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)[0]
    tx = max(10, (fw - text_size[0]) // 2)
    cv2.putText(frame, message, (tx, y0 + banner_h // 2 + 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)


def draw_gate_banner(frame, message, color=(0, 140, 255)):
    """NANG CAP Phase 4 - banner "CONG DANG DONG" (vd "CHO - CAU DANG
    DAY"), nam o NUA TREN man hinh (khac vi tri voi draw_capacity_banner
    o GIUA, de 2 banner khong de len nhau neu xay ra cung luc - vd vua
    cham nguong "cho" vua cham nguong "qua tai")."""
    fh, fw = frame.shape[:2]
    banner_h = 56
    y0 = 44  # ngay duoi thanh status_bar (cao 40px)
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, y0), (fw, y0 + banner_h), color, -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, dst=frame)
    cv2.rectangle(frame, (0, y0), (fw, y0 + banner_h), (255, 255, 255), 2)
    text_size = cv2.getTextSize(message, cv2.FONT_HERSHEY_SIMPLEX, 0.75, 2)[0]
    tx = max(10, (fw - text_size[0]) // 2)
    cv2.putText(frame, message, (tx, y0 + banner_h // 2 + 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2, cv2.LINE_AA)


def draw_countdown(frame, remaining_slots: int):
    """NANG CAP Phase 4 - hien "Con X cho trong" o goc tren-phai man hinh,
    doi mau theo con so con lai (xanh -> vang -> do) de nhan ra tu xa."""
    fh, fw = frame.shape[:2]
    text = f"Con {max(0, remaining_slots)} cho trong" if remaining_slots > 0 else "HET CHO"
    color = (60, 180, 75) if remaining_slots > 5 else ((0, 165, 255) if remaining_slots > 0 else (0, 0, 255))
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
    pad = 8
    x1 = fw - text_size[0] - pad * 2 - 10
    y0 = 44
    cv2.rectangle(frame, (x1, y0), (fw - 10, y0 + 32), (25, 25, 25), -1)
    cv2.rectangle(frame, (x1, y0), (fw - 10, y0 + 32), color, 2)
    cv2.putText(frame, text, (x1 + pad, y0 + 22), cv2.FONT_HERSHEY_SIMPLEX,
                0.6, color, 2, cv2.LINE_AA)


# ======================================================================
# CHU TIENG VIET CO DAU tren khung hinh camera
# ----------------------------------------------------------------------
# cv2.putText chi ve duoc chu ASCII (mat dau). Cac ham duoi day dung Pillow
# + 1 font he thong co ho tro tieng Viet (Arial/Segoe UI tren Windows, Arial
# tren macOS, DejaVu tren Linux). Gom het chu cua 1 frame roi ve 1 LAN de
# khong lam cham camera. Khong tim thay font -> tu lui ve cv2.putText.
# ======================================================================
import os as _os

import numpy as _np

try:
    from PIL import Image as _Image, ImageDraw as _ImageDraw, ImageFont as _ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

_FONT_CANDIDATES = [
    _os.environ.get("SMARTCAU_FONT", ""),
    r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\tahoma.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]
_FONT_BOLD_CANDIDATES = [
    r"C:\Windows\Fonts\segoeuib.ttf", r"C:\Windows\Fonts\arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
]
_font_cache = {}


def _font_path(bold=False):
    for p in (_FONT_BOLD_CANDIDATES if bold else []) + _FONT_CANDIDATES:
        if p and _os.path.exists(p):
            return p
    return None


def _font(size, bold=False):
    key = (size, bold)
    if key not in _font_cache:
        path = _font_path(bold)
        _font_cache[key] = _ImageFont.truetype(path, size) if (path and _HAS_PIL) else None
    return _font_cache[key]


def vietnamese_text_supported() -> bool:
    return _HAS_PIL and _font(16) is not None


class TextLayer:
    """Gom chu + o nen cua 1 frame, ve 1 lan bang render(frame).

        layer = TextLayer()
        layer.text("Đang trên cầu: 12", (10, 10), size=20, color=(255,255,255), bg=(30,30,30))
        layer.render(frame)
    Mau theo BGR (giong OpenCV)."""

    def __init__(self):
        self.items = []

    def text(self, text, org, size=18, color=(255, 255, 255), bg=None, bold=False, pad=6, anchor="lt"):
        self.items.append((str(text), org, size, color, bg, bold, pad, anchor))

    def measure(self, text, size=18, bold=False):
        f = _font(size, bold) if _HAS_PIL else None
        if f is None:
            (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, size / 32, 1)
            return w, h
        l, t, r, b = f.getbbox(text)
        return r - l, b - t

    def render(self, frame):
        if not self.items:
            return
        if not vietnamese_text_supported():
            for text, (x, y), size, color, bg, bold, pad, anchor in self.items:
                ascii_text = text.encode("ascii", "ignore").decode()
                w, h = self.measure(ascii_text, size, bold)
                if anchor == "mt":
                    x -= w // 2
                if bg is not None:
                    cv2.rectangle(frame, (x - pad, y - pad), (x + w + pad, y + h + pad), bg, -1)
                cv2.putText(frame, ascii_text, (x, y + h), cv2.FONT_HERSHEY_SIMPLEX, size / 32, color,
                            2 if bold else 1, cv2.LINE_AA)
            self.items = []
            return
        img = _Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = _ImageDraw.Draw(img, "RGBA")
        for text, (x, y), size, color, bg, bold, pad, anchor in self.items:
            f = _font(size, bold)
            l, t, r, b = draw.textbbox((0, 0), text, font=f)
            w, h = r - l, b - t
            if anchor == "mt":
                x -= w // 2
            if bg is not None:
                rgba = (bg[2], bg[1], bg[0], 215) if len(bg) == 3 else (bg[2], bg[1], bg[0], bg[3])
                draw.rounded_rectangle((x - pad, y - pad, x + w + pad, y + h + pad), radius=6, fill=rgba)
            draw.text((x - l, y - t), text, font=f, fill=(color[2], color[1], color[0]))
        frame[:] = cv2.cvtColor(_np.asarray(img), cv2.COLOR_RGB2BGR)
        self.items = []


def panel_lines(layer: TextLayer, frame, box, lines, accent=(0, 140, 255)):
    """O thong tin canh khung nguoi (uu tien ben phai), chu co dau."""
    x, y, w, h = box
    fh, fw = frame.shape[:2]
    size, gap = 17, 6
    widths = [layer.measure(t, size, i == 0)[0] for i, t in enumerate(lines)]
    pw = max(widths) + 14
    line_h = layer.measure("Ẩg", size)[1] + gap
    ph = line_h * len(lines) + 6
    px = x + w + 8
    if px + pw > fw:
        px = max(0, x - pw - 8)
    py = max(0, min(y, fh - ph))
    for i, t in enumerate(lines):
        layer.text(t, (px + 7, py + 4 + i * line_h), size=size, bold=(i == 0),
                   color=(255, 255, 255), bg=accent if i == 0 else (40, 40, 40), pad=4)
