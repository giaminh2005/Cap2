"""
data_simulator.py
------------------
Sinh DU LIEU MO PHONG (khong phai so lieu thuc te da cong bo) cho:
  1) visitors.csv    - tung luot khach: gio den, quoc gia/xuat xu,
                        nhom tuoi, gioi tinh, thoi gian luu lai tren cau
                        (dai dien cho du lieu tu Module "Thu thap
                        Quoc tich/Xuat xu" - QR check-in / dang ky doan)
  2) occupancy.csv    - so nguoi dang co mat tren cau tai moi moc 5 phut
                        + trang thai canh bao (OK/WARNING/ALERT/CRITICAL)
                        (dai dien cho output cua module Camera AI dem nguoi)

QUAN TRONG: Day la du lieu GIA DINH de lam demo/proof-of-concept cho do
an hoc phan, KHONG PHAI thong ke du lich chinh thuc cua Hoi An. Khi lam
bao cao, nhom can ghi ro day la du lieu mo phong.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from crowd_counter import CameraThresholds
from region_mapping import nationality_to_region

RNG = np.random.default_rng(42)

# --- Gia dinh ty le khach theo quoc gia/xuat xu (MINH HOA, khong phai so lieu that) ---
NATIONALITIES = {
    "Viet Nam (noi dia)": 0.30,
    "Han Quoc": 0.18,
    "Trung Quoc": 0.10,
    "Phap": 0.08,
    "My": 0.06,
    "Duc": 0.05,
    "Dai Loan": 0.05,
    "Uc": 0.04,
    "Thai Lan": 0.04,
    "Anh": 0.04,
    "An Do": 0.04,
    "Nhat Ban": 0.02,
}

AGE_GROUPS = {
    "Duoi 18": 0.05,
    "18-24": 0.20,
    "25-34": 0.28,
    "35-44": 0.22,
    "45-59": 0.17,
    "Tren 60": 0.08,
}

GENDERS = {"Nu": 0.52, "Nam": 0.48}

# Trong so luot khach theo GIO trong ngay (6h-21h), Chua Cau dong cua ngoai gio nay.
HOURLY_WEIGHT = {
    6: 0.3, 7: 0.6, 8: 1.2, 9: 1.6, 10: 1.4, 11: 1.0, 12: 0.6,
    13: 0.5, 14: 0.7, 15: 1.0, 16: 1.5, 17: 1.9, 18: 2.0, 19: 1.7,
    20: 1.1, 21: 0.5,
}


def _weighted_choice(options: dict, n: int):
    keys = list(options.keys())
    probs = np.array(list(options.values()))
    probs = probs / probs.sum()
    idx = RNG.choice(len(keys), size=n, p=probs)
    return [keys[i] for i in idx]


def _emit(records, day, hour, minutes, n):
    nats = _weighted_choice(NATIONALITIES, n)
    ages = _weighted_choice(AGE_GROUPS, n)
    gens = _weighted_choice(GENDERS, n)
    dwell = np.clip(RNG.normal(6, 2, size=n), 2, 15)
    for i in range(n):
        arrival = day.replace(hour=hour, minute=int(minutes[i]), second=0)
        records.append({
            "arrival_time": arrival,
            "dwell_minutes": round(float(dwell[i]), 1),
            "nationality": nats[i],
            "age_group": ages[i],
            "gender": gens[i],
        })


def simulate_visitors(start_date: str, num_days: int = 14, base_daily_visitors: int = 1500) -> pd.DataFrame:
    """Sinh danh sach tung luot khach qua Chua Cau trong `num_days` ngay.

    Mo phong 2 kieu den: khach le (rai deu trong gio) va DOAN/TOUR (den
    cung luc mot nhom 5-35 nguoi trong vai phut) - day chinh la nguyen
    nhan gay QUA TAI DOT NGOT tren cau trong thuc te, va la ly do can
    he thong canh bao tu dong thay vi dem thu cong.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    records = []
    total_weight = sum(HOURLY_WEIGHT.values())

    for d in range(num_days):
        day = start + timedelta(days=d)
        # Cuoi tuan dong hon ngay thuong (gia dinh)
        weekend_factor = 1.35 if day.weekday() >= 5 else 1.0
        day_total = int(RNG.normal(base_daily_visitors, base_daily_visitors * 0.08) * weekend_factor)
        day_total = max(day_total, 100)

        for hour, w in HOURLY_WEIGHT.items():
            lam = day_total * (w / total_weight)
            n_hour = RNG.poisson(lam)
            if n_hour <= 0:
                continue

            remaining = n_hour
            # ~35% luot khach di theo doan/tour (den thanh cum)
            group_budget = int(n_hour * 0.35)
            while group_budget > 0:
                gsize = int(np.clip(RNG.normal(14, 8), 4, 35))
                gsize = min(gsize, group_budget, remaining)
                if gsize <= 0:
                    break
                base_minute = int(RNG.integers(0, 60))
                jitter = RNG.integers(-1, 2, size=gsize)
                minutes = np.clip(base_minute + jitter, 0, 59)
                _emit(records, day, hour, minutes, gsize)
                group_budget -= gsize
                remaining -= gsize

            if remaining > 0:
                minutes = RNG.integers(0, 60, size=remaining)
                _emit(records, day, hour, minutes, remaining)

    df = pd.DataFrame.from_records(records)
    df.sort_values("arrival_time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    # NANG CAP Phase 3/5: them cot "region" (quy doi tu "nationality" - xem
    # region_mapping.py) de dashboard.py co the ve bieu do theo khu vuc
    # ma khong can suy doan lai tu ten quoc gia moi lan ve bieu do.
    df["region"] = df["nationality"].map(nationality_to_region)
    return df


def compute_occupancy(visitors: pd.DataFrame, thresholds: CameraThresholds = None, step_minutes: int = 5) -> pd.DataFrame:
    """Tu danh sach luot khach (gio den + thoi gian luu lai), tinh so nguoi
    dang co mat TREN CAU tai moi moc thoi gian step_minutes phut - mo phong
    dau ra cua camera AI dem nguoi thoi gian thuc."""
    th = thresholds or CameraThresholds()
    # Dung numpy datetime64[m] xuyen suot (khong boc qua pd.Series) de tranh
    # bi ep ve do phan giai nanosecond mac dinh cua pandas khi astype("int64").
    starts_ts = visitors["arrival_time"].values.astype("datetime64[m]").astype("int64")
    ends_ts = (visitors["arrival_time"] + pd.to_timedelta(visitors["dwell_minutes"], unit="m")) \
        .values.astype("datetime64[m]").astype("int64")

    t0 = pd.Timestamp(visitors["arrival_time"].min()).floor("h")
    t1 = pd.Timestamp(visitors["arrival_time"].max()).ceil("h")
    timeline = pd.date_range(t0, t1, freq=f"{step_minutes}min")
    timeline_ts = timeline.values.astype("datetime64[m]").astype("int64")

    rows = []
    for t, t64 in zip(timeline, timeline_ts):
        occ = int(((starts_ts <= t64) & (ends_ts > t64)).sum())
        rows.append({"timestamp": t, "occupancy": occ, "status": th.status_of(occ)})

    occ_df = pd.DataFrame(rows)
    return occ_df


if __name__ == "__main__":
    import os

    out_dir = os.path.join(os.path.dirname(__file__), "..", "sample_data")
    os.makedirs(out_dir, exist_ok=True)

    visitors = simulate_visitors(start_date="2026-09-08", num_days=14, base_daily_visitors=1500)
    occupancy = compute_occupancy(visitors)

    visitors.to_csv(os.path.join(out_dir, "visitors.csv"), index=False)
    occupancy.to_csv(os.path.join(out_dir, "occupancy.csv"), index=False)

    n_alert = (occupancy["status"].isin(["ALERT", "CRITICAL"])).sum()
    print(f"Da sinh {len(visitors)} luot khach trong 14 ngay (mo phong).")
    print(f"Da tinh {len(occupancy)} moc thoi gian occupancy (moi 5 phut).")
    print(f"So moc thoi gian VUOT NGUONG (ALERT/CRITICAL): {n_alert} ({n_alert/len(occupancy)*100:.1f}%)")
    print(f"Da luu: {out_dir}/visitors.csv va {out_dir}/occupancy.csv")
