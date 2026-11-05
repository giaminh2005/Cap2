"""
backend/messages.py  —  Noi dung tin nhan Telegram (dinh dang HTML, co bieu tuong)
===================================================================================
Moi tin nhan canh bao deu kem "anh chup" tinh hinh hien tai cua cau:
so nguoi / suc chua (thanh muc), tung chan cau, xu huong 5 phut, thoi gian
cho, luot vao hom nay, camera, su co dang mo. Cac ham chi DOC CSDL.

    status_block(db)          khoi tinh hinh dung chung
    status_message(db)        tin /tinhhinh
    event_message(db, ...)    tin cho tung su kien camera gui len
    incident_closed_message   tin dong su co
    today_message(db)         tin /homnay
    morning_message(db)       ban tin dau ngay (luc mo cua)
    daily_report_message(r)   tom tat bao cao ngay (kem PDF)
"""

from datetime import datetime, timedelta
from html import escape

from .models import OccupancySnapshot, get_config, get_state
from .timeutil import local_now, to_local

LEVEL = {  # ma muc -> (bieu tuong, ten)
    "OK": ("🟢", "An toàn"), "WARNING": ("🟡", "Cảnh báo Vàng"), "ALERT": ("🟠", "Vàng · đang xác nhận"),
    "CRITICAL": ("🔴", "Quá tải"),
}
FOOT = "<i>SmartCau AI · Chùa Cầu Hội An</i>"


def bar(value: int, cap: int, width: int = 10) -> str:
    cap = max(1, cap)
    filled = min(width, round(value / cap * width))
    color = "🟥" if value > cap else "🟨" if value >= cap * 0.75 else "🟩"
    return color * filled + "⬜" * (width - filled)


def _level(db) -> str:
    latest = db.query(OccupancySnapshot).order_by(OccupancySnapshot.timestamp.desc()).first()
    if latest is None or datetime.utcnow() - latest.timestamp > timedelta(seconds=30):
        return "OK"
    return latest.status or "OK"


def _stamp() -> str:
    return local_now().strftime("%H:%M:%S · %d/%m/%Y")


