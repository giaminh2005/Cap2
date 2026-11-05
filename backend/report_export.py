"""
backend/report_export.py  —  MODULE M4 · F5.3 Xuat bao cao PDF / Excel (FR-11, AC-07.1)
==========================================================================================
Phu trach: HOAN.

PDF theo the thuc van ban hanh chinh (Nghi dinh 30/2020/ND-CP): Quoc hieu, tieu ngu,
ten co quan, so bao cao, dia danh - ngay thang, tieu de, cac muc I, II, III..., noi nhan,
chu ky. Font Times New Roman 13 (Windows / macOS), Liberation Serif / DejaVu Serif (Linux).
Moi trang co logo SmartCau in chim (mo) o giua va so trang o chan trang.
Bieu do ve bang matplotlib, chen vao PDF dang PNG.

    to_pdf(r, options)    r = ket qua /reports/summary; options = tuy chinh (xem PDF_DEFAULTS)
    to_excel(r)           cac bang cua bao cao, moi bang 1 trang tinh
    report_tables(r)      bang dung chung cho web / Excel / PDF

Ten co quan doi bang bien moi truong SMARTCAU_ORG_PARENT, SMARTCAU_ORG_NAME,
SMARTCAU_ORG_PLACE hoac truyen trong options.
"""

import io
import os
from datetime import datetime

import pandas as pd

