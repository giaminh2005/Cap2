import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple

# Khôi phục chính xác các khoảng tuổi bạn yêu cầu
_AGE_BUCKETS = [
    (0, 5, "0-5"), (6, 12, "6-12"), (13, 17, "13-17"), (18, 24, "18-24"),
    (25, 34, "25-34"), (35, 44, "35-44"), (45, 54, "45-54"),
    (55, 64, "55-64"), (65, 69, "65-69"),
]

def age_to_range(age: Optional[int]) -> str:
    if age is None or age < 0: return "Khong ro"
    if age >= 70: return "70+"
    for lo, hi, label in _AGE_BUCKETS:
        if lo <= age <= hi: return label
    return "Khong ro"

def estimate_age_gender(image_bgr, detector_backend: str = "mtcnn", include_race: bool = True) -> List[Dict]:
    try:
        from deepface import DeepFace
    except ImportError:
        print("Chua cai deepface. Chay: pip install deepface tf-keras")
        return []

    if image_bgr is None or image_bgr.size == 0:
        return []

    actions = ["age", "gender", "race"] if include_race else ["age", "gender"]
    
    try:
        results = DeepFace.analyze(
            img_path=image_bgr,
            actions=actions,
            enforce_detection=True, 
            detector_backend="mtcnn",
            align=True,
            silent=True,
        )
    except Exception:
        return []

    if isinstance(results, dict):
        results = [results]

    out = []
    for r in results:
        gender_data = r.get("gender")
        if isinstance(gender_data, dict):
            woman_prob = float(gender_data.get("Woman", gender_data.get("Female", 0.0)))
            man_prob = float(gender_data.get("Man", gender_data.get("Male", 0.0)))
        else:
            dominant = str(r.get("dominant_gender", gender_data)).strip().lower()
            woman_prob = 100.0 if dominant in ["woman", "female", "nữ", "nu", "f", "w"] else 0.0
            man_prob = 100.0 if dominant in ["man", "male", "nam", "m"] else 0.0

        if woman_prob >= 28.0 or woman_prob >= man_prob:
            dominant_gender = "Woman"
            confidence = max(woman_prob, 55.0)
        else:
            dominant_gender = "Man"
            confidence = max(man_prob, 55.0)

        age = int(r.get("age", -1))
        
        # --- LOGIC PHÂN LOẠI QUỐC TỊCH (Đã được bổ sung vào đây) ---
        race_probs = r.get("race", {})
        nationality = "Unknown"
        if include_race and race_probs:
            dominant_race = r.get("dominant_race", "")
            if dominant_race == "asian":
                asian_prob = float(race_probs.get("asian", 0.0))
                if asian_prob > 60.0:
                    nationality = "Trong Nuoc/Chau A"
                else:
                    nationality = "Quoc Te"
            else:
                nationality = "Quoc Te"

        out.append({
            "age": age,
            "age_range": age_to_range(age),
            "gender": dominant_gender,
            "gender_confidence": round(float(confidence), 1),
            "region": r.get("region", {}),
            "race_probs": race_probs if include_race else None,
            "nationality": nationality # <-- TRƯỜNG DỮ LIỆU ĐÃ ĐƯỢC THÊM
        })
    return out

def estimate_demographics_from_person_box(
    frame, box: Tuple[int, int, int, int], include_race: bool = True
) -> Dict:
    x, y, w, h = box
    fh, fw = frame.shape[:2]
    empty = {"age": None, "age_range": "Khong ro", "gender": None,
             "gender_confidence": 0.0, "race_probs": None, "nationality": "Unknown"}
    if w <= 0 or h <= 0:
        return empty

    pad_x = int(w * 0.10)
    pad_y = int(h * 0.10)
    x0 = max(0, x - pad_x)
    x1 = min(fw, x + w + pad_x)
    y0 = max(0, y - pad_y)
    y1 = min(fh, y + int(h * 0.55) + pad_y)

    roi = frame[y0:y1, x0:x1]
    if roi.size == 0:
        return empty

    faces = estimate_age_gender(roi, include_race=include_race)
    if not faces:
        return empty

    box_cx_roi = (x + w / 2.0) - x0
    box_cy_roi = (y + h / 2.0) - y0

    def _dist_to_box_center(f):
        r = f["region"]
        fcx = r.get("x", 0) + r.get("w", 0) / 2.0
        fcy = r.get("y", 0) + r.get("h", 0) / 2.0
        return ((fcx - box_cx_roi) ** 2 + (fcy - box_cy_roi) ** 2) ** 0.5

    faces.sort(key=_dist_to_box_center)
    best = faces[0]
    return {
        "age": best["age"],
        "age_range": best["age_range"],
        "gender": best["gender"],
        "gender_confidence": best["gender_confidence"],
        "race_probs": best.get("race_probs"),
        "nationality": best.get("nationality", "Unknown") # <-- TRƯỜNG DỮ LIỆU ĐÃ ĐƯỢC THÊM
    }