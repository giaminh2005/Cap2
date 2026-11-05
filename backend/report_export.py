"""
frontend/report_export.py  —  MODULE M4 · F5.3 Xuat bao cao PDF / Excel (FR-11, AC-07.1)
Phu trach: HOAN.
PDF dung fpdf2 + 1 font he thong co tieng Viet (Arial tren Windows/macOS,
DejaVu tren Linux). Excel dung openpyxl qua pandas.
"""

import io
import os
from datetime import datetime

import pandas as pd

FONT_REGULAR = [os.environ.get("SMARTCAU_FONT", ""), r"C:\Windows\Fonts\arial.ttf", r"C:\Windows\Fonts\segoeui.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial Unicode.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf"]
FONT_BOLD = [r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\segoeuib.ttf",
             "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
             "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"]
PERIOD_VI = {"day": "Ngày", "week": "Tuần", "month": "Tháng"}


def _first(paths):
    return next((p for p in paths if p and os.path.exists(p)), None)


def report_tables(r: dict) -> dict:
    """Cac bang cua bao cao (dung chung cho Excel, PDF va trang web)."""
    dem = r["demographics"]
    ident = dem["identified"] or 1
    overview = pd.DataFrame([
        ("Kỳ báo cáo", f"{PERIOD_VI[r['period']]}: {r['date_from']} → {r['date_to']}"),
        ("Tổng lượt vào cầu", r["total_entries"]),
        ("Tổng lượt ra", r["total_exits"]),
        ("Lượt qua mặt tiền (không lên cầu)", r["facade_passes"]),
        ("Giờ có nhiều lượt vào nhất", f"{r['peak_hour']}h ({r['peak_hour_entries']} lượt)" if r["peak_hour"] is not None else "–"),
        ("Số người trên cầu cao nhất", r["peak_count"]),
        ("Cảnh báo Vàng", r["alerts"]["WARNING"]),
        ("Cảnh báo Đỏ", r["alerts"]["CRITICAL_ALERT"]),
        ("Sự cố quá tải", r["incidents"]),
        ("Sự cố được xác nhận", r["incidents_acked"]),
        ("Thời gian phản hồi trung bình (giây)", r["avg_handle_seconds"] if r["avg_handle_seconds"] is not None else "–"),
        ("Đoàn khách lớn", r["alerts"]["GROUP_DETECTED"]),
        ("Mất tín hiệu camera", r["alerts"]["CAMERA_LOST"]),
    ], columns=["Chỉ tiêu", "Giá trị"])
    k = r.get("kpis") or {}

    def pct(v):
        return "–" if v is None else f"{v:.1f}%"

    kpi_tbl = pd.DataFrame([
        ("O1", "Số phút có hơn sức chứa trên cầu", f"{k.get('o1_minutes_over', 0)} phút ({k.get('o1_minutes_per_day', 0)} phút/ngày)", "giảm ≥ 70%"),
        ("O4", "Sự cố được xử lý trong 3 phút", pct(k.get("o4_handled_within_3min_pct")), "≥ 90%"),
        ("O5", "Tỷ lệ cảnh báo sai", pct(k.get("o5_false_alarm_pct")), "≤ 5%"),
        ("O8", "Tỷ lệ chênh lệch lượt vào / vé", pct(k.get("o8_gap_rate_pct")), "xu hướng giảm"),
    ], columns=["Mã", "Chỉ số", "Kết quả", "Mục tiêu"])
    by_day = pd.DataFrame(r["by_day"]).rename(columns={"date": "Ngày", "entries": "Lượt vào"})
    slots = pd.DataFrame(r["time_slots"]).rename(columns={"slot": "Khung giờ", "entries": "Lượt vào"})
    by15 = pd.DataFrame(r["by_15min"]).rename(columns={"slot": "Khung 15 phút", "entries": "Lượt vào"})
    demo_rows = [("Nữ", dem["gender"]["Woman"]), ("Nam", dem["gender"]["Man"]),
                 ("Không xác định", dem["unknown"]),
                 ("Trong nước/châu Á (ước lượng)", dem["origin"]["Trong nuoc"]),
                 ("Quốc tế (ước lượng)", dem["origin"]["Nuoc ngoai"])]
    demo_rows += [(f"Tuổi {k}", v) for k, v in dem["age_range"].items() if v]
    demo = pd.DataFrame(demo_rows, columns=["Nhóm", "Số lượt"])
    demo["Tỷ lệ"] = [f"{v / ident * 100:.1f}%" if n != "Không xác định" else "không tính" for n, v in demo_rows]
    tables = {"Tổng quan": overview, "Chỉ số KPI": kpi_tbl, "Theo ngày": by_day, "Theo khung giờ": slots, "Cơ cấu khách": demo}
    if not by15.empty:
        tables["Theo 15 phút"] = by15
    return tables


