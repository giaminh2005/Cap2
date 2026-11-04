"""
backend/timeutil.py  (MODULE M2 - Nen tang) — gio dia phuong dung chung
=======================================================================
CSDL luu thoi gian theo UTC (datetime.utcnow). Moi phep "chot ngay", thong
ke theo gio/ngay va gio mo cua deu tinh theo gio Viet Nam (UTC+7, doi duoc
qua bien moi truong SMARTCAU_UTC_OFFSET_HOURS).
"""

import os
from datetime import datetime, timedelta

UTC_OFFSET_HOURS = float(os.environ.get("SMARTCAU_UTC_OFFSET_HOURS", "7"))
LOCAL_UTC_OFFSET = timedelta(hours=UTC_OFFSET_HOURS)


def utcnow() -> datetime:
    return datetime.utcnow()


def local_now() -> datetime:
    return datetime.utcnow() + LOCAL_UTC_OFFSET


def to_local(dt_utc: datetime) -> datetime:
    return dt_utc + LOCAL_UTC_OFFSET


def local_day_range_utc(day_from: datetime, day_to: datetime):
    """[00:00 ngay day_from, 00:00 ngay sau day_to) theo gio dia phuong -> UTC."""
    start = datetime(day_from.year, day_from.month, day_from.day) - LOCAL_UTC_OFFSET
    end = datetime(day_to.year, day_to.month, day_to.day) + timedelta(days=1) - LOCAL_UTC_OFFSET
    return start, end


def parse_day(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def iso(dt):
    return dt.isoformat() if dt else None
