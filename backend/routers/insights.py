"""
backend/routers/insights.py  —  Nhan dinh & du bao (ho tro F5.1, FR-17)
========================================================================
Phu trach: MINH.

    GET /insights/live        xu huong 5 phut, du kien bao lau thi day cau, thoi gian cho
                              du kien (FR-17: duoi 3 / 3-5 / tren 5 phut), du bao luot vao
                              tung gio con lai trong ngay
    GET /insights/summary     cac cau nhan dinh tu dong cho trang Tong quan / Bao cao

Du bao dung "trung binh cung thu, cung gio trong 8 tuan gan nhat" nhan voi he so
"hom nay dong hon / vang hon binh thuong bao nhieu tinh den gio nay" - don gian,
giai thich duoc, khong can huan luyen. Chi dung de dieu phoi, khong phai so lieu chinh thuc.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import VisitEvent, get_config, get_state
from ..timeutil import local_day_range_utc, local_now, to_local

router = APIRouter(prefix="/insights", tags=["Nhan dinh & du bao"])

WEEKS = 8
TREND_MIN = 5


def _crossings_between(db, start_loc: datetime, end_loc: datetime, direction: str):
    from .bridge import BridgeCrossing
    return [t for (t,) in db.query(BridgeCrossing.local_time).filter(
        BridgeCrossing.direction == direction, BridgeCrossing.local_time >= start_loc,
        BridgeCrossing.local_time < end_loc).all()]


def _hourly_profile(db, now: datetime):
    """Trung binh luot vao theo gio cua cung thu trong WEEKS tuan truoc (khong tinh hom nay)."""
    totals = [0] * 24
    days = 0
    for w in range(1, WEEKS + 1):
        d = (now - timedelta(days=7 * w)).replace(hour=0, minute=0, second=0, microsecond=0)
        rows = _crossings_between(db, d, d + timedelta(days=1), "in")
        if rows:
            days += 1
            for t in rows:
                totals[t.hour] += 1
    return [round(v / days, 1) for v in totals] if days else None, days


def wait_bucket(minutes):
    if minutes is None:
        return None
    if minutes < 3:
        return "Dưới 3 phút"
    if minutes <= 5:
        return "3–5 phút"
    return "Trên 5 phút"


def wait_bucket_en(minutes):
    if minutes is None:
        return None
    return "Under 3 min" if minutes < 3 else "3–5 min" if minutes <= 5 else "Over 5 min"


@router.get("/live")
def live(db: Session = Depends(get_db)):
    now = local_now()
    cap = get_config(db).alert_threshold
    onbridge = get_state(db).current_count
    since = now - timedelta(minutes=TREND_MIN)
    n_in = len(_crossings_between(db, since, now + timedelta(seconds=1), "in"))
    n_out = len(_crossings_between(db, since, now + timedelta(seconds=1), "out"))
    in_rate, out_rate = n_in / TREND_MIN, n_out / TREND_MIN
    net = in_rate - out_rate
    trend = "tăng" if net > 0.3 else "giảm" if net < -0.3 else "ổn định"

    minutes_to_full = None
    if net > 0 and onbridge <= cap:
        minutes_to_full = round((cap + 1 - onbridge) / net, 1)
    # FR-17: cho bao lau de co cho trong = so nguoi vuot / toc do khach roi cau
    wait = None
    if onbridge >= cap:
        wait = round((onbridge - cap + 1) / out_rate, 1) if out_rate > 0 else 99.0

    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today = [0] * 24
    for t in _crossings_between(db, day0, now + timedelta(seconds=1), "in"):
        today[t.hour] += 1
    profile, days = _hourly_profile(db, now)
    forecast = []
    ratio = None
    if profile:
        elapsed = sum(profile[:now.hour]) + profile[now.hour] * (now.minute / 60)
        so_far = sum(today[:now.hour + 1])
        ratio = round(so_far / elapsed, 2) if elapsed >= 5 else 1.0
        ratio = max(0.3, min(3.0, ratio))
        for h in range(24):
            forecast.append({"hour": h, "actual": today[h] if h <= now.hour else None,
                             "usual": profile[h], "expected": round(profile[h] * ratio, 1)})
        rest = [f for f in forecast if f["hour"] > now.hour]
        peak = max(rest, key=lambda f: f["expected"]) if rest and max(f["expected"] for f in rest) > 0 else None
    else:
        peak = None
    return {
        "now": now.isoformat(timespec="seconds"), "onbridge": onbridge, "capacity": cap,
        "in_per_min": round(in_rate, 1), "out_per_min": round(out_rate, 1), "net_per_min": round(net, 1),
        "trend": trend, "minutes_to_full": minutes_to_full,
        "wait_minutes": wait, "wait_label": wait_bucket(wait), "wait_label_en": wait_bucket_en(wait),
        "forecast": forecast, "history_days": days, "today_vs_usual": ratio,
        "expected_peak": {"hour": peak["hour"], "entries": peak["expected"]} if peak else None,
        "expected_rest_of_day": round(sum(f["expected"] for f in forecast if f["hour"] > now.hour), 0) if forecast else None,
    }


def _pct_change(a, b):
    return round((a - b) / b * 100) if b else None


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    """Cac cau nhan dinh {tone, title, text}. tone: up | down | warn | info."""
    from .alerts import Incident
    from .counting import FacadePass

    now = local_now()
    day0 = now.replace(hour=0, minute=0, second=0, microsecond=0)
    items = []

    today_in = _crossings_between(db, day0, now + timedelta(seconds=1), "in")
    lw0 = day0 - timedelta(days=7)
    lw_same = _crossings_between(db, lw0, lw0 + (now - day0), "in")
    ch = _pct_change(len(today_in), len(lw_same))
    if today_in or lw_same:
        if ch is None:
            items.append({"tone": "info", "title": "Lượt khách hôm nay",
                          "text": f"{len(today_in)} lượt vào cầu tính đến {now:%H:%M}. Chưa có dữ liệu cùng kỳ tuần trước để so sánh."})
        else:
            items.append({"tone": "up" if ch >= 0 else "down", "title": "So với tuần trước",
                          "text": f"{len(today_in)} lượt vào tính đến {now:%H:%M}, "
                                  f"{'nhiều' if ch >= 0 else 'ít'} hơn {abs(ch)}% so với cùng giờ {['Thứ Hai', 'Thứ Ba', 'Thứ Tư', 'Thứ Năm', 'Thứ Sáu', 'Thứ Bảy', 'Chủ nhật'][now.weekday()]} tuần trước ({len(lw_same)} lượt)."})

    lv = live(db)
    if lv["expected_peak"] and lv["expected_peak"]["entries"] >= 1:
        p = lv["expected_peak"]
        items.append({"tone": "warn" if p["entries"] >= lv["capacity"] * 3 else "info", "title": "Dự báo cao điểm",
                      "text": f"Khung {p['hour']}h–{p['hour'] + 1}h dự kiến đông nhất phần còn lại của ngày, khoảng "
                              f"{p['entries']:.0f} lượt vào. Nên bố trí thêm người điều tiết trước {p['hour']}h."})
    if lv["minutes_to_full"] is not None and lv["minutes_to_full"] <= 10:
        items.append({"tone": "warn", "title": "Cầu sắp đầy",
                      "text": f"Khách vào nhanh hơn khách ra {str(lv['net_per_min']).replace('.', ',')} người/phút; với tốc độ này cầu sẽ chạm "
                              f"sức chứa sau khoảng {lv['minutes_to_full']:.0f} phút."})

    s_utc, e_utc = local_day_range_utc(now - timedelta(days=6), now)
    visits = db.query(VisitEvent.origin, VisitEvent.timestamp).filter(
        VisitEvent.timestamp >= s_utc, VisitEvent.timestamp < e_utc, VisitEvent.origin.isnot(None)).all()
    if len(visits) >= 20:
        t_s, t_e = local_day_range_utc(now, now)
        today_v = [o for o, ts in visits if t_s <= ts < t_e]
        week_share = sum(1 for o, _ in visits if o == "Nuoc ngoai") / len(visits) * 100
        text = f"Khách quốc tế (ước lượng) chiếm {week_share:.0f}% lượt khách 7 ngày qua"
        if len(today_v) >= 10:
            today_share = sum(1 for o in today_v if o == "Nuoc ngoai") / len(today_v) * 100
            text += f"; hôm nay {today_share:.0f}%"
        items.append({"tone": "info", "title": "Cơ cấu khách", "text": text + "."})

    inc_today = db.query(Incident).filter(Incident.opened_at >= local_day_range_utc(now, now)[0]).all()
    inc_week = db.query(Incident).filter(Incident.opened_at >= s_utc).count()
    if inc_today:
        slow = [i for i in inc_today if i.acked_at and (i.acked_at - i.opened_at).total_seconds() > 180]
        unacked = [i for i in inc_today if not i.acked_at]
        text = f"{len(inc_today)} sự cố quá tải hôm nay (7 ngày qua: {inc_week})."
        if slow or unacked:
            text += f" {len(slow)} sự cố xử lý chậm hơn 3 phút, {len(unacked)} chưa được xác nhận."
        items.append({"tone": "warn", "title": "Sự cố", "text": text})
    elif inc_week == 0 and today_in:
        items.append({"tone": "up", "title": "An toàn", "text": "Không có sự cố quá tải nào trong 7 ngày qua."})

    facade = db.query(FacadePass).filter(FacadePass.timestamp >= local_day_range_utc(now, now)[0]).count()
    if facade and today_in:
        conv = len(today_in) / (len(today_in) + facade) * 100
        items.append({"tone": "info", "title": "Mặt tiền và lên cầu",
                      "text": f"{facade} lượt đi ngang mặt tiền hôm nay; {conv:.0f}% người đến khu vực cầu đã lên cầu."})
    if not items:
        items.append({"tone": "info", "title": "Chưa đủ dữ liệu",
                      "text": "Hệ thống sẽ đưa ra nhận định khi camera ghi nhận lượt khách."})
    return {"generated_at": now.isoformat(timespec="seconds"), "items": items}
