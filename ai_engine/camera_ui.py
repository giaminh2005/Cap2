"""
camera_ui.py
--------------
Ve len khung hinh camera chan cau (camera_bridge.py): khung nguoi, chu tieng Viet co dau
(TextLayer, ve bang Pillow theo tung o chu nho), o thong tin canh khung nguoi (panel_lines).
"""

import cv2


def draw_person_box(frame, box, tid, color):
    x, y, w, h = box
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
    cv2.putText(frame, f"ID {tid}", (x, max(0, y - 8)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)


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
        # Chi chuyen sang Pillow TUNG O CHU nho (khong phai ca khung hinh) -> nhanh hon nhieu o 720p/1080p
        fh, fw = frame.shape[:2]
        for text, (x, y), size, color, bg, bold, pad, anchor in self.items:
            f = _font(size, bold)
            l, t, r, b = f.getbbox(text)
            w, h = r - l, b - t
            if anchor == "mt":
                x -= w // 2
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1, y1 = min(fw, x + w + pad + 1), min(fh, y + h + pad + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            patch = _Image.fromarray(cv2.cvtColor(frame[y0:y1, x0:x1], cv2.COLOR_BGR2RGB))
            draw = _ImageDraw.Draw(patch, "RGBA")
            if bg is not None:
                rgba = (bg[2], bg[1], bg[0], 215) if len(bg) == 3 else (bg[2], bg[1], bg[0], bg[3])
                draw.rounded_rectangle((x - pad - x0, y - pad - y0, x + w + pad - x0, y + h + pad - y0),
                                       radius=6, fill=rgba)
            draw.text((x - l - x0, y - t - y0), text, font=f, fill=(color[2], color[1], color[0]))
            frame[y0:y1, x0:x1] = cv2.cvtColor(_np.asarray(patch), cv2.COLOR_RGB2BGR)
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
