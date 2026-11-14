"""
backend/daily_report.py  —  MODULE M4 · F5.2 Bao cao ngay TU DONG (FR-11, AC-07.1, O6)
=======================================================================================
Phu trach: HOAN.

Sau gio dong cua (cau hinh o trang "Nguong & gio hoat dong"), backend tu lap
bao cao ngay, luu vao CSDL va gui tin nhan tom tat + tep PDF cho danh sach
nguoi nhan canh bao (Telegram). Luong nen kiem tra moi phut:

    - Hom nay: da qua gio dong cua va chua co bao cao -> lap + gui.
    - Hom qua: chua co bao cao (vd may tat luc dong cua) va co du lieu -> lap bu.

Tat bang bien moi truong SMARTCAU_DISABLE_SCHEDULER=1 (vd khi chay test).
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta

from sqlalchemy import Column, DateTime, Integer, String, Text

from . import notify
from .database import Base, SessionLocal
from .models import OccupancySnapshot, get_config
from .timeutil import local_day_range_utc, local_now


class DailyReport(Base):
    __tablename__ = "daily_reports"
    id = Column(Integer, primary_key=True)
    date = Column(String, unique=True, index=True)     # YYYY-MM-DD gio dia phuong
    data = Column(Text)                                # JSON cua /reports/summary?period=day
    total_entries = Column(Integer, default=0)
    incidents = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    delivery = Column(String, nullable=True)           # tom tat ket qua gui


def _summary(db, day: datetime) -> dict:
    from .routers.reports import report_summary
    return report_summary(period="day", date=day.strftime("%Y-%m-%d"), db=db)


def summary_text(r: dict, tickets_missing: bool = False) -> str:
    from .messages import daily_report_message
    return daily_report_message(r, tickets_missing)


def _tickets_missing(db, date_s: str) -> bool:
    from .routers.tickets import TicketCount
    return db.query(TicketCount.id).filter(TicketCount.date == date_s).first() is None


_PDF_KEYS = ("by_day", "by_month", "by_hour", "time_slots", "demographics", "alerts", "kpis", "date_from", "date_to")


def pdf_of(rep: DailyReport, db=None) -> bytes:
    """PDF bao cao ngay. Ban luu trong CSDL thieu muc (lap tu phien ban cu, hoac du lieu mau)
    -> lap lai tu du lieu goc cua ngay do de khop mau PDF hien tai."""
    from .report_export import to_pdf
    try:
        data = json.loads(rep.data or "{}")
    except ValueError:
        data = {}
    if not all(k in data for k in _PDF_KEYS):
        day = datetime.strptime(rep.date, "%Y-%m-%d")
        if db is not None:
            data = _summary(db, day)
        else:
            with SessionLocal() as s:
                data = _summary(s, day)
    return to_pdf(data)


def _deliver(report_id: int, text: str, pdf: bytes, filename: str):
    from .routers.admin import active_recipients
    with SessionLocal() as db:
        recipients = active_recipients(db, "daily")
        results = notify.deliver(recipients, text)
        results += notify.deliver_document(recipients, filename, pdf, f"📎 Báo cáo ngày {filename[13:23]}")
        rep = db.query(DailyReport).filter(DailyReport.id == report_id).first()
        ok = sum(1 for x in results if x["status"] == "ok")
        rep.sent_at = datetime.utcnow()
        if not results:
            rep.delivery = "Không có người nhận (thêm ở trang Người nhận cảnh báo)"
        elif ok == 0:
            rep.delivery = f"Chưa gửi được: {results[0]['status']}"
        else:
            rep.delivery = f"Đã gửi {ok}/{len(results)} tin"
        db.commit()
    # Tu dong dong bo Google Sheets sau bao cao ngay (bat / tat o trang Google Sheets)
    from .sheets_auto import auto_sync_after_report
    res = auto_sync_after_report()
    if res:
        print(f"[google_sheets] {res}")
        with SessionLocal() as db:
            rep = db.query(DailyReport).filter(DailyReport.id == report_id).first()
            rep.delivery = f"{rep.delivery} · Google Sheets: {res}"
            db.commit()
            notify.deliver(active_recipients(db, "system"),
                           ("✅" if res.startswith("đã") else "⚠️") + f" <b>Google Sheets</b>: {res}.")


def generate(db, day: datetime, send: bool = True, sync_send: bool = False) -> DailyReport:
    """Lap (hoac lap lai) bao cao ngay `day` va gui cho nguoi nhan."""
    r = _summary(db, day)
    date_s = day.strftime("%Y-%m-%d")
    rep = db.query(DailyReport).filter(DailyReport.date == date_s).first()
    if rep is None:
        rep = DailyReport(date=date_s)
        db.add(rep)
    rep.data = json.dumps(r, ensure_ascii=False)
    rep.total_entries, rep.incidents = r["total_entries"], r["incidents"]
    rep.created_at = datetime.utcnow()
    db.commit()
    db.refresh(rep)
    if send:
        missing = r["total_entries"] > 0 and _tickets_missing(db, date_s)
        args = (rep.id, summary_text(r, missing), pdf_of(rep), f"bao_cao_ngay_{date_s}.pdf")
        if sync_send:
            _deliver(*args)
            db.refresh(rep)
        else:
            threading.Thread(target=_deliver, args=args, daemon=True).start()
    return rep


def _has_data(db, day: datetime) -> bool:
    from .routers.bridge import BridgeCrossing
    s, e = local_day_range_utc(day, day)
    return (db.query(BridgeCrossing.id).filter(BridgeCrossing.timestamp >= s, BridgeCrossing.timestamp < e).first()
            is not None or db.query(OccupancySnapshot.id).filter(OccupancySnapshot.timestamp >= s,
                                                                   OccupancySnapshot.timestamp < e).first() is not None)


def run_due(db, now_local: datetime = None, send: bool = True):
    """Lap cac bao cao den han. Tra ve danh sach ngay vua lap."""
    now_local = now_local or local_now()
    cfg = get_config(db)
    done = []
    today = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - timedelta(days=1)
    close_h, close_m = map(int, cfg.close_time.split(":"))
    exists = {d for (d,) in db.query(DailyReport.date).filter(
        DailyReport.date.in_([today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")])).all()}
    if yesterday.strftime("%Y-%m-%d") not in exists and _has_data(db, yesterday):
        generate(db, yesterday, send=send)
        done.append(yesterday.strftime("%Y-%m-%d"))
    open_h, open_m = map(int, cfg.open_time.split(":"))
    mins, open_min = now_local.hour * 60 + now_local.minute, open_h * 60 + open_m
    if send and open_min <= mins < min(open_min + 60, close_h * 60 + close_m) \
            and _once(db, "MORNING_BRIEF", today, now_local):     # ban tin dau ngay: trong 1 gio dau sau gio mo cua
        _send_morning(db)
        done.append("morning")
    # Nhac nhap so cuong ve 30 phut truoc gio dong cua (de bao cao ngay tinh duoc chenh lech ve)
    remind = datetime(2000, 1, 1, close_h, close_m) - timedelta(minutes=30)
    if send and (remind.hour, remind.minute) <= (now_local.hour, now_local.minute) < (close_h, close_m) \
            and _tickets_missing(db, today.strftime("%Y-%m-%d")) and _once(db, "TICKET_REMINDER", today, now_local):
        notify.deliver_async(_recipients(db, "ticket"), "🎟 <b>NHẮC NHẬP SỐ CUỐNG VÉ</b>\n"
                             f"Còn 30 phút nữa đóng cửa ({cfg.close_time}) mà chưa nhập số cuống vé hôm nay.\n"
                             "Nhập ở trang <b>Đối chiếu vé</b> để báo cáo ngày tính được chênh lệch vé.")
        done.append("ticket-reminder")
    # Bao cao tuan: sang thu Hai, tu gio mo cua (tuan truoc Thu 2 - CN, so voi tuan truoc nua)
    if send and now_local.weekday() == 0 and (now_local.hour, now_local.minute) >= (open_h, open_m) \
            and _once(db, "WEEKLY_REPORT", today, now_local):
        send_weekly(db, today)
        done.append("weekly")
    after_close = (now_local.hour, now_local.minute) >= (close_h, close_m)
    if after_close and today.strftime("%Y-%m-%d") not in exists:
        generate(db, today, send=send)
        done.append(today.strftime("%Y-%m-%d"))
    return done


def _recipients(db, topic=None):
    from .routers.admin import active_recipients
    return active_recipients(db, topic)


def _once(db, kind: str, today: datetime, now_local: datetime = None) -> bool:
    """True neu hom nay chua lam viec `kind` (ghi lai vao nhat ky su kien de khong lap sau khi khoi dong lai)."""
    from .models import SystemEvent
    from .timeutil import local_day_range_utc
    s, e = local_day_range_utc(today, today)
    if db.query(SystemEvent.id).filter(SystemEvent.event_type == kind, SystemEvent.timestamp >= s,
                                       SystemEvent.timestamp < e).first():
        return False
    from .timeutil import LOCAL_UTC_OFFSET
    db.add(SystemEvent(event_type=kind, message=f"Tự động: {kind}", timestamp=(now_local or local_now()) - LOCAL_UTC_OFFSET))
    db.commit()
    return True


def _send_morning(db):
    from .messages import morning_message
    from .routers.alerts import buttons
    notify.deliver_async(_recipients(db, "morning"), morning_message(db), buttons())


def weekly_summaries(db, ref_day: datetime):
    """(tuan vua qua, tuan truoc do). Tuan = Thu 2 -> Chu nhat, ket thuc truoc ngay ref_day."""
    from .routers.reports import report_summary
    last_sun = ref_day - timedelta(days=ref_day.weekday() + 1)
    cur = report_summary(period="week", date=last_sun.strftime("%Y-%m-%d"), db=db)
    prev = report_summary(period="week", date=(last_sun - timedelta(days=7)).strftime("%Y-%m-%d"), db=db)
    return cur, prev


def send_weekly(db, ref_day: datetime = None, sync_send: bool = False) -> dict:
    """Lap bao cao tuan + PDF, gui cho nguoi nhan chon 'Bao cao tuan'. Tra ve tom tat."""
    from .messages import weekly_message
    from .report_export import to_pdf
    ref_day = ref_day or local_now().replace(hour=0, minute=0, second=0, microsecond=0)
    cur, prev = weekly_summaries(db, ref_day)
    text, pdf = weekly_message(cur, prev), to_pdf(cur)
    name = f"bao_cao_tuan_{cur['date_from']}_{cur['date_to']}.pdf"
    recipients = _recipients(db, "weekly")

    def go():
        res = notify.deliver(recipients, text)
        res += notify.deliver_document(recipients, name, pdf, f"📎 Báo cáo tuần {cur['date_from'][8:]}/{cur['date_from'][5:7]}"
                                                              f" – {cur['date_to'][8:]}/{cur['date_to'][5:7]}")
        return res

    results = go() if sync_send else (threading.Thread(target=go, daemon=True).start() or [])
    return {"date_from": cur["date_from"], "date_to": cur["date_to"], "total_entries": cur["total_entries"],
            "prev_total_entries": prev["total_entries"], "recipients": len(recipients),
            "sent_ok": sum(1 for r in results if r["status"] == "ok")}


def start_scheduler(interval_sec: int = 60):
    if os.environ.get("SMARTCAU_DISABLE_SCHEDULER"):
        return None

    def loop():
        while True:
            try:
                with SessionLocal() as db:
                    made = run_due(db)
                    if made:
                        print(f"[daily_report] Đã lập báo cáo ngày: {', '.join(made)}")
            except Exception as e:  # khong de luong nen chet
                print(f"[daily_report] Lỗi: {e}")
            time.sleep(interval_sec)

    t = threading.Thread(target=loop, daemon=True, name="daily-report")
    t.start()
    return t