# ------------------------------------------------------------------ font
_W = r"C:\Windows\Fonts"
_MAC = "/System/Library/Fonts/Supplemental"
FONT_SETS = [   # (thuong, dam, nghieng, dam nghieng) - uu tien Times New Roman cho van ban hanh chinh
    (os.environ.get("SMARTCAU_FONT", ""), os.environ.get("SMARTCAU_FONT_BOLD", ""), "", ""),
    (rf"{_W}\times.ttf", rf"{_W}\timesbd.ttf", rf"{_W}\timesi.ttf", rf"{_W}\timesbi.ttf"),
    (f"{_MAC}/Times New Roman.ttf", f"{_MAC}/Times New Roman Bold.ttf", f"{_MAC}/Times New Roman Italic.ttf",
     f"{_MAC}/Times New Roman Bold Italic.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSerif-BoldItalic.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-BoldItalic.ttf"),
    (rf"{_W}\arial.ttf", rf"{_W}\arialbd.ttf", rf"{_W}\ariali.ttf", rf"{_W}\arialbi.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "", ""),
]
# giu ten cu cho code khac (vd kiem tra font)
FONT_REGULAR = [s[0] for s in FONT_SETS]
FONT_BOLD = [s[1] for s in FONT_SETS]

PERIOD_VI = {"day": "Ngày", "week": "Tuần", "month": "Tháng", "year": "Năm", "custom": "Khoảng thời gian"}
WEEKDAY_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"]

ORG_PARENT = os.environ.get("SMARTCAU_ORG_PARENT", "TRUNG TÂM QUẢN LÝ BẢO TỒN\nDI SẢN VĂN HÓA HỘI AN")
ORG_NAME = os.environ.get("SMARTCAU_ORG_NAME", "BỘ PHẬN VẬN HÀNH\nHỆ THỐNG SMARTCAU AI")
ORG_PLACE = os.environ.get("SMARTCAU_ORG_PLACE", "Hội An")

SECTIONS = {   # ma -> ten muc trong bao cao (nguoi dung chon muc nao dua vao PDF)
    "overview": "Tình hình chung",
    "trend": "Diễn biến lượng khách",
    "demographics": "Cơ cấu khách tham quan",
    "safety": "Công tác đảm bảo an toàn",
    "tickets": "Đối chiếu số lượt vào với số vé",
    "assessment": "Đánh giá và kiến nghị",
}
PDF_DEFAULTS = {
    "sections": list(SECTIONS),
    "charts": True,
    "report_no": "",              # vd "12" -> "Số: 12/BC-SCAI"
    "prepared_by": "",            # nguoi lap
    "prepared_title": "NGƯỜI LẬP BÁO CÁO",
    "approver": "",               # thu truong don vi
    "approver_title": "THỦ TRƯỞNG ĐƠN VỊ",
    "recipients": "- Ban Giám đốc Trung tâm;\n- Phòng Quản lý di tích;\n- Lưu: VT.",
    "notes": "",                  # kien nghi, de xuat nguoi lap tu viet them
    "org_parent": None, "org_name": None, "place": None,
}

INK, MUTED, RULE = (20, 20, 20), (90, 90, 90), (150, 150, 150)
BRAND, GOLD = (125, 35, 24), (168, 129, 47)
CHART = {"oxblood": "#7D2318", "gold": "#B8913F", "teal": "#2F6F73", "stone": "#9A8F84", "ink": "#2A211B",
         "grid": "#E3DACB", "ok": "#4F7F5A", "warn": "#C98A1B"}


def _first(paths):
    return next((p for p in paths if p and os.path.exists(p)), None)


def _fmt_d(s: str) -> str:
    return f"{s[8:]}/{s[5:7]}/{s[:4]}"


def _n(v) -> str:
    return "–" if v is None else f"{int(v):,}".replace(",", ".")


def _pct(v, digits=1) -> str:
    return "–" if v is None else f"{v:.{digits}f}%".replace(".", ",")


def _until_today(r: dict, made_at: datetime = None) -> dict:
    """Bo cac ngay / thang chua toi (ky thang / nam dang dien ra) khoi bang va bieu do."""
    today = (made_at or datetime.now()).strftime("%Y-%m-%d")
    r = dict(r)
    r["by_day"] = [d for d in r["by_day"] if d["date"] <= today] or r["by_day"][:1]
    r["by_month"] = [m for m in r.get("by_month", []) if m["month"] <= today[:7]] or r.get("by_month", [])[:1]
    return r


def period_label(r: dict) -> str:
    p, a, b = r["period"], r["date_from"], r["date_to"]
    if p == "day":
        wd = WEEKDAY_VI[datetime.strptime(a, "%Y-%m-%d").weekday()]
        return f"{wd}, ngày {_fmt_d(a)}"
    if p == "month":
        return f"Tháng {a[5:7]}/{a[:4]}"
    if p == "year":
        return f"Năm {a[:4]}"
    if p == "week":
        return f"Tuần từ {_fmt_d(a)} đến {_fmt_d(b)}"
    return f"Từ ngày {_fmt_d(a)} đến ngày {_fmt_d(b)}"


# ------------------------------------------------------------------ bang
def report_tables(r: dict) -> dict:
    """Cac bang cua bao cao (dung chung cho Excel, PDF va trang web)."""
    dem = r["demographics"]
    ident = dem["identified"] or 1
    overview = pd.DataFrame([
        ("Kỳ báo cáo", period_label(r)),
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
    if r.get("by_month") and len(r["by_month"]) > 1:
        tables["Theo tháng"] = pd.DataFrame(r["by_month"]).rename(columns={"month": "Tháng", "entries": "Lượt vào"})
    if r.get("tickets"):
        tables["Đối chiếu vé"] = pd.DataFrame(r["tickets"]).rename(columns={
            "date": "Ngày", "entries": "Lượt vào", "tickets": "Số vé", "gap": "Chênh lệch", "gap_rate_pct": "Tỷ lệ (%)"})
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


# ------------------------------------------------------------------ bieu do
def _plt():
    import logging

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Liberation Serif", "DejaVu Serif"],
        "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.edgecolor": CHART["stone"],
        "axes.labelcolor": CHART["ink"], "xtick.color": CHART["ink"], "ytick.color": CHART["ink"],
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.color": CHART["grid"],
        "grid.linewidth": 0.6, "axes.axisbelow": True, "figure.dpi": 100,
    })
    return plt


def _png(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor="white")
    import matplotlib.pyplot as plt
    plt.close(fig)
    buf.seek(0)
    return buf


def chart_trend(r: dict):
    """Luot vao theo 15 phut (ky 1 ngay) / theo ngay (<= 62 ngay) / theo thang (dai hon)."""
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 2.7))
    if r["period"] == "day":
        rows = r["by_15min"]
        x, y = [s["slot"] for s in rows], [s["entries"] for s in rows]
        title, step = "Lượt vào cầu theo khung 15 phút", max(1, len(x) // 12)
    elif len(r["by_day"]) <= 62:
        rows = r["by_day"]
        x, y = [f"{d['date'][8:]}/{d['date'][5:7]}" for d in rows], [d["entries"] for d in rows]
        title, step = "Lượt vào cầu theo ngày", max(1, len(x) // 16)
    else:
        rows = r["by_month"]
        x, y = [f"T{m['month'][5:7]}/{m['month'][2:4]}" for m in rows], [m["entries"] for m in rows]
        title, step = "Lượt vào cầu theo tháng", 1
    if not x:
        plt.close(fig)
        return None
    bars = ax.bar(range(len(x)), y, color=CHART["oxblood"], width=0.72)
    avg = sum(y) / len(y)
    ax.axhline(avg, color=CHART["gold"], linewidth=1.1, linestyle="--", label=f"Bình quân: {avg:,.0f}".replace(",", "."))
    if len(x) <= 16:
        for b, v in zip(bars, y):
            if v:
                ax.annotate(_n(v), (b.get_x() + b.get_width() / 2, v), ha="center", va="bottom", fontsize=7,
                            xytext=(0, 1.5), textcoords="offset points")
    ax.set_xticks(range(0, len(x), step))
    ax.set_xticklabels(x[::step], rotation=0 if len(x) <= 16 else 45, ha="center" if len(x) <= 16 else "right")
    ax.set_ylabel("Lượt vào")
    ax.set_title(title, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.grid(axis="x", visible=False)
    return _png(fig)


def chart_hours_slots(r: dict):
    plt = _plt()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.2, 2.5), gridspec_kw={"width_ratios": [1.7, 1]})
    hours = {h["hour"]: h["entries"] for h in r["by_hour"]}
    hs = list(range(6, 24))
    a1.bar([f"{h}" for h in hs], [hours.get(h, 0) for h in hs], color=CHART["teal"], width=0.7)
    a1.set_title("Lượt vào theo giờ trong ngày", loc="left")
    a1.set_xlabel("Giờ")
    a1.grid(axis="x", visible=False)
    s = r["time_slots"]
    a2.barh([x["slot"] for x in s][::-1], [x["entries"] for x in s][::-1], color=CHART["gold"], height=0.6)
    a2.set_title("Theo buổi", loc="left")
    a2.grid(axis="y", visible=False)
    fig.tight_layout(w_pad=2)
    return _png(fig)


def chart_demographics(r: dict):
    dem = r["demographics"]
    if not dem.get("identified"):
        return None
    plt = _plt()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.5), gridspec_kw={"width_ratios": [1, 1, 1.6]})

    def donut(ax, labels, values, colors, title):
        vals = [(l, v, c) for l, v, c in zip(labels, values, colors) if v]
        if not vals:
            ax.axis("off")
            return
        ax.pie([v for _, v, _ in vals], labels=None, colors=[c for _, _, c in vals], startangle=90, counterclock=False,
               wedgeprops=dict(width=0.38, edgecolor="white"), autopct=lambda p: f"{p:.0f}%", pctdistance=0.8,
               textprops=dict(fontsize=7.5, color="white", fontweight="bold"))
        ax.legend([l for l, _, _ in vals], loc="lower center", bbox_to_anchor=(0.5, -0.28), ncol=2, frameon=False, fontsize=7.5)
        ax.set_title(title, fontsize=9.5)

    donut(axes[0], ["Nam", "Nữ"], [dem["gender"]["Man"], dem["gender"]["Woman"]], [CHART["teal"], CHART["oxblood"]],
          "Giới tính")
    donut(axes[1], ["Trong nước/châu Á", "Quốc tế"], [dem["origin"]["Trong nuoc"], dem["origin"]["Nuoc ngoai"]],
          [CHART["gold"], CHART["stone"]], "Nguồn khách (ước lượng)")
    ages = [(k, v) for k, v in dem["age_range"].items()]
    axes[2].bar([k for k, _ in ages], [v for _, v in ages], color=CHART["oxblood"], width=0.7)
    axes[2].set_title("Nhóm tuổi", loc="left")
    axes[2].tick_params(axis="x", labelrotation=45, labelsize=7)
    axes[2].grid(axis="x", visible=False)
    fig.tight_layout(w_pad=1.5)
    return _png(fig)