def to_excel(r: dict) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, df in report_tables(r).items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
            ws = xw.sheets[name[:31]]
            for col in ws.columns:
                width = max(len(str(c.value or "")) for c in col) + 2
                ws.column_dimensions[col[0].column_letter].width = min(60, max(12, width))
    return buf.getvalue()


def to_pdf(r: dict) -> bytes:
    from fpdf import FPDF
    from fpdf.fonts import FontFace

    try:
        from .timeutil import local_now
        made_at = local_now()
    except ImportError:
        made_at = datetime.now()

    reg, bold = _first(FONT_REGULAR), _first(FONT_BOLD)
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(True, margin=14)
    if reg:
        pdf.add_font("vn", "", reg)
        pdf.add_font("vn", "B", bold or reg)
        family = "vn"
    else:  # khong co font tieng Viet -> bo dau de khong loi
        import unicodedata
        family = "helvetica"
        r = _strip_accents(r, unicodedata)
    pdf.add_page()
    pdf.set_draw_color(168, 129, 47)
    pdf.set_text_color(168, 129, 47)
    pdf.set_font(family, "B", 8)
    pdf.cell(0, 5, "TRUNG TÂM QUẢN LÝ BẢO TỒN DI SẢN VĂN HÓA HỘI AN · SMARTCAU AI" if reg else "SMARTCAU AI",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(31, 26, 23)
    pdf.set_font(family, "B", 17)
    pdf.cell(0, 10, "Báo cáo lượng khách Chùa Cầu" if reg else "Bao cao luong khach Chua Cau", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "", 9.5)
    pdf.set_text_color(119, 107, 95)
    d1, d2 = r["date_from"], r["date_to"]
    pdf.cell(0, 6, f"{PERIOD_VI[r['period']]} {d1[8:]}/{d1[5:7]}/{d1[:4]} – {d2[8:]}/{d2[5:7]}/{d2[:4]} · "
                   f"lập lúc {made_at:%H:%M %d/%m/%Y}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_line_width(0.4)
    y = pdf.get_y() + 2
    pdf.line(pdf.l_margin, y, pdf.l_margin + 18, y)
    pdf.set_draw_color(227, 217, 200)
    pdf.set_line_width(0.2)
    pdf.line(pdf.l_margin + 20, y, pdf.w - pdf.r_margin, y)
    pdf.ln(7)
    head = FontFace(family=family, emphasis="BOLD", color=(31, 26, 23), fill_color=(239, 231, 217))
    for name, df in report_tables(r).items():
        if df.empty:
            continue
        pdf.set_font(family, "B", 12)
        pdf.set_text_color(125, 35, 24)
        pdf.cell(0, 8, name, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(31, 26, 23)
        pdf.set_font(family, "", 9.5)
        pdf.set_draw_color(227, 217, 200)
        pdf.set_fill_color(255, 255, 255)
        widths = (0.6, 3, 1.8, 1.2) if name == "Chỉ số KPI" else tuple([3] + [1.4] * (len(df.columns) - 1))
        with pdf.table(col_widths=widths, text_align="LEFT",
                       line_height=6, first_row_as_headings=True, headings_style=head,
                       borders_layout="HORIZONTAL_LINES", padding=1.5) as table:
            table.row([str(c) for c in df.columns])
            for _, row in df.iterrows():
                table.row([str(v) for v in row.values])
        pdf.ln(4)
    pdf.set_font(family, "", 8)
    pdf.multi_cell(0, 4.5, "Ghi chú: “Trong nước/châu Á – Quốc tế” là ước lượng từ nhóm khu vực rộng của mô hình AI, "
                           "không phải quốc tịch. Hệ thống không lưu ảnh hay đặc trưng khuôn mặt.")
    return bytes(pdf.output())


def _strip_accents(obj, unicodedata):
    if isinstance(obj, str):
        return unicodedata.normalize("NFKD", obj.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode()
    if isinstance(obj, dict):
        return {k: _strip_accents(v, unicodedata) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_accents(v, unicodedata) for v in obj]
    return obj
