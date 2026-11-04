"""
generate_dashboard.py
----------------------
Doc visitors.csv + occupancy.csv (sinh boi data_simulator.py) va tao ra
MOT file HTML dashboard duy nhat, tu chua toan bo (khong can Internet,
khong can CDN) de nhom co the mo bang trinh duyet va trinh bay/demo.

Chay: python generate_dashboard.py
Ket qua: ../dashboard.html
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

import base64
import io
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from data_simulator import simulate_visitors, compute_occupancy
from crowd_counter import CameraThresholds
from region_mapping import REGION_ORDER, REGION_LABEL_DISPLAY, DISCLAIMER_VI, nationality_to_region

plt.rcParams.update({
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#444444",
    "figure.facecolor": "white",
})

PALETTE = ["#2563eb", "#f97316", "#10b981", "#ef4444", "#8b5cf6", "#06b6d4",
           "#eab308", "#ec4899", "#64748b", "#14b8a6", "#a855f7", "#f43f5e"]


def fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def chart_occupancy_day(occupancy: pd.DataFrame, thresholds: CameraThresholds) -> str:
    occupancy = occupancy.copy()
    occupancy["timestamp"] = pd.to_datetime(occupancy["timestamp"])
    occupancy["date"] = occupancy["timestamp"].dt.date
    # chon ngay co dinh diem occupancy cao nhat de minh hoa canh bao
    peak_date = occupancy.loc[occupancy["occupancy"].idxmax(), "date"]
    day_df = occupancy[occupancy["date"] == peak_date]

    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    ax.fill_between(day_df["timestamp"], day_df["occupancy"], color="#93c5fd", alpha=0.4)
    ax.plot(day_df["timestamp"], day_df["occupancy"], color="#2563eb", linewidth=1.6)
    ax.axhline(thresholds.warning, color="#f59e0b", linestyle="--", linewidth=1, label=f"Canh bao Vang (tu {thresholds.warning})")
    ax.axhline(thresholds.alert, color="#ef4444", linestyle="--", linewidth=1, label=f"Suc chua toi da ({thresholds.alert}) - Do khi vuot lien tuc {int(thresholds.red_hold_sec)}s")
    ax.set_title(f"So nguoi tren Chua Cau theo thoi gian thuc - ngay {peak_date} (mo phong)")
    ax.set_ylabel("So nguoi dang co mat")
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    ax.legend(loc="upper left", fontsize=9, frameon=False)
    fig.autofmt_xdate()
    return fig_to_base64(fig)


def chart_hourly_pattern(visitors: pd.DataFrame) -> str:
    v = visitors.copy()
    v["hour"] = pd.to_datetime(v["arrival_time"]).dt.hour
    by_hour = v.groupby("hour").size()
    fig, ax = plt.subplots(figsize=(9.5, 3.2))
    ax.bar(by_hour.index, by_hour.values, color="#2563eb")
    ax.set_title("Tong luot khach theo gio trong ngay (gop 14 ngay mo phong)")
    ax.set_xlabel("Gio")
    ax.set_ylabel("Luot khach")
    ax.set_xticks(list(by_hour.index))
    return fig_to_base64(fig)


def chart_nationality(visitors: pd.DataFrame) -> str:
    counts = visitors["nationality"].value_counts()
    fig, ax = plt.subplots(figsize=(9.5, 4.2))
    colors = (PALETTE * (len(counts) // len(PALETTE) + 1))[: len(counts)]
    ax.barh(counts.index[::-1], counts.values[::-1], color=colors[::-1])
    ax.set_title("Ty trong khach theo quoc gia/xuat xu (du lieu mo phong)")
    ax.set_xlabel("So luot khach")
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    return fig_to_base64(fig)


def chart_age_gender(visitors: pd.DataFrame) -> str:
    order = ["Duoi 18", "18-24", "25-34", "35-44", "45-59", "Tren 60"]
    pivot = visitors.pivot_table(index="age_group", columns="gender", aggfunc="size", fill_value=0)
    pivot = pivot.reindex(order)
    fig, ax = plt.subplots(figsize=(9.5, 3.4))
    x = range(len(pivot.index))
    width = 0.38
    ax.bar([i - width / 2 for i in x], pivot["Nu"], width=width, label="Nu", color="#ec4899")
    ax.bar([i + width / 2 for i in x], pivot["Nam"], width=width, label="Nam", color="#2563eb")
    ax.set_xticks(list(x))
    ax.set_xticklabels(pivot.index)
    ax.set_title("Co cau khach theo nhom tuoi & gioi tinh (du lieu mo phong)")
    ax.set_ylabel("Luot khach")
    ax.legend(frameon=False)
    return fig_to_base64(fig)


def chart_region_distribution(visitors: pd.DataFrame) -> str:
    """NANG CAP Phase 5 - "Phan bo khach theo khu vuc" (1 trong 4 bieu do
    moi yeu cau o Phase 5)."""
    counts = visitors["region"].value_counts().reindex(REGION_ORDER).fillna(0)
    labels = [REGION_LABEL_DISPLAY.get(r, r) for r in counts.index]
    fig, ax = plt.subplots(figsize=(9.5, 3.4))
    colors = PALETTE[: len(counts)]
    ax.bar(labels, counts.values, color=colors)
    ax.set_title("Phan bo khach theo khu vuc (quy doi tu quoc gia/xuat xu - du lieu mo phong)")
    ax.set_ylabel("So luot khach")
    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{int(v):,}", ha="center", va="bottom", fontsize=9)
    return fig_to_base64(fig)


def chart_hourly_region(visitors: pd.DataFrame) -> str:
    """NANG CAP Phase 5 - "Xu huong theo gio x khu vuc" (gio nao khach
    thuoc nhom nao dong nhat), bieu do cot nhom (grouped bar) theo gio."""
    v = visitors.copy()
    v["hour"] = pd.to_datetime(v["arrival_time"]).dt.hour
    pivot = v.pivot_table(index="hour", columns="region", aggfunc="size", fill_value=0)
    pivot = pivot.reindex(columns=REGION_ORDER, fill_value=0)

    fig, ax = plt.subplots(figsize=(9.8, 3.6))
    hours = pivot.index.tolist()
    n_regions = len(REGION_ORDER)
    width = 0.8 / n_regions
    x = np.arange(len(hours))
    for i, region in enumerate(REGION_ORDER):
        ax.bar(x + i * width - 0.4 + width / 2, pivot[region].values, width=width,
               label=REGION_LABEL_DISPLAY.get(region, region), color=PALETTE[i % len(PALETTE)])
    ax.set_xticks(list(x))
    ax.set_xticklabels(hours)
    ax.set_xlabel("Gio")
    ax.set_ylabel("Luot khach")
    ax.set_title("Luot khach theo gio x khu vuc (gop 14 ngay mo phong) - giup chon khung gio truyen thong theo tung nhom khach")
    ax.legend(frameon=False, fontsize=8, ncol=4, loc="upper left")
    return fig_to_base64(fig)


def chart_age_gender_region_heatmap(visitors: pd.DataFrame) -> str:
    """NANG CAP Phase 5 - "Heatmap tuoi x gioi tinh x khu vuc": vi 1 anh
    2D chi the hien duoc 2 chieu, ghep CHIEU KHU VUC va CHIEU GIOI TINH
    lam 1 truc cot (vd "Phuong Tay / Nu"), truc hang la nhom tuoi."""
    age_order = ["Duoi 18", "18-24", "25-34", "35-44", "45-59", "Tren 60"]
    v = visitors.copy()
    v["col"] = v["region"].map(lambda r: REGION_LABEL_DISPLAY.get(r, r)) + " / " + v["gender"]

    col_order = []
    for region in REGION_ORDER:
        rlabel = REGION_LABEL_DISPLAY.get(region, region)
        for gender in ["Nu", "Nam"]:
            col_order.append(f"{rlabel} / {gender}")

    pivot = v.pivot_table(index="age_group", columns="col", aggfunc="size", fill_value=0)
    pivot = pivot.reindex(index=age_order, columns=col_order, fill_value=0)

    fig, ax = plt.subplots(figsize=(11, 4.2))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(col_order)))
    ax.set_xticklabels(col_order, rotation=40, ha="right", fontsize=8)
    ax.set_yticks(range(len(age_order)))
    ax.set_yticklabels(age_order)
    ax.set_title("Heatmap: Nhom tuoi x Gioi tinh x Khu vuc (so luot khach - du lieu mo phong)")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = int(pivot.values[i, j])
            if val > 0:
                ax.text(j, i, f"{val}", ha="center", va="center", fontsize=7,
                        color="white" if val > pivot.values.max() * 0.5 else "black")
    fig.colorbar(im, ax=ax, shrink=0.8, label="So luot khach")
    fig.tight_layout()
    return fig_to_base64(fig)


def compute_peak_hour_per_region(visitors: pd.DataFrame) -> pd.DataFrame:
    """NANG CAP Phase 5 - "Peak hours de lap lich nhan su": tra ve bang
    GIO CAO DIEM NHAT cho TUNG khu vuc (vd "khach phuong Tay dong nhat
    luc 17h")."""
    v = visitors.copy()
    v["hour"] = pd.to_datetime(v["arrival_time"]).dt.hour
    rows = []
    for region in REGION_ORDER:
        sub = v[v["region"] == region]
        if sub.empty:
            continue
        by_hour = sub.groupby("hour").size()
        peak_hour = by_hour.idxmax()
        rows.append({
            "region": REGION_LABEL_DISPLAY.get(region, region),
            "peak_hour": f"{peak_hour}:00-{peak_hour + 1}:00",
            "peak_count": int(by_hour.max()),
            "total": int(len(sub)),
        })
    return pd.DataFrame(rows)


def export_marketing_summary_csv(visitors: pd.DataFrame, out_path: str) -> None:
    """NANG CAP Phase 5 - "Export CSV cho doi marketing": xuat 1 file CSV
    TONG HOP (hour x region x age_group x gender -> so luot khach), de
    doi marketing dung truc tiep (vd import vao Excel/PowerBI) ma khong
    can tu xu ly lai tu visitors.csv tho (hon 10 nghin dong)."""
    v = visitors.copy()
    v["hour"] = pd.to_datetime(v["arrival_time"]).dt.hour
    summary = (
        v.groupby(["hour", "region", "age_group", "gender"])
        .size()
        .reset_index(name="visit_count")
        .sort_values(["hour", "region", "age_group", "gender"])
    )
    summary["region"] = summary["region"].map(lambda r: REGION_LABEL_DISPLAY.get(r, r))
    summary.to_csv(out_path, index=False, encoding="utf-8-sig")


def build_html(visitors: pd.DataFrame, occupancy: pd.DataFrame, thresholds: CameraThresholds) -> str:
    total_visitors = len(visitors)
    n_days = visitors["arrival_time"].apply(lambda t: t.date()).nunique() if not visitors.empty else 0
    peak_occ = int(occupancy["occupancy"].max())
    n_alert_events = int(occupancy["status"].isin(["ALERT", "CRITICAL"]).sum())
    pct_alert = n_alert_events / len(occupancy) * 100
    top_nat = visitors["nationality"].value_counts().idxmax()
    top_nat_pct = visitors["nationality"].value_counts(normalize=True).max() * 100
    avg_dwell = visitors["dwell_minutes"].mean()

    top_events = (
        occupancy[occupancy["status"].isin(["ALERT", "CRITICAL"])]
        .sort_values("occupancy", ascending=False)
        .head(8)
    )
    rows_html = "".join(
        f"<tr><td>{r.timestamp}</td><td>{int(r.occupancy)}</td>"
        f"<td><span class='badge badge-{r.status.lower()}'>{r.status}</span></td></tr>"
        for r in top_events.itertuples()
    )

    nat_table = visitors["nationality"].value_counts(normalize=True).mul(100).round(1)
    nat_rows = "".join(f"<tr><td>{k}</td><td>{v:.1f}%</td></tr>" for k, v in nat_table.items())

    img_occ = chart_occupancy_day(occupancy, thresholds)
    img_hour = chart_hourly_pattern(visitors)
    img_nat = chart_nationality(visitors)
    img_age = chart_age_gender(visitors)

    # --- NANG CAP Phase 5: bieu do + bang moi theo khu vuc ---
    img_region = chart_region_distribution(visitors)
    img_hour_region = chart_hourly_region(visitors)
    img_heatmap = chart_age_gender_region_heatmap(visitors)
    peak_df = compute_peak_hour_per_region(visitors)
    peak_rows = "".join(
        f"<tr><td>{r.region}</td><td>{r.peak_hour}</td><td>{r.peak_count:,}</td><td>{r.total:,}</td></tr>"
        for r in peak_df.itertuples()
    )

    html = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8" />
<title>SmartCau AI - Dashboard Giam sat & Marketing (Demo)</title>
<style>
  :root {{
    --bg: #f6f7fb; --card: #ffffff; --ink: #111827; --muted: #6b7280;
    --line: #e5e7eb; --brand: #2563eb;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
          background: var(--bg); color: var(--ink); }}
  header {{ background: linear-gradient(135deg,#1e3a8a,#2563eb); color:#fff; padding: 28px 32px; }}
  header h1 {{ margin:0 0 4px 0; font-size: 22px; }}
  header p {{ margin:0; opacity:.9; font-size: 13px; }}
  .wrap {{ max-width: 1100px; margin: 0 auto; padding: 24px 20px 60px; }}
  .kpis {{ display:grid; grid-template-columns: repeat(5, 1fr); gap:14px; margin: -18px 0 22px; }}
  .kpi {{ background: var(--card); border:1px solid var(--line); border-radius:12px; padding:14px 16px;
          box-shadow: 0 1px 2px rgba(0,0,0,.04); }}
  .kpi .v {{ font-size: 22px; font-weight: 700; color: var(--brand); }}
  .kpi .l {{ font-size: 11.5px; color: var(--muted); margin-top:2px; }}
  .card {{ background: var(--card); border:1px solid var(--line); border-radius:12px; padding:18px;
           margin-bottom: 18px; box-shadow: 0 1px 2px rgba(0,0,0,.04); }}
  .card h2 {{ font-size: 15px; margin: 0 0 12px; }}
  .grid2 {{ display:grid; grid-template-columns: 1fr 1fr; gap: 18px; }}
  img {{ width:100%; height:auto; display:block; border-radius: 8px; }}
  table {{ width:100%; border-collapse: collapse; font-size: 13px; }}
  th, td {{ text-align:left; padding: 7px 8px; border-bottom: 1px solid var(--line); }}
  th {{ color: var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.03em;}}
  .badge {{ padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight:700; }}
  .badge-alert {{ background:#ffedd5; color:#c2410c; }}
  .badge-critical {{ background:#fee2e2; color:#b91c1c; }}
  .note {{ font-size: 12.5px; color: var(--muted); line-height:1.5; }}
  .foot {{ text-align:center; color:var(--muted); font-size:12px; margin-top: 30px; }}
  @media (max-width: 800px) {{ .kpis {{ grid-template-columns: repeat(2,1fr);}} .grid2{{grid-template-columns:1fr;}} }}
</style>
</head>
<body>
<header>
  <h1>SmartCau AI &mdash; Dashboard Giam sat Dam dong & Phan tich Khach du lich (Ban demo)</h1>
  <p>Di tich Chua Cau, Hoi An &middot; Du lieu: {n_days} ngay MO PHONG (khong phai so lieu thuc te da cong bo) &middot; Vang tu {thresholds.warning} nguoi, suc chua toi da {thresholds.alert} nguoi</p>
</header>
<div class="wrap">

  <div class="kpis">
    <div class="kpi"><div class="v">{total_visitors:,}</div><div class="l">Tong luot khach ({n_days} ngay)</div></div>
    <div class="kpi"><div class="v">{peak_occ}</div><div class="l">So nguoi cao nhat cung luc</div></div>
    <div class="kpi"><div class="v">{n_alert_events}</div><div class="l">Moc thoi gian vuot nguong ({pct_alert:.1f}%)</div></div>
    <div class="kpi"><div class="v">{top_nat}</div><div class="l">Nhom khach dong nhat ({top_nat_pct:.0f}%)</div></div>
    <div class="kpi"><div class="v">{avg_dwell:.1f} phut</div><div class="l">Thoi gian luu lai TB tren cau</div></div>
  </div>

  <div class="card">
    <h2>1. Giam sat dam dong theo thoi gian thuc (module Camera AI dem nguoi)</h2>
    <img src="data:image/png;base64,{img_occ}" alt="Occupancy chart" />
    <p class="note">Duong xanh la so nguoi dang co mat tren cau (tinh tu du lieu mo phong luot khach + thoi gian luu lai).
    Cac vach dut la 3 nguong canh bao dung trong <code>crowd_counter.py</code>. Trong he thong that, duong nay se duoc
    cap nhat truc tiep tu module nhan dien nguoi qua camera (xem phan Kiem thu ben duoi).</p>
  </div>

  <div class="card">
    <h2>2. Cac moc thoi gian vuot nguong gan day (nhat ky canh bao mo phong)</h2>
    <table>
      <thead><tr><th>Thoi diem</th><th>So nguoi</th><th>Trang thai</th></tr></thead>
      <tbody>{rows_html if rows_html else '<tr><td colspan="3">Khong co moc vuot nguong trong du lieu mo phong nay.</td></tr>'}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>3. Gio cao diem trong ngay</h2>
    <img src="data:image/png;base64,{img_hour}" alt="Hourly pattern" />
    <p class="note">Giup Ban quan ly bo tri nhan su/canh bao va giup marketing chon khung gio dang bai truyen thong,
    khuyen mai giam tai (vd uu dai buoi trua) phu hop.</p>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>4. Khach theo quoc gia/xuat xu</h2>
      <img src="data:image/png;base64,{img_nat}" alt="Nationality chart" />
    </div>
    <div class="card">
      <h2>5. Bang chi tiet ty trong quoc gia</h2>
      <table><thead><tr><th>Quoc gia/xuat xu</th><th>Ty trong</th></tr></thead><tbody>{nat_rows}</tbody></table>
    </div>
  </div>

  <div class="card">
    <h2>6. Co cau tuoi & gioi tinh</h2>
    <img src="data:image/png;base64,{img_age}" alt="Age gender chart" />
    <p class="note">Ket hop voi muc 4, day la co so de phan khuc khach hang (customer segmentation) cho campaign
    marketing: vi du chien dich rieng cho khach Han Quoc 25-34 tuoi, hoac uu dai gia dinh cho nhom co tre em.</p>
  </div>

  <div class="card">
    <h2>7. Phan bo khach theo khu vuc (Phase 3/5 - nang cap)</h2>
    <img src="data:image/png;base64,{img_region}" alt="Region distribution chart" />
    <p class="note">{DISCLAIMER_VI}</p>
  </div>

  <div class="card">
    <h2>8. Xu huong theo gio x khu vuc</h2>
    <img src="data:image/png;base64,{img_hour_region}" alt="Hourly by region chart" />
    <p class="note">Giup chon dung khung gio cho tung chien dich theo nhom khach (vd dang bai tieng Anh luc khach
    Phuong Tay dong nhat, thay vi dang chung chung ca ngay).</p>
  </div>

  <div class="card">
    <h2>9. Heatmap: Nhom tuoi x Gioi tinh x Khu vuc</h2>
    <img src="data:image/png;base64,{img_heatmap}" alt="Age x gender x region heatmap" />
    <p class="note">O cang dam mau = cang nhieu luot khach thuoc dung to hop (nhom tuoi, gioi tinh, khu vuc) do.</p>
  </div>

  <div class="card">
    <h2>10. Gio cao diem theo tung khu vuc (xep lich nhan su/marketing)</h2>
    <table>
      <thead><tr><th>Khu vuc</th><th>Gio cao diem</th><th>So luot (gio cao diem)</th><th>Tong luot (14 ngay)</th></tr></thead>
      <tbody>{peak_rows if peak_rows else '<tr><td colspan="4">Khong co du lieu.</td></tr>'}</tbody>
    </table>
  </div>

  <div class="card">
    <h2>Gioi han & minh bach ve du lieu</h2>
    <p class="note">
    Toan bo so lieu trong dashboard nay la <b>du lieu MO PHONG</b> duoc sinh boi <code>data_simulator.py</code> de lam
    proof-of-concept cho do an hoc phan &mdash; KHONG PHAI so lieu du lich chinh thuc cua Hoi An. Module dem nguoi qua
    camera (<code>crowd_counter.py</code>, dung OpenCV HOG+SVM pedestrian detector co san) da duoc kiem thu don vi
    (xem <code>test_crowd_counter.py</code>, 3/3 test PASS) nhung chua duoc chay tren anh/video that tu Chua Cau vi
    moi truong lam demo nay khong co ket noi Internet de tai anh mau. Neu ban gui mot anh/video dong nguoi that,
    co the chay nhan dien thuc te ngay. Camera AI KHONG the xac dinh quoc tich tu khuon mat &mdash; du lieu quoc gia
    o day dai dien cho k&ecirc;nh check-in so (QR/dang ky doan) bo sung, nhu da neu trong tai lieu du an.
    </p>
  </div>

  <div class="foot">SmartCau AI Demo &middot; Sinh tu du lieu mo phong luc {pd.Timestamp.now():%Y-%m-%d %H:%M} &middot; Do an hoc phan Quan tri Du an TMDT</div>
</div>
</body>
</html>"""
    return html


if __name__ == "__main__":
    here = os.path.dirname(__file__)
    data_dir = os.path.join(here, "..", "sample_data")

    v_path = os.path.join(data_dir, "visitors.csv")
    o_path = os.path.join(data_dir, "occupancy.csv")
    thresholds = CameraThresholds()

    # NANG CAP Phase 3/5: file CSV CU (sinh truoc khi co cot "region", hoac
    # sinh khi nguong canh bao con la 7/9/10 cu) se KHONG khop voi code
    # moi (bug #2 kieu moi: dashboard ve vach nguong moi nhung du lieu cu
    # lai tinh status theo nguong cu). De tranh lai LECH nhu truoc, neu
    # phat hien du lieu cu (thieu cot "region") thi SINH LAI tu dau thay
    # vi dung tiep file cu.
    need_regen = not (os.path.exists(v_path) and os.path.exists(o_path))
    if not need_regen:
        _probe = pd.read_csv(v_path, nrows=1)
        if "region" not in _probe.columns:
            print("Phat hien du lieu mo phong CU (thieu cot 'region') - sinh lai cho khop ban nang cap moi...")
            need_regen = True

    if need_regen:
        visitors = simulate_visitors(start_date="2026-09-08", num_days=14, base_daily_visitors=1500)
        occupancy = compute_occupancy(visitors, thresholds=thresholds)
        os.makedirs(data_dir, exist_ok=True)
        visitors.to_csv(v_path, index=False)
        occupancy.to_csv(o_path, index=False)
    else:
        visitors = pd.read_csv(v_path, parse_dates=["arrival_time"])
        occupancy = pd.read_csv(o_path, parse_dates=["timestamp"])
        # Luon tinh lai "status" tu nguong HIEN TAI (khong tin cot status
        # da luu san trong CSV cu) - tranh lech nguong nhu bug #2 goc.
        occupancy["status"] = occupancy["occupancy"].apply(thresholds.status_of)

    html = build_html(visitors, occupancy, thresholds)
    out_path = os.path.join(here, "..", "dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Da tao dashboard: {out_path}")

    summary_path = os.path.join(data_dir, "marketing_summary.csv")
    export_marketing_summary_csv(visitors, summary_path)
    print(f"Da xuat CSV tong hop cho marketing: {summary_path}")
