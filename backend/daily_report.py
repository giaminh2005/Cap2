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


def summary_text(r: dict) -> str:
    k = r["kpis"]

    def pct(v):
        return "–" if v is None else f"{v:.0f}%"

    d = r["date_to"]
    return (f"[SmartCau AI] BÁO CÁO NGÀY {d[8:]}/{d[5:7]}/{d[:4]}\n"
            f"• Lượt vào cầu: {r['total_entries']} · lượt qua mặt tiền: {r['facade_passes']}\n"
            f"• Đông nhất: {r['peak_count']} người cùng lúc"
            + (f" · giờ nhiều khách nhất: {r['peak_hour']}h" if r["peak_hour"] is not None else "") + "\n"
            f"• Số phút vượt sức chứa (O1): {k['o1_minutes_over']}\n"
            f"• Sự cố quá tải: {r['incidents']} · xử lý trong 3 phút (O4): {pct(k['o4_handled_within_3min_pct'])}"
            f" · báo sai (O5): {pct(k['o5_false_alarm_pct'])}\n"
            f"• Cảnh báo Vàng: {r['alerts']['WARNING']} · đoàn khách lớn: {r['alerts']['GROUP_DETECTED']}"
            + (f"\n• Chênh lệch vé (O8): {k['o8_gap_rate_pct']}%" if k["o8_gap_rate_pct"] is not None else ""))


def pdf_of(rep: DailyReport) -> bytes:
    from .report_export import to_pdf
    return to_pdf(json.loads(rep.data))


def _deliver(report_id: int, text: str, pdf: bytes, filename: str):
    from .routers.admin import active_recipients
    with SessionLocal() as db:
        recipients = active_recipients(db)
        results = notify.deliver(recipients, text)
        results += notify.deliver_document(recipients, filename, pdf, f"Báo cáo ngày {filename[13:23]}")
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
        args = (rep.id, summary_text(r), pdf_of(rep), f"bao_cao_ngay_{date_s}.pdf")
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
    after_close = (now_local.hour, now_local.minute) >= (close_h, close_m)
    if after_close and today.strftime("%Y-%m-%d") not in exists:
        generate(db, today, send=send)
        done.append(today.strftime("%Y-%m-%d"))
    return done


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