def status_block(db, level: str = None) -> str:
    from .routers.alerts import Incident
    from .routers.bridge import _get_bridge_state, cameras
    from .routers.insights import live

    cfg = get_config(db)
    st = _get_bridge_state(db)
    lv = live(db)
    onb, cap = get_state(db).current_count, cfg.alert_threshold
    level = level or _level(db)
    icon, name = LEVEL.get(level, LEVEL["OK"])
    trend_icon = {"tăng": "📈", "giảm": "📉"}.get(lv["trend"], "➖")
    lines = [
        f"{icon} <b>{name}</b> · <b>{onb}/{cap}</b> người trên cầu",
        f"{bar(onb, cap)} {round(onb / max(1, cap) * 100)}%",
        f"🌉 Chân cầu 1: <b>{st.num1}</b> · Chân cầu 2: <b>{st.num2}</b>",
        f"{trend_icon} 5 phút qua: vào {lv['in_per_min']}/phút · ra {lv['out_per_min']}/phút ({lv['trend']})",
    ]
    if lv["minutes_to_full"] is not None and onb <= cap and level != "CRITICAL":
        lines.append(f"⏳ Dự kiến đầy sau khoảng <b>{lv['minutes_to_full']:.0f} phút</b>")
    if lv["wait_label"]:
        lines.append(f"⌛ Thời gian chờ dự kiến: <b>{lv['wait_label']}</b>")
    lines.append(f"🎫 Hôm nay: <b>{st.dem}</b> lượt vào cầu")
    cams = cameras(db)
    lines.append("📷 " + " · ".join(f"Cam {c['camera_id']} {'✅' if c['online'] else '❌'}" for c in cams))
    inc = db.query(Incident).filter(Incident.closed_at.is_(None)).order_by(Incident.id.desc()).first()
    if inc is not None:
        mins = int((datetime.utcnow() - inc.opened_at).total_seconds() // 60)
        lines.append(f"🚨 Sự cố #{inc.id} đang mở {mins} phút · "
                     + (f"đã xác nhận bởi {escape(inc.acked_by or '')}" if inc.acked_at else "<b>chưa ai xác nhận</b>"))
    return "\n".join(lines)


def status_message(db) -> str:
    return f"📍 <b>TÌNH HÌNH CHÙA CẦU</b>\n🕒 {_stamp()}\n\n{status_block(db)}\n\n{FOOT}"


def event_message(db, event_type: str, count=None, camera_id=None, incident=None) -> str:
    """Tin cho su kien camera gui len. Tra ve None neu khong co mau rieng (dung tin goc)."""
    cfg = get_config(db)
    cap = cfg.alert_threshold
    cam = f"chân cầu {camera_id}" if camera_id else "camera"
    if event_type == "WARNING":
        head = "🟡 <b>CẢNH BÁO VÀNG · CẦU SẮP ĐẦY</b>"
        action = "👉 Nhắc khách đi chậm, không dừng lại giữa cầu; chuẩn bị điều tiết ở hai đầu cầu."
        level = "WARNING"
    elif event_type == "CRITICAL_ALERT":
        if incident is not None and (incident.alert_count or 1) > 1:
            mins = int((datetime.utcnow() - incident.opened_at).total_seconds() // 60)
            head = (f"🔴⏰ <b>NHẮC LẠI · VẪN QUÁ TẢI</b> (lần {incident.alert_count})\n"
                    f"Sự cố #{incident.id} đã kéo dài {mins} phút · cao nhất {incident.peak_count} người")
        else:
            head = (f"🔴🔴 <b>CẢNH BÁO ĐỎ · QUÁ TẢI</b>\n"
                    f"Vượt sức chứa {cap} người liên tục 15 giây"
                    + (f" · Sự cố #{incident.id}" if incident is not None else ""))
        acked = incident is not None and incident.acked_at is not None
        action = ("👉 <b>Tạm dừng cho khách lên cầu</b>, hướng dẫn khách chờ ở đầu cầu."
                  + ("" if acked else "\nBấm <b>✅ Đã xử lý</b> bên dưới khi đã có người ra điều tiết."))
        level = "CRITICAL"
    elif event_type == "GROUP_DETECTED":
        head = f"👥 <b>ĐOÀN KHÁCH LỚN</b> · khoảng <b>{count or '?'}</b> người đang đến {cam}"
        action = "👉 Chuẩn bị điều tiết, kiểm tra vé đoàn, chia nhóm lên cầu."
        level = None
    elif event_type == "CAMERA_LOST":
        head = f"📷❌ <b>MẤT TÍN HIỆU CAMERA {cam.upper()}</b>"
        action = "👉 Chuyển sang <b>đếm và điều tiết thủ công</b> ở đầu cầu này. Camera tự kết nối lại khi có tín hiệu."
        level = None
    elif event_type == "CAMERA_RESTORED":
        head = f"📷✅ <b>CAMERA {cam.upper()} HOẠT ĐỘNG LẠI</b>"
        action = "Hệ thống đếm tự động trở lại bình thường."
        level = None
    else:
        return None
    return f"{head}\n🕒 {_stamp()}\n\n{status_block(db, level)}\n\n{action}\n\n{FOOT}"


def incident_closed_message(db, inc, reason: str, by: str) -> str:
    dur = int(((inc.closed_at or datetime.utcnow()) - inc.opened_at).total_seconds())
    handled = (f"✅ Xác nhận bởi <b>{escape(inc.acked_by or '')}</b> sau {int((inc.acked_at - inc.opened_at).total_seconds())} giây"
               if inc.acked_at else "⚠️ Không có người xác nhận")
    how = "tự động (≤ ngưỡng Vàng liên tục 15 giây)" if reason == "auto" else f"thủ công bởi {escape(by)}"
    return (f"✅ <b>HẾT QUÁ TẢI · SỰ CỐ #{inc.id} ĐÃ ĐÓNG</b>\n🕒 {_stamp()}\n\n"
            f"⏱ Bắt đầu {to_local(inc.opened_at):%H:%M} · kéo dài <b>{dur // 60} phút {dur % 60} giây</b>\n"
            f"👥 Cao nhất <b>{inc.peak_count}</b> người · {inc.alert_count} lần cảnh báo\n"
            f"{handled}\n🔒 Đóng {how}\n\n{status_block(db)}\n\n"
            "👉 Có thể cho khách lên cầu trở lại.\n\n" + FOOT)


def today_message(db) -> str:
    from .routers.alerts import Incident
    from .routers.bridge import _get_bridge_state
    from .routers.insights import live
    from .timeutil import local_day_range_utc

    now = local_now()
    st = _get_bridge_state(db)
    lv = live(db)
    s, e = local_day_range_utc(now, now)
    inc = db.query(Incident).filter(Incident.opened_at >= s, Incident.opened_at < e).all()
    peak = (db.query(OccupancySnapshot.count).filter(OccupancySnapshot.timestamp >= s, OccupancySnapshot.timestamp < e)
            .order_by(OccupancySnapshot.count.desc()).first())
    hours = [f for f in lv["forecast"] if f["actual"]] if lv["forecast"] else []
    busiest = max(hours, key=lambda f: f["actual"]) if hours else None
    lines = [f"📊 <b>HÔM NAY TẠI CHÙA CẦU</b> · {now:%d/%m/%Y}", f"🕒 Tính đến {now:%H:%M}", "",
             f"🎫 Lượt vào cầu: <b>{st.dem}</b>"]
    if lv["today_vs_usual"] is not None:
        pct = round((lv["today_vs_usual"] - 1) * 100)
        lines.append(f"{'📈' if pct >= 0 else '📉'} So với ngày thường cùng giờ: <b>{pct:+d}%</b>")
    if busiest:
        lines.append(f"⏰ Giờ đông nhất đến giờ: <b>{busiest['hour']}h</b> ({busiest['actual']} lượt)")
    if peak:
        lines.append(f"👥 Cao nhất cùng lúc: <b>{peak[0]}</b> người")
    lines.append(f"🚨 Sự cố quá tải: <b>{len(inc)}</b>"
                 + (f" · {sum(1 for i in inc if i.closed_at is None)} đang mở" if inc else ""))
    if lv["expected_rest_of_day"]:
        lines.append(f"🔮 Dự báo thêm khoảng <b>{lv['expected_rest_of_day']:.0f}</b> lượt đến cuối ngày"
                     + (f", cao điểm dự kiến <b>{lv['expected_peak']['hour']}h</b>" if lv["expected_peak"] else ""))
    return "\n".join(lines) + f"\n\n{status_block(db)}\n\n{FOOT}"


def morning_message(db) -> str:
    from .routers.bridge import BridgeCrossing, cameras
    from .routers.insights import live
    from .timeutil import local_day_range_utc

    cfg = get_config(db)
    now = local_now()
    y = now - timedelta(days=1)
    s, e = local_day_range_utc(y, y)
    y_in = db.query(BridgeCrossing).filter(BridgeCrossing.timestamp >= s, BridgeCrossing.timestamp < e,
                                           BridgeCrossing.direction == "in").count()
    lv = live(db)
    cams = cameras(db)
    off = [c for c in cams if not c["online"]]
    lines = ["☀️ <b>CHÀO BUỔI SÁNG · CHÙA CẦU MỞ CỬA</b>", f"📅 {now:%d/%m/%Y} · giờ hoạt động {cfg.open_time}–{cfg.close_time}", "",
             f"📒 Hôm qua: <b>{y_in}</b> lượt vào cầu"]
    if lv["forecast"]:
        total = sum(f["expected"] for f in lv["forecast"])
        lines.append(f"🔮 Dự báo hôm nay: khoảng <b>{total:.0f}</b> lượt"
                     + (f", cao điểm dự kiến <b>{lv['expected_peak']['hour']}h</b>" if lv["expected_peak"] else ""))
    else:
        lines.append("🔮 Chưa đủ dữ liệu các tuần trước để dự báo.")
    lines.append(f"⚖️ Sức chứa: <b>{cfg.alert_threshold}</b> người · Vàng từ {max(1, round(cfg.alert_threshold * 0.75))}")
    lines.append("📷 " + " · ".join(f"Camera {c['camera_id']} {'✅ đang chạy' if c['online'] else '❌ chưa chạy'}" for c in cams))
    if off:
        lines.append("⚠️ <b>Hãy bật camera " + ", ".join(str(c["camera_id"]) for c in off) + "</b> trước khi đón khách.")
    lines.append("\nGõ /tinhhinh để xem tình hình bất cứ lúc nào.")
    return "\n".join(lines) + f"\n\n{FOOT}"


def daily_report_message(r: dict, tickets_missing: bool = False) -> str:
    k = r["kpis"]

    def pct(v):
        return "–" if v is None else f"{v:.0f}%"

    d = r["date_to"]
    lines = [f"📋 <b>BÁO CÁO NGÀY {d[8:]}/{d[5:7]}/{d[:4]}</b>", "",
             f"🎫 Lượt vào cầu: <b>{r['total_entries']}</b> · qua mặt tiền: {r['facade_passes']}",
             f"👥 Đông nhất: <b>{r['peak_count']}</b> người cùng lúc"
             + (f" · giờ nhiều khách nhất: <b>{r['peak_hour']}h</b>" if r["peak_hour"] is not None else ""),
             f"⏱ Phút vượt sức chứa: <b>{k['o1_minutes_over']}</b>",
             f"🚨 Sự cố quá tải: <b>{r['incidents']}</b> · xử lý trong 3 phút: {pct(k['o4_handled_within_3min_pct'])}"
             f" · báo sai: {pct(k['o5_false_alarm_pct'])}",
             f"🟡 Cảnh báo Vàng: {r['alerts']['WARNING']} · 👥 đoàn khách lớn: {r['alerts']['GROUP_DETECTED']}"]
    dem = r.get("demographics") or {}
    if dem.get("identified"):
        g, o = dem.get("gender", {}), dem.get("origin", {})
        lines.append(f"🧑‍🤝‍🧑 Nam {g.get('Man', 0)} · Nữ {g.get('Woman', 0)} · "
                     f"trong nước/châu Á {o.get('Trong nuoc', 0)} · quốc tế {o.get('Nuoc ngoai', 0)}")
    if k["o8_gap_rate_pct"] is not None:
        lines.append(f"🎟 Chênh lệch vé: <b>{k['o8_gap_rate_pct']}%</b>")
    elif tickets_missing:
        lines.append("⚠️ <b>Chưa nhập số cuống vé hôm nay</b> → chưa tính được chênh lệch vé. "
                     "Nhập ở trang Đối chiếu vé.")
    lines.append("\n📎 Báo cáo đầy đủ trong tệp PDF đính kèm.")
    return "\n".join(lines) + f"\n\n{FOOT}"


WEEKDAY_VI = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ nhật"]


def _change(cur, prev) -> str:
    if not prev:
        return "" if not cur else " (tuần trước chưa có số liệu)"
    pct = round((cur - prev) / prev * 100)
    return f" ({'📈' if pct > 0 else '📉' if pct < 0 else '➖'} {pct:+d}% so với tuần trước: {prev})"


def weekly_message(r: dict, prev: dict) -> str:
    """Bao cao tuan: tong luot, so voi tuan truoc, ngay dong nhat / vang nhat, gio cao diem, su co, KPI."""
    from datetime import datetime as _dt
    k, pk = r["kpis"], prev["kpis"]

    def d(s):
        return f"{s[8:]}/{s[5:7]}"

    def pct(v):
        return "–" if v is None else f"{v:.0f}%"

    days = [x for x in r["by_day"]]
    busiest = max(days, key=lambda x: x["entries"]) if days else None
    quiet = min(days, key=lambda x: x["entries"]) if days else None
    wd = (lambda s: WEEKDAY_VI[_dt.strptime(s, "%Y-%m-%d").weekday()])
    avg = round(r["total_entries"] / max(1, len(days)))
    lines = [f"📅 <b>BÁO CÁO TUẦN {d(r['date_from'])} – {d(r['date_to'])}/{r['date_to'][:4]}</b>", "",
             f"🎫 Tổng lượt vào cầu: <b>{r['total_entries']}</b>{_change(r['total_entries'], prev['total_entries'])}",
             f"📊 Trung bình <b>{avg}</b> lượt/ngày"]
    if busiest and busiest["entries"]:
        lines.append(f"🏆 Đông nhất: <b>{wd(busiest['date'])} {d(busiest['date'])}</b> · {busiest['entries']} lượt")
        lines.append(f"🌙 Vắng nhất: {wd(quiet['date'])} {d(quiet['date'])} · {quiet['entries']} lượt")
        short = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"]
        bars = "\n".join(f"<code>{short[_dt.strptime(x['date'], '%Y-%m-%d').weekday()]} {d(x['date'])} "
                         f"{'▇' * max(0, round(x['entries'] / max(1, busiest['entries']) * 12)):<12} {x['entries']}</code>"
                         for x in days)
        lines.append(bars)
    if r["peak_hour"] is not None:
        lines.append(f"⏰ Giờ cao điểm cả tuần: <b>{r['peak_hour']}h</b>"
                     + (f" · đông nhất cùng lúc <b>{r['peak_count']}</b> người" if r["peak_count"] else ""))
    lines += [
        f"🚨 Sự cố quá tải: <b>{r['incidents']}</b>{_change(r['incidents'], prev['incidents']) if prev['incidents'] or r['incidents'] else ''}",
        f"⏱ Phút vượt sức chứa: <b>{k['o1_minutes_over']}</b> (tuần trước {pk['o1_minutes_over']})",
        f"✅ Xử lý trong 3 phút: {pct(k['o4_handled_within_3min_pct'])} · báo sai: {pct(k['o5_false_alarm_pct'])}",
        f"🟡 Cảnh báo Vàng: {r['alerts']['WARNING']} · 👥 đoàn khách lớn: {r['alerts']['GROUP_DETECTED']}"
        f" · 📷 mất tín hiệu: {r['alerts']['CAMERA_LOST']}",
    ]
    dem = r.get("demographics") or {}
    if dem.get("identified"):
        g, o, n = dem.get("gender", {}), dem.get("origin", {}), dem["identified"]
        lines.append(f"🧑‍🤝‍🧑 Nam {round(g.get('Man', 0) / n * 100)}% · Nữ {round(g.get('Woman', 0) / n * 100)}% · "
                     f"quốc tế {round(o.get('Nuoc ngoai', 0) / n * 100)}%")
    if k["o8_gap_rate_pct"] is not None:
        lines.append(f"🎟 Chênh lệch vé: <b>{k['o8_gap_rate_pct']}%</b>")
    lines.append("\n📎 Báo cáo đầy đủ trong tệp PDF đính kèm.")
    return "\n".join(lines) + f"\n\n{FOOT}"
