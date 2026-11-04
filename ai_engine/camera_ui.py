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