def chart_tickets(r: dict):
    rows = r.get("tickets") or []
    if not rows:
        return None
    plt = _plt()
    fig, ax = plt.subplots(figsize=(7.2, 2.4))
    x = [f"{t['date'][8:]}/{t['date'][5:7]}" for t in rows]
    import numpy as np
    i = np.arange(len(x))
    ax.bar(i - 0.2, [t["entries"] for t in rows], 0.4, color=CHART["oxblood"], label="Lượt vào (camera)")
    ax.bar(i + 0.2, [t["tickets"] for t in rows], 0.4, color=CHART["gold"], label="Số cuống vé")
    step = max(1, len(x) // 16)
    ax.set_xticks(i[::step])
    ax.set_xticklabels(x[::step])
    ax.set_title("Lượt vào cầu so với số cuống vé", loc="left")
    ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    ax.grid(axis="x", visible=False)
    return _png(fig)


# ------------------------------------------------------------------ PDF
def _make_doc_class():
    from fpdf import FPDF

    class Doc(FPDF):
        family = "helvetica"
        footer_text = ""

        def header(self):
            self.watermark()
            self.set_xy(self.l_margin, self.t_margin)
            if self.page_no() > 1:
                self.set_font(self.family, "I", 9)
                self.set_text_color(*MUTED)
                self.set_xy(self.l_margin, 10)
                self.cell(0, 5, self.footer_text, align="R")
                self.set_draw_color(*RULE)
                self.set_line_width(0.2)
                self.line(self.l_margin, 15.5, self.w - self.r_margin, 15.5)
                self.set_y(self.t_margin)

        def footer(self):
            self.set_y(-14)
            self.set_draw_color(*RULE)
            self.set_line_width(0.2)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.set_font(self.family, "", 9)
            self.set_text_color(*MUTED)
            self.cell(0, 6, "Báo cáo lập từ dữ liệu hệ thống SmartCau AI", align="L")
            self.set_x(self.l_margin)
            self.cell(0, 6, f"Trang {self.page_no()}/{{nb}}", align="R")

        def watermark(self):
            """Logo SmartCau (mai cau + chu) in chim, mo, giua trang A4."""
            cx, cy, k = self.w / 2, self.h / 2 + 4, 2.7          # 1 don vi logo = 2.7 mm
            ox, oy = cx - 26 * k, cy - 34 * k

            def P(x, y):
                return ox + x * k, oy + y * k
            with self.local_context(stroke_opacity=0.07, fill_opacity=0.07):
                self.set_draw_color(*GOLD)
                self.set_line_width(1.6)
                lines = [[(4, 44), (48, 44)], [(7, 32), (26, 16), (45, 32)], [(19, 20), (26, 12), (33, 20)],
                         [(14, 39), (14, 30)], [(26, 37), (26, 26)], [(38, 39), (38, 30)]]
                for pts in lines:
                    self.polyline([P(*p) for p in pts])
                arc = [(8 + 36 * t, 44 - 28 * t * (1 - t)) for t in [i / 24 for i in range(25)]]   # Q(8,44)(26,30)(44,44)
                self.polyline([P(*p) for p in arc])
                self.set_text_color(*GOLD)
                self.set_font(self.family, "B", 46)
                self.set_xy(self.l_margin, oy + 50 * k)
                self.cell(self.w - self.l_margin - self.r_margin, 18, "SmartCau", align="C")
                self.set_font(self.family, "", 15)
                self.set_xy(self.l_margin, oy + 50 * k + 18)
                self.cell(self.w - self.l_margin - self.r_margin, 8, "CHÙA CẦU · HỘI AN", align="C")
            self.set_text_color(*INK)

    return Doc


def _narrative(r: dict) -> list:
    """Cac doan van tu sinh cho muc I (tinh hinh chung)."""
    days = len(r["by_day"]) or 1
    avg = r["total_entries"] / days
    out = [f"Trong kỳ báo cáo ({period_label(r).lower() if r['period'] != 'day' else period_label(r)}), hệ thống camera "
           f"tại hai chân cầu ghi nhận {_n(r['total_entries'])} lượt khách vào lòng cầu"
           + (f", bình quân {_n(round(avg))} lượt/ngày" if days > 1 else "") + "."]
    prev = (r.get("previous") or {}).get("total_entries")
    if prev:
        ch = (r["total_entries"] - prev) / prev * 100
        same = " cùng số ngày" if r["previous"].get("same_elapsed_days") else ""
        out[-1] += (f" So với{same} kỳ trước ({_fmt_d(r['previous']['date_from'])} – {_fmt_d(r['previous']['date_to'])}: "
                    f"{_n(prev)} lượt), lượng khách {'tăng' if ch >= 0 else 'giảm'} {_pct(abs(ch))}.")
    if days > 1 and r["total_entries"]:
        best = max(r["by_day"], key=lambda d: d["entries"])
        wd = WEEKDAY_VI[datetime.strptime(best["date"], "%Y-%m-%d").weekday()]
        out.append(f"Ngày đông khách nhất là {wd.lower()} {_fmt_d(best['date'])} với {_n(best['entries'])} lượt.")
    if r["peak_hour"] is not None:
        out.append(f"Khung giờ có nhiều lượt vào nhất là {r['peak_hour']}h – {r['peak_hour'] + 1}h "
                   f"({_n(r['peak_hour_entries'])} lượt). Số người trên cầu cao nhất cùng lúc là {r['peak_count']} người "
                   f"(sức chứa quy định {r.get('capacity') or r['kpis']['capacity']} người).")
    out.append(f"Ngoài ra có {_n(r['facade_passes'])} lượt khách đi qua khu vực mặt tiền nhưng không lên cầu.")
    return out


def _assessment(r: dict) -> list:
    k, out = r["kpis"], []
    if r["incidents"] == 0:
        out.append("Trong kỳ không xảy ra tình trạng quá tải trên cầu; công tác điều tiết khách được duy trì ổn định.")
    else:
        o4 = k["o4_handled_within_3min_pct"]
        out.append(f"Trong kỳ xảy ra {r['incidents']} sự cố quá tải; tỷ lệ sự cố được xử lý trong 3 phút đạt "
                   f"{_pct(o4)} (mục tiêu ≥ 90%)." + ("" if o4 is None or o4 >= 90 else
                                                     " Đề nghị tăng cường người trực tại hai đầu cầu vào khung giờ cao điểm."))
    if k["o5_false_alarm_pct"] is not None and k["o5_false_alarm_pct"] > 5:
        out.append(f"Tỷ lệ cảnh báo sai {_pct(k['o5_false_alarm_pct'])} cao hơn mục tiêu 5%; đề nghị kiểm tra lại "
                   "vị trí camera và vạch đếm.")
    if r["peak_hour"] is not None:
        out.append(f"Đề nghị bố trí lực lượng soát vé, hướng dẫn khách tập trung vào khung giờ {r['peak_hour']}h – "
                   f"{r['peak_hour'] + 1}h.")
    if r["alerts"]["CAMERA_LOST"]:
        out.append(f"Camera mất tín hiệu {r['alerts']['CAMERA_LOST']} lần; đề nghị kiểm tra nguồn điện, đường truyền.")
    if k["o8_gap_rate_pct"] is not None and k["o8_gap_rate_pct"] > 10:
        out.append(f"Chênh lệch giữa lượt vào và số vé ở mức {_pct(k['o8_gap_rate_pct'])}; đề nghị rà soát công tác soát vé.")
    return out


def to_pdf(r: dict, options: dict = None) -> bytes:
    """Bao cao PDF theo the thuc van ban hanh chinh. options: xem PDF_DEFAULTS."""
    from fpdf.fonts import FontFace

    o = {**PDF_DEFAULTS, **(options or {})}
    try:
        from .timeutil import local_now
        made_at = local_now()
    except ImportError:
        made_at = datetime.now()

    r = _until_today(r, made_at)
    Doc = _make_doc_class()
    pdf = Doc(format="A4")
    pdf.set_margins(30, 20, 15)                      # trai 30, tren 20, phai 15 mm (Nghi dinh 30)
    pdf.set_auto_page_break(True, margin=20)
    fonts = next((s for s in FONT_SETS if s[0] and os.path.exists(s[0])), None)
    if fonts:
        reg, bold, ital, bi = fonts
        pdf.add_font("vn", "", reg)
        pdf.add_font("vn", "B", bold if os.path.exists(bold or "") else reg)
        pdf.add_font("vn", "I", ital if os.path.exists(ital or "") else reg)
        pdf.add_font("vn", "BI", bi if os.path.exists(bi or "") else (bold if os.path.exists(bold or "") else reg))
        family = "vn"
    else:   # khong co font tieng Viet -> bo dau de khong loi
        import unicodedata
        family = "helvetica"
        r = _strip_accents(r, unicodedata)
        o = _strip_accents(o, unicodedata)
    Doc.family = family
    Doc.footer_text = f"Báo cáo tình hình khách tham quan Chùa Cầu · {period_label(r)}"
    pdf.alias_nb_pages()
    pdf.add_page()
    W = pdf.w - pdf.l_margin - pdf.r_margin
    org_parent = o["org_parent"] or ORG_PARENT
    org_name = o["org_name"] or ORG_NAME
    place = o["place"] or ORG_PLACE

    # ---------------- phan dau: co quan | quoc hieu
    left_w, right_w = 72, W - 72
    y0 = pdf.get_y()
    pdf.set_text_color(*INK)
    pdf.set_font(family, "", 12)
    pdf.set_xy(pdf.l_margin, y0)
    pdf.multi_cell(left_w, 5.5, org_parent.upper(), align="C")
    pdf.set_font(family, "B", 12)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(left_w, 5.5, org_name.upper(), align="C")
    yl = pdf.get_y() + 0.8
    pdf.set_line_width(0.3)
    pdf.set_draw_color(*INK)
    pdf.line(pdf.l_margin + left_w / 2 - 14, yl, pdf.l_margin + left_w / 2 + 14, yl)
    pdf.set_font(family, "", 13)
    pdf.set_xy(pdf.l_margin, yl + 3)
    pdf.cell(left_w, 6, f"Số: {o['report_no'] or '......'}/BC-SCAI", align="C")
    y_left_end = pdf.get_y() + 6

    xr = pdf.l_margin + left_w
    pdf.set_xy(xr, y0)
    pdf.set_font(family, "B", 12)
    pdf.cell(right_w, 5.5, "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", align="C", new_x="LEFT", new_y="NEXT")
    pdf.set_font(family, "B", 13)
    pdf.cell(right_w, 6, "Độc lập - Tự do - Hạnh phúc", align="C", new_x="LEFT", new_y="NEXT")
    tw = pdf.get_string_width("Độc lập - Tự do - Hạnh phúc")
    yr = pdf.get_y() + 0.3
    pdf.line(xr + right_w / 2 - tw / 2, yr, xr + right_w / 2 + tw / 2, yr)
    pdf.set_xy(xr, yr + 4)
    pdf.set_font(family, "I", 13)
    pdf.cell(right_w, 6, f"{place}, ngày {made_at.day:02d} tháng {made_at.month:02d} năm {made_at.year}", align="C")
    pdf.set_y(max(y_left_end, pdf.get_y() + 6) + 6)

    # ---------------- tieu de
    pdf.set_font(family, "B", 14)
    pdf.cell(0, 7, "BÁO CÁO", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "B", 13)
    pdf.multi_cell(0, 6.5, "Tình hình khách tham quan và công tác đảm bảo an toàn\ntại di tích Chùa Cầu (Lai Viễn Kiều)",
                   align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "I", 13)
    pdf.cell(0, 7, f"Kỳ báo cáo: {period_label(r)}", align="C", new_x="LMARGIN", new_y="NEXT")
    yy = pdf.get_y() + 1
    pdf.line(pdf.w / 2 - 20, yy, pdf.w / 2 + 20, yy)
    pdf.ln(6)

    head = FontFace(family=family, emphasis="BOLD", color=INK, fill_color=(238, 234, 226))
    roman = iter(["I", "II", "III", "IV", "V", "VI", "VII", "VIII"])

    def heading(title):
        if pdf.get_y() > pdf.h - 85:          # khong de tieu de muc mo coi cuoi trang
            pdf.add_page()
        pdf.ln(2)
        pdf.set_font(family, "B", 13)
        pdf.set_text_color(*INK)
        pdf.cell(0, 7, f"{next(roman)}. {title.upper()}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def para(text, italic=False, size=13):
        pdf.set_font(family, "I" if italic else "", size)
        pdf.set_text_color(*INK)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 6.5 if size >= 12 else 5, "      " + text, align="J", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(0.8)

    def sub(text):
        pdf.set_font(family, "B", 13)
        pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")

    def table(columns, rows, widths=None, align=None, caption=None):
        if caption:
            pdf.set_font(family, "BI", 11.5)
            pdf.cell(0, 6, caption, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font(family, "", 11.5)
        pdf.set_draw_color(*RULE)
        pdf.set_line_width(0.2)
        pdf.set_fill_color(255, 255, 255)
        with pdf.table(col_widths=widths, line_height=6.2, first_row_as_headings=True, headings_style=head,
                       text_align=align or "LEFT", padding=(1.2, 2), borders_layout="ALL") as t:
            t.row([str(c) for c in columns])
            for row in rows:
                t.row([str(v) for v in row])
        pdf.ln(3)

    def figure(buf, caption):
        if buf is None:
            return
        from PIL import Image
        im = Image.open(buf)
        h = W * im.height / im.width
        if pdf.get_y() + h + 10 > pdf.h - pdf.b_margin:
            pdf.add_page()
        buf.seek(0)
        pdf.image(buf, x=pdf.l_margin, w=W)
        pdf.set_font(family, "I", 11)
        pdf.set_text_color(*MUTED)
        pdf.cell(0, 6, caption, align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(*INK)
        pdf.ln(2)

    fig_no = iter(range(1, 20))
    tbl_no = iter(range(1, 20))
    sec = set(o["sections"])
    charts = o["charts"]
    k = r["kpis"]
    dem = r["demographics"]

    if "overview" in sec:
        heading(SECTIONS["overview"])
        for t in _narrative(r):
            para(t)
        table(["Chỉ tiêu", "Kết quả"], [
            ("Tổng lượt khách vào lòng cầu", _n(r["total_entries"])),
            ("Bình quân lượt vào mỗi ngày", _n(round(r["total_entries"] / (len(r["by_day"]) or 1)))),
            ("Lượt qua mặt tiền (không lên cầu)", _n(r["facade_passes"])),
            ("Số người trên cầu cao nhất cùng lúc", f"{r['peak_count']} người"),
            ("Số sự cố quá tải", _n(r["incidents"])),
            ("Tỷ lệ sự cố xử lý trong 3 phút", _pct(k["o4_handled_within_3min_pct"])),
        ], widths=(3, 1.4), caption=f"Bảng {next(tbl_no)}. Một số chỉ tiêu chính")

    if "trend" in sec:
        heading(SECTIONS["trend"])
        if charts:
            figure(chart_trend(r), f"Hình {next(fig_no)}. Diễn biến lượt khách vào cầu")
            figure(chart_hours_slots(r), f"Hình {next(fig_no)}. Phân bố lượt vào theo giờ và theo buổi")
        if r["period"] == "year" or len(r["by_day"]) > 62:
            rows = [(f"Tháng {m['month'][5:7]}/{m['month'][:4]}", _n(m["entries"])) for m in r["by_month"]]
            table(["Tháng", "Lượt vào"], rows, widths=(2, 1.4), caption=f"Bảng {next(tbl_no)}. Lượt vào theo tháng")
        elif r["period"] != "day":
            rows = [(f"{WEEKDAY_VI[datetime.strptime(d['date'], '%Y-%m-%d').weekday()]}, {_fmt_d(d['date'])}", _n(d["entries"]))
                    for d in r["by_day"]]
            table(["Ngày", "Lượt vào"], rows, widths=(2, 1.4), caption=f"Bảng {next(tbl_no)}. Lượt vào theo ngày")
        rows = [(s["slot"], _n(s["entries"]), _pct(s["entries"] / r["total_entries"] * 100 if r["total_entries"] else None))
                for s in r["time_slots"]]
        table(["Khung giờ", "Lượt vào", "Tỷ lệ"], rows, widths=(2, 1.2, 1), caption=f"Bảng {next(tbl_no)}. Lượt vào theo buổi")

    if "demographics" in sec:
        heading(SECTIONS["demographics"])
        if dem["identified"]:
            n = dem["identified"]
            para(f"Hệ thống ước lượng được thông tin của {_n(n)}/{_n(dem['total'])} lượt khách "
                 f"({_pct(n / dem['total'] * 100 if dem['total'] else None)}); {_n(dem['unknown'])} lượt không đủ độ tin cậy "
                 "được ghi nhận là “không xác định” và không tính vào tỷ lệ. Trong số khách xác định được: nam chiếm "
                 f"{_pct(dem['gender']['Man'] / n * 100)}, nữ chiếm {_pct(dem['gender']['Woman'] / n * 100)}; "
                 f"khách trong nước/châu Á chiếm {_pct(dem['origin']['Trong nuoc'] / n * 100)}, khách quốc tế chiếm "
                 f"{_pct(dem['origin']['Nuoc ngoai'] / n * 100)}.")
            if charts:
                figure(chart_demographics(r), f"Hình {next(fig_no)}. Cơ cấu khách theo giới tính, nguồn khách và nhóm tuổi")
            rows = [("Nam", _n(dem["gender"]["Man"]), _pct(dem["gender"]["Man"] / n * 100)),
                    ("Nữ", _n(dem["gender"]["Woman"]), _pct(dem["gender"]["Woman"] / n * 100)),
                    ("Trong nước/châu Á", _n(dem["origin"]["Trong nuoc"]), _pct(dem["origin"]["Trong nuoc"] / n * 100)),
                    ("Quốc tế", _n(dem["origin"]["Nuoc ngoai"]), _pct(dem["origin"]["Nuoc ngoai"] / n * 100))]
            rows += [(f"Nhóm tuổi {a}", _n(v), _pct(v / n * 100)) for a, v in dem["age_range"].items() if v]
            table(["Nhóm khách", "Số lượt", "Tỷ lệ"], rows, widths=(2, 1.2, 1),
                  caption=f"Bảng {next(tbl_no)}. Cơ cấu khách tham quan")
            para("Ghi chú: giới tính, độ tuổi và nguồn khách là kết quả ước lượng của mô hình trí tuệ nhân tạo, chỉ dùng "
                 "để theo dõi xu hướng; hệ thống không lưu ảnh hay đặc trưng khuôn mặt của khách.", italic=True, size=11)
        else:
            para("Trong kỳ chưa có dữ liệu cơ cấu khách (camera chưa bật chức năng nhận diện hoặc chưa đủ độ tin cậy).")

    if "safety" in sec:
        heading(SECTIONS["safety"])
        if r["incidents"]:
            para(f"Trong kỳ ghi nhận {r['alerts']['WARNING']} lần cảnh báo Vàng (cầu sắp đầy) và {r['incidents']} sự cố "
                 f"quá tải (cảnh báo Đỏ); {r['incidents_acked']} sự cố được người trực xác nhận xử lý, thời gian phản hồi "
                 f"trung bình {_n(r['avg_handle_seconds'])} giây. Tổng thời gian trên cầu vượt sức chứa là "
                 f"{_n(k['o1_minutes_over'])} phút.")
        else:
            para(f"Trong kỳ ghi nhận {r['alerts']['WARNING']} lần cảnh báo Vàng; không xảy ra sự cố quá tải.")
        table(["Mã", "Chỉ số", "Kết quả", "Mục tiêu"], [
            ("O1", "Số phút có số người vượt sức chứa", f"{_n(k['o1_minutes_over'])} phút", "Giảm ≥ 70%"),
            ("O4", "Sự cố được xử lý trong 3 phút", _pct(k["o4_handled_within_3min_pct"]), "≥ 90%"),
            ("O5", "Tỷ lệ cảnh báo sai", _pct(k["o5_false_alarm_pct"]), "≤ 5%"),
            ("O8", "Chênh lệch lượt vào so với số vé", _pct(k["o8_gap_rate_pct"]), "Xu hướng giảm"),
        ], widths=(0.6, 2.6, 1.2, 1.1), caption=f"Bảng {next(tbl_no)}. Kết quả các chỉ số an toàn")
        table(["Loại sự kiện", "Số lần"], [
            ("Cảnh báo Vàng (cầu sắp đầy)", _n(r["alerts"]["WARNING"])),
            ("Cảnh báo Đỏ (quá tải)", _n(r["alerts"]["CRITICAL_ALERT"])),
            ("Đoàn khách lớn", _n(r["alerts"]["GROUP_DETECTED"])),
            ("Camera mất tín hiệu", _n(r["alerts"]["CAMERA_LOST"])),
        ], widths=(2.4, 1), caption=f"Bảng {next(tbl_no)}. Thống kê cảnh báo")

    if "tickets" in sec:
        heading(SECTIONS["tickets"])
        rows = r.get("tickets") or []
        if rows:
            te, tt = sum(t["entries"] for t in rows), sum(t["tickets"] for t in rows)
            para(f"Trong {len(rows)} ngày có số liệu vé, camera ghi nhận {_n(te)} lượt vào lòng cầu, bộ phận soát vé thu "
                 f"{_n(tt)} cuống vé; chênh lệch {_n(te - tt)} lượt ({_pct((te - tt) / te * 100 if te else None)}). "
                 "Số liệu chỉ dùng để điều phối lực lượng soát vé, không dùng làm căn cứ xử phạt.")
            if charts:
                figure(chart_tickets(r), f"Hình {next(fig_no)}. Lượt vào cầu và số cuống vé theo ngày")
            table(["Ngày", "Lượt vào", "Số vé", "Chênh lệch", "Tỷ lệ"],
                  [(_fmt_d(t["date"]), _n(t["entries"]), _n(t["tickets"]), _n(t["gap"]), _pct(t["gap_rate_pct"]))
                   for t in rows], widths=(1.4, 1, 1, 1, 0.9), align="CENTER",
                  caption=f"Bảng {next(tbl_no)}. Đối chiếu lượt vào với số cuống vé")
        else:
            para("Trong kỳ chưa nhập số cuống vé nên chưa đối chiếu được.")

    if "assessment" in sec:
        heading(SECTIONS["assessment"])
        for t in _assessment(r):
            para("- " + t)
        if o["notes"].strip():
            for line in o["notes"].strip().splitlines():
                if line.strip():
                    para(line.strip())

    # ---------------- noi nhan + chu ky
    if pdf.get_y() > pdf.h - 70:
        pdf.add_page()
    pdf.ln(6)
    y = pdf.get_y()
    half = W / 2
    pdf.set_xy(pdf.l_margin, y)
    pdf.set_font(family, "BI", 12)
    pdf.cell(half, 6, "Nơi nhận:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(family, "", 11)
    pdf.multi_cell(half, 5, o["recipients"])
    pdf.set_xy(pdf.l_margin + half, y)
    pdf.set_font(family, "B", 13)
    pdf.multi_cell(half, 6, (o["approver_title"] if o["approver"] or not o["prepared_by"] else o["prepared_title"]).upper(),
                   align="C")
    pdf.set_x(pdf.l_margin + half)
    pdf.set_font(family, "I", 12)
    pdf.cell(half, 6, "(Ký, ghi rõ họ tên)", align="C", new_x="LEFT", new_y="NEXT")
    pdf.ln(18)
    pdf.set_x(pdf.l_margin + half)
    pdf.set_font(family, "B", 13)
    pdf.cell(half, 6, o["approver"] or o["prepared_by"], align="C", new_x="LMARGIN", new_y="NEXT")
    if o["approver"] and o["prepared_by"]:
        pdf.ln(4)
        pdf.set_font(family, "I", 11)
        pdf.cell(0, 6, f"Người lập báo cáo: {o['prepared_by']}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font(family, "I", 9.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 4.5, f"Báo cáo được lập lúc {made_at:%H:%M} ngày {made_at:%d/%m/%Y} từ dữ liệu hệ thống camera AI "
                           "SmartCau (2 camera đặt tại hai chân cầu, đếm lượt qua vạch). Thông tin giới tính, độ tuổi, "
                           "nguồn khách là ước lượng, không phải dữ liệu định danh.")
    return bytes(pdf.output())


def _strip_accents(obj, unicodedata):
    if isinstance(obj, str):
        return unicodedata.normalize("NFKD", obj.replace("đ", "d").replace("Đ", "D")).encode("ascii", "ignore").decode()
    if isinstance(obj, dict):
        return {k: _strip_accents(v, unicodedata) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_strip_accents(v, unicodedata) for v in obj]
    return obj
