import sys
import time
import cv2

from crowd_counter import CrowdCounter
from camera_ui import draw_info_panel as _shared_draw_info_panel

ANALYSIS_INTERVAL_SEC = 1.0
MAX_PEOPLE_LABEL = 8

try:
    from age_gender_estimator import estimate_demographics_from_person_box
    DEEPFACE_OK = True
except ImportError:
    DEEPFACE_OK = False

def draw_info_panel(frame, person_box, lines, color=(255, 0, 255)):
    return _shared_draw_info_panel(frame, person_box, lines, color=color)

def run_full_analysis(counter, frame):
    count, status, boxes, weights = counter.count_and_status(frame)
    faces_results = []
    
    if boxes and DEEPFACE_OK:
        for box in boxes:
            res = estimate_demographics_from_person_box(frame, box)
            faces_results.append(res)
    else:
        faces_results = [{} for _ in boxes] if boxes else []
        
    return count, status, boxes, faces_results

def main():
    source = sys.argv[1] if len(sys.argv) > 1 else 0
    if isinstance(source, str) and source.isdigit():
        source = int(source)

    if not DEEPFACE_OK:
        print("[Canh bao] Chua cai duoc deepface -> se CHI dem nguoi, khong hien tuoi/gioi tinh.")
        print("Cai bang: pip install deepface tf-keras\n")

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f"Khong mo duoc nguon video/camera: {source}")
        sys.exit(1)

    counter = CrowdCounter()
    last_analysis_time = 0.0
    count, status, boxes, faces = 0, "OK", [], []

    print("Dang chay... nhan 'q' de thoat.")
    while True:
        ok, frame = cap.read()
        if not ok:
            print("Khong doc duoc frame.")
            break

        now = time.time()
        if now - last_analysis_time >= ANALYSIS_INTERVAL_SEC:
            count, status, boxes, faces = run_full_analysis(counter, frame)
            last_analysis_time = now

        out = counter.annotate(frame, boxes, count, status)

        shown = 0
        for idx, (box, face_info) in enumerate(zip(boxes, faces)):
            if shown >= MAX_PEOPLE_LABEL:
                break
                
            if not face_info or face_info.get("gender") is None:
                continue
                
            gender_display = "Nữ" if face_info["gender"] == "Woman" else "Nam"
            lines = [f"Nguoi #{idx + 1}", f"{gender_display}", f"Khoang {face_info.get('age_range', 'Khong ro')}"]
            draw_info_panel(out, box, lines)
            shown += 1

        cv2.imshow("SmartCau AI - Dem nguoi + Nhan khau hoc (nhan 'q' de thoat)", out)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
