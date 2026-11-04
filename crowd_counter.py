"""
crowd_counter.py
------------------
Module "Giam sat & Dem nguoi" (Crowd Counting & Alert) cho he thong
SmartCau AI - Chua Cau, Hoi An.

Dung OpenCV (HOG + Linear SVM pedestrian detector co san, khong can
tai model tu Internet) de phat hien nguoi trong anh/khung hinh camera,
dem so luong va so sanh voi nguong an toan cua Chua Cau (20-25 nguoi).

Ghi chu quan trong (that voi hoc phan):
- Day la mo-dun detection "classical CV" (HOG+SVM), chay duoc offline,
  khong can GPU/Internet -> phu hop lam proof-of-concept trong moi
  truong khong co mang.
- Trong ban trien khai thuc te / huong phat trien tiep (Cap3, NCKH),
  nen nang cap len mot mo hinh deep-learning hien dai hon (vi du
  YOLOv8 - Ultralytics) de tang do chinh xac khi dam dong, bi che khuat.
- Detector nay hoat dong tot nhat tren ANH/VIDEO THAT (co nguoi that,
  anh sang, do phan giai hop ly). Tren anh tong hop (synthetic) do
  chuong trinh tu ve, so nguoi phat hien co the la 0 - dieu nay LA
  BINH THUONG va duoc kiem tra rieng trong test_crowd_counter.py.
"""

from dataclasses import dataclass
from typing import List, Tuple
import cv2
import numpy as np

try:
    from ultralytics import YOLO
    _YOLO_AVAILABLE = True
except ImportError:
    _YOLO_AVAILABLE = False


@dataclass
class CameraThresholds:
    """Nguong canh bao. SUA LOI (nang cap Phase 1, bug #1/#2): ban truoc
    de warning=7/alert=9/critical=10 (chi la so vi du luc dau), nhung BRD
    va dashboard.html da chot suc chua Chua Cau la 20-25 nguoi - 2 noi
    nay bi LECH nhau. Doi lai dung theo BRD: 18/20/25."""
    warning: int = 18   # gan nguong - can chu y, hien tren man hinh
    alert: int = 20     # DAT NGUONG CHO VAO: cong GATE hien "CHO - CAU DANG DAY"
    critical: int = 25  # VUOT SUC CHUA TOI DA that su -> canh bao khan + Telegram + buzzer

    def status_of(self, count: int) -> str:
        if count >= self.critical:
            return "CRITICAL"
        if count >= self.alert:
            return "ALERT"
        if count >= self.warning:
            return "WARNING"
        return "OK"

    @classmethod
    def from_alert_threshold(cls, alert: int) -> "CameraThresholds":
        """NANG CAP (Admin Web): trang Admin Web (muc "Cau hinh") chi cho
        admin doi DUY NHAT 1 so - "nguong canh bao" (alert_threshold, luu o
        bang SystemConfig/endpoint /config trong api_server.py) - vi doi
        rieng le ca 3 nguong warning/alert/critical tren 1 man hinh web se
        de nham/roi. Ham nay TU DONG suy ra warning/critical con lai theo
        DUNG TY LE cua bo 3 mac dinh (18/20/25), de doi 1 so alert van giu
        dung "hinh dang" 3 muc canh bao nhu BRD da chot.
        Vi du: alert=20 (mac dinh) -> warning=18, critical=25 (giong nhu cu).
                alert=30            -> warning=27, critical=38 (lam tron)."""
        alert = max(1, int(alert))
        warning = max(1, round(alert * 0.9))     # 18/20 = 0.9
        critical = max(alert + 1, round(alert * 1.25))  # 25/20 = 1.25
        return cls(warning=warning, alert=alert, critical=critical)


STATUS_COLOR_BGR = {
    "OK": (60, 180, 75),
    "WARNING": (0, 165, 255),
    "ALERT": (0, 0, 255),
    "CRITICAL": (0, 0, 200),
}

STATUS_LABEL_VI = {
    "OK": "Binh thuong",
    "WARNING": "Gan nguong - theo doi",
    "ALERT": "VUOT NGUONG - can canh bao",
    "CRITICAL": "QUA TAI NGHIEM TRONG - can can thiep ngay",
}


class CrowdCounter:
    """Bo dem nguoi. Ho tro 2 "backend":
      - "yolo": YOLOv8 (Ultralytics) - deep learning, chinh xac cao hon
                nhieu, tu dong chi nhan dien dung class "person", it bao
                nham vat the hon HAN so voi HOG. CAN cai `ultralytics`
                (pip install ultralytics) va Internet o LAN CHAY DAU TIEN
                de tai san san model (~6MB cho ban "nano" yolov8n.pt).
      - "hog" : HOG+SVM co san trong OpenCV, khong can cai them gi, khong
                can Internet, nhung de bao nham vat the hon.

    Mac dinh backend="auto": tu dong dung YOLO neu da cai duoc thu vien
    `ultralytics`, neu chua cai thi tu dong lui ve dung HOG (khong bi loi,
    chi kem chinh xac hon)."""

    def __init__(
        self,
        thresholds: CameraThresholds = None,
        backend: str = "auto",
        yolo_model: str = "yolov8n.pt",
        yolo_conf: float = 0.4,
    ):
        self.thresholds = thresholds or CameraThresholds()

        if backend == "auto":
            backend = "yolo" if _YOLO_AVAILABLE else "hog"
        self.backend = backend
        self.yolo_conf = yolo_conf

        if self.backend == "yolo":
            if not _YOLO_AVAILABLE:
                raise RuntimeError(
                    "backend='yolo' nhung chua cai duoc thu vien ultralytics.\n"
                    "Chay: pip install ultralytics"
                )
            print(f"[CrowdCounter] Dung YOLOv8 ({yolo_model}) de nhan dien nguoi "
                  f"(lan dau chay se tu tai model, can Internet)...")
            self.model = YOLO(yolo_model)
        elif self.backend == "hog":
            print("[CrowdCounter] Dung HOG+SVM (co san trong OpenCV) de nhan dien nguoi...")
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
        else:
            raise ValueError(f"backend khong hop le: {backend!r} (chi nhan 'auto', 'yolo' hoac 'hog')")

    def detect_people(self, image_bgr: np.ndarray, **kwargs) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Phat hien nguoi trong anh. Tra ve (danh sach box (x,y,w,h), danh
        sach do tin cay). Tu dong goi dung ham theo backend dang dung."""
        if self.backend == "yolo":
            return self._detect_yolo(image_bgr)
        return self._detect_hog(image_bgr, **kwargs)

    def _detect_yolo(self, image_bgr: np.ndarray) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """YOLO da tu lam NMS va phan loai class ben trong, nen chi can loc
        giu lai class "person" (id 0 trong bo COCO ma YOLOv8 pretrained dung)
        va bo cac ket qua co do tin cay thap hon yolo_conf. Nho vay hau nhu
        khong con bi bao nham thanh ghe/tu/cot nhu HOG nua."""
        results = self.model(image_bgr, verbose=False)[0]
        boxes_out, weights_out = [], []
        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            if cls_id != 0:  # 0 = "person" trong bo lop COCO
                continue
            if conf < self.yolo_conf:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            boxes_out.append((int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
            weights_out.append(conf)
        return boxes_out, weights_out

    def _detect_hog(
        self,
        image_bgr: np.ndarray,
        min_weight: float = 0.4,
        min_aspect: float = 1.1,
        max_aspect: float = 4.5,
        min_height_frac: float = 0.12,
        nms_threshold: float = 0.35,
    ) -> Tuple[List[Tuple[int, int, int, int]], List[float]]:
        """Phat hien NGUOI trong anh bang HOG+SVM, co loc bot vat khong phai nguoi.

        HOG+SVM (thuat toan classical, khong phai deep learning) hay bi
        "bao nham" tren cac vat co canh doc/hinh dang giong nguoi (tu,
        cot, khung cua...). De giam nham, ap dung 4 lop loc:
          1. min_weight     - bo cac ket qua co diem tin cay SVM thap
          2. min/max_aspect - nguoi dung/di thuong CAO HON RONG theo 1 ty
                               le nhat dinh (loai vat qua vuong hoac qua det)
          3. min_height_frac- bo cac khung qua nho so voi chieu cao anh
                               (thuong la nhieu/vat o xa, khong phai nguoi
                               dang can quan tam trong khung hinh)
          4. NMS (Non-Max Suppression) - gop cac khung bi trung/long nhau
                               thanh 1 khung duy nhat cho moi nguoi

        Cac tham so co the chinh lai (vd giam min_weight neu thay bo sot
        nguoi that; tang len neu van con bao nham vat the).
        """
        boxes, weights = self.hog.detectMultiScale(
            image_bgr, winStride=(8, 8), padding=(8, 8), scale=1.05
        )
        img_h = image_bgr.shape[0]

        candidates = []
        for (x, y, w, h), wt in zip(boxes, weights):
            wt = float(wt)
            if w <= 0 or h <= 0:
                continue
            if wt < min_weight:
                continue
            aspect = h / float(w)
            if not (min_aspect <= aspect <= max_aspect):
                continue
            if h < min_height_frac * img_h:
                continue
            candidates.append((int(x), int(y), int(w), int(h), wt))

        if not candidates:
            return [], []

        nms_boxes = [[c[0], c[1], c[2], c[3]] for c in candidates]
        nms_scores = [c[4] for c in candidates]
        indices = cv2.dnn.NMSBoxes(nms_boxes, nms_scores, score_threshold=min_weight, nms_threshold=nms_threshold)

        if indices is None or len(indices) == 0:
            return [], []
        indices = np.array(indices).flatten()

        final_boxes = [(candidates[i][0], candidates[i][1], candidates[i][2], candidates[i][3]) for i in indices]
        final_weights = [candidates[i][4] for i in indices]
        return final_boxes, final_weights

    def count_and_status(self, image_bgr: np.ndarray):
        boxes, weights = self.detect_people(image_bgr)
        count = len(boxes)
        status = self.thresholds.status_of(count)
        return count, status, boxes, weights

    def annotate(self, image_bgr: np.ndarray, boxes, count: int, status: str) -> np.ndarray:
        out = image_bgr.copy()
        color = STATUS_COLOR_BGR[status]
        for (x, y, w, h) in boxes:
            cv2.rectangle(out, (x, y), (x + w, y + h), color, 2)

        # Thanh trang thai tren cung anh
        bar_h = 46
        overlay = out.copy()
        cv2.rectangle(overlay, (0, 0), (out.shape[1], bar_h), (25, 25, 25), -1)
        out = cv2.addWeighted(overlay, 0.75, out, 0.25, 0)

        text = f"So nguoi tren cau: {count}  |  Nguong: {self.thresholds.alert}-{self.thresholds.critical}  |  {STATUS_LABEL_VI[status]}"
        cv2.putText(out, text, (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)
        return out


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    backend = sys.argv[2] if len(sys.argv) > 2 else "auto"  # "auto" | "yolo" | "hog"
    if not path:
        print("Dung: python3 crowd_counter.py <duong_dan_anh> [yolo|hog]")
        sys.exit(1)

    counter = CrowdCounter(backend=backend)

    img = cv2.imread(path)
    if img is None:
        print(f"Khong doc duoc anh: {path}")
        sys.exit(1)

    count, status, boxes, weights = counter.count_and_status(img)
    print(f"Phat hien {count} nguoi -> trang thai: {status} ({STATUS_LABEL_VI[status]})")

    annotated = counter.annotate(img, boxes, count, status)
    out_path = path.rsplit(".", 1)[0] + "_annotated.jpg"
    cv2.imwrite(out_path, annotated)
    print(f"Da luu anh ket qua: {out_path}")
