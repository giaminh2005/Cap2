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


def pdf_of(rep: DailyReport) -> bytes:
    from .report_export import to_pdf
    return to_pdf(json.loads(rep.data))


def _deliver(report_id: int, text: str, pdf: bytes, filename: str):
    from .routers.admin import active_recipients
    with SessionLocal() as db:
        recipients = active_recipients(db)
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
        notify.deliver_async(_recipients(db), "🎟 <b>NHẮC NHẬP SỐ CUỐNG VÉ</b>\n"
                             f"Còn 30 phút nữa đóng cửa ({cfg.close_time}) mà chưa nhập số cuống vé hôm nay.\n"
                             "Nhập ở trang <b>Đối chiếu vé</b> để báo cáo ngày tính được chênh lệch vé.")
        done.append("ticket-reminder")
    after_close = (now_local.hour, now_local.minute) >= (close_h, close_m)
    if after_close and today.strftime("%Y-%m-%d") not in exists:
        generate(db, today, send=send)
        done.append(today.strftime("%Y-%m-%d"))
    return done


def _recipients(db):
    from .routers.admin import active_recipients
    return active_recipients(db)


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
    notify.deliver_async(_recipients(db), morning_message(db), buttons())


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
