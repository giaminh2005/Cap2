"""
webcam_demo.py
----------------
Chay demo TRUC TIEP bang webcam cua may tinh (hoac mot file video co san)
de minh hoa truc quan cho phan thuyet trinh: camera "nhin thay" nguoi va
dem so luong + canh bao ngay theo thoi gian thuc, ngay tren man hinh.

Cach chay:
  python3 webcam_demo.py            -> dung webcam mac dinh cua may (index 0)
  python3 webcam_demo.py video.mp4  -> dung 1 file video co san thay vi webcam
  python3 webcam_demo.py 1          -> dung webcam thu 2 neu may co nhieu camera

Nhan phim 'q' trong cua so video hien ra de thoat.

Luu y ve do chinh xac: bo dem dung thuat toan HOG+SVM (xem crowd_counter.py),
hoat dong tot nhat khi thay ro TOAN THAN nguoi dung/di chuyen, du sang, khong
qua gan camera. Neu chi dua mat vao camera (giong webcam hop thoai video call)
so dem co the la 0 - dieu nay LA BINH THUONG, khong phai loi.
"""

# --- [To chuc lai thu muc - Sprint 3] file nay da duoc chuyen khoi src/.
# Dong duoi giup import cac module trong ai_engine/ (crowd_counter,
# camera_ui, ...) va tools/ ma KHONG can sua lai tung dong import cu.
import os as _os, sys as _sys
_ROOT = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..")
for _sub in ("ai_engine", "tools"):
    _p = _os.path.abspath(_os.path.join(_ROOT, _sub))
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
# --- het phan them moi ---

import sys
import cv2

from crowd_counter import CrowdCounter


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else 0
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Khong mo duoc nguon video/camera: {source}")
        print("- Neu dung webcam: vao System Settings > Privacy & Security > Camera,")
        print("  cap quyen dung Camera cho Terminal (hoac Visual Studio Code), roi chay lai lenh nay.")
        sys.exit(1)

    counter = CrowdCounter()
    frame_idx = 0
    last_result = (0, "OK", [], [])

    print("Dang chay... nhan 'q' trong cua so video de thoat.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Khong doc duoc frame (het video hoac mat ket noi camera).")
            break

        # HOG kha cham, chi chay detect that moi 3 frame de do giat/lag,
        # cac frame con lai dung lai ket qua gan nhat cho muot hon.
        if frame_idx % 3 == 0:
            count, status, boxes, weights = counter.count_and_status(frame)
            last_result = (count, status, boxes, weights)
        else:
            count, status, boxes, weights = last_result

        annotated = counter.annotate(frame, boxes, count, status)
        cv2.imshow("SmartCau AI - Demo dem nguoi truc tiep (nhan 'q' de thoat)", annotated)

        frame_idx += 1
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
