"""
tools/migrate_sqlite_to_pg.py
---------------------------------------------------------------------
Chuyen TOAN BO du lieu tu SQLite (backend/smartcau.db) sang PostgreSQL
tren Supabase.  Chay 1 lan duy nhat sau khi da:

  1. Cau hinh SMARTCAU_DATABASE_URL trong file .env (tro den Supabase).
  2. pip install -r requirements.txt  (can psycopg2-binary, python-dotenv).

Cach dung:
    cd <thu-muc-goc-du-an>
    python tools/migrate_sqlite_to_pg.py

Script se:
  - Doc .env de lay SMARTCAU_DATABASE_URL (PostgreSQL).
  - Mo file backend/smartcau.db (SQLite) bang engine rieng.
  - Import moi model ORM (ca trong models.py lan cac router) de
    Base.metadata chua day du schema.
  - Tao cac bang tren PostgreSQL (neu chua co).
  - Sap xep thu tu bang theo phu thuoc khoa ngoai (topological sort)
    roi copy tung bang: doc tu SQLite -> chen vao PostgreSQL.
  - In tien trinh chi tiet ra man hinh.

Luu y:
  - Script dung INSERT, khong xoa du lieu cu tren PG.  Neu muon chay
    lai tu dau, hay xoa (TRUNCATE) cac bang tren Supabase truoc.
  - Neu bang da co du lieu trung khoa chinh, script se bao loi va dung
    lai o bang do (du lieu cac bang truoc do da duoc commit).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# 0. Dam bao import duoc backend/  (them thu muc goc vao sys.path)
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

# Doc .env TRUOC khi import bat ky thu gi tu backend
from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# 1. Kiem tra dieu kien tien quyet
# ---------------------------------------------------------------------------
PG_URL = os.environ.get("SMARTCAU_DATABASE_URL", "")
if not PG_URL or PG_URL.startswith("sqlite"):
    print("❌  SMARTCAU_DATABASE_URL chua duoc cau hinh hoac dang tro ve SQLite.")
    print("    Hay kiem tra file .env o thu muc goc du an.")
    sys.exit(1)

SQLITE_PATH = _PROJECT_ROOT / "backend" / "smartcau.db"
if not SQLITE_PATH.exists():
    print(f"❌  Khong tim thay file SQLite: {SQLITE_PATH}")
    sys.exit(1)

SQLITE_URL = f"sqlite:///{SQLITE_PATH}"

print("=" * 68)
print("  SMARTCAU AI — Chuyen du lieu SQLite  ➜  PostgreSQL (Supabase)")
print("=" * 68)
print(f"  SQLite : {SQLITE_PATH}")
# An mat khau trong connection string khi in ra man hinh
_safe_pg = PG_URL
if "@" in _safe_pg:
    _pre, _post = _safe_pg.split("@", 1)
    _safe_pg = _pre.rsplit(":", 1)[0] + ":****@" + _post
print(f"  PG     : {_safe_pg}")
print()

# ---------------------------------------------------------------------------
# 2. Tao 2 engine: SQLite (chi doc) va PostgreSQL (ghi)
# ---------------------------------------------------------------------------
from sqlalchemy import create_engine, inspect, text, MetaData

engine_sqlite = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
engine_pg = create_engine(PG_URL)

# ---------------------------------------------------------------------------
# 3. Import tat ca model ORM de Base.metadata chua day du bang
#    (gom ca cac model nam trong routers/)
# ---------------------------------------------------------------------------
from backend.database import Base

# Models chinh
import backend.models  # noqa: F401

# Models nam trong cac router
from backend.routers import (  # noqa: F401
    accounts, admin, alerts, bridge, counting,
    demographics, display, insights, reports, tickets,
)

print(f"📋  Tong so bang ORM da dang ky: {len(Base.metadata.tables)}")
print(f"    {', '.join(Base.metadata.tables.keys())}")
print()

# ---------------------------------------------------------------------------
# 4. Tao schema tren PostgreSQL (neu chua co)
# ---------------------------------------------------------------------------
print("🔧  Tao / kiem tra schema tren PostgreSQL ...")
Base.metadata.create_all(bind=engine_pg)
print("    ✔ Schema san sang.\n")

# ---------------------------------------------------------------------------
# 5. Sap xep bang theo thu tu phu thuoc (topological sort) de INSERT
#    khong vi pham rang buoc khoa ngoai.
#    Base.metadata.sorted_tables da tra ve thu tu nay (cha truoc, con sau).
# ---------------------------------------------------------------------------
tables_ordered = Base.metadata.sorted_tables

# Loc chi nhung bang thuc su ton tai trong SQLite
insp_sqlite = inspect(engine_sqlite)
sqlite_tables = set(insp_sqlite.get_table_names())
tables_to_migrate = [t for t in tables_ordered if t.name in sqlite_tables]

print(f"📦  Bang co trong SQLite ({len(tables_to_migrate)}/{len(tables_ordered)}):")
for i, t in enumerate(tables_to_migrate, 1):
    print(f"    {i:>2}. {t.name}")
print()

if not tables_to_migrate:
    print("⚠️  Khong co bang nao trong SQLite de chuyen.  Ket thuc.")
    sys.exit(0)

# ---------------------------------------------------------------------------
# 6. Chuyen du lieu tung bang
# ---------------------------------------------------------------------------
total_rows = 0
t_start = time.perf_counter()

# Reflect metadata tu SQLite de doc du lieu bang cach trung lap (SELECT *)
meta_sqlite = MetaData()
meta_sqlite.reflect(bind=engine_sqlite)

for idx, table_orm in enumerate(tables_to_migrate, 1):
    tname = table_orm.name
    print(f"[{idx}/{len(tables_to_migrate)}] 📤  {tname} ", end="", flush=True)

    # Doc toan bo du lieu tu SQLite
    table_src = meta_sqlite.tables.get(tname)
    if table_src is None:
        print("— khong co trong SQLite (bo qua)")
        continue

    with engine_sqlite.connect() as conn_src:
        rows = conn_src.execute(table_src.select()).fetchall()
        columns = [c.name for c in table_src.columns]

    row_count = len(rows)
    if row_count == 0:
        print(f"— 0 dong (bang trong)")
        continue

    # Chuyen thanh danh sach dict
    data = [dict(zip(columns, row)) for row in rows]

    # Chen vao PostgreSQL theo tung batch (tranh qua tai bo nho voi bang lon)
    BATCH = 500
    inserted = 0
    with engine_pg.begin() as conn_pg:
        for start in range(0, row_count, BATCH):
            batch = data[start : start + BATCH]
            conn_pg.execute(table_orm.insert(), batch)
            inserted += len(batch)
            # In tien trinh moi 500 dong
            if row_count > BATCH:
                pct = inserted * 100 // row_count
                print(f"\r[{idx}/{len(tables_to_migrate)}] 📤  {tname}  "
                      f"{inserted:>7,}/{row_count:,} ({pct}%)", end="", flush=True)

    total_rows += row_count
    print(f"\r[{idx}/{len(tables_to_migrate)}] ✅  {tname}  "
          f"— {row_count:,} dong                    ")

# ---------------------------------------------------------------------------
# 7. Cap nhat SEQUENCE cua PostgreSQL (AUTO INCREMENT) de INSERT tiep
#    theo khong bi trung id.
# ---------------------------------------------------------------------------
print("\n🔄  Cap nhat SEQUENCE (auto-increment) tren PostgreSQL ...")
with engine_pg.begin() as conn_pg:
    for table_orm in tables_to_migrate:
        for col in table_orm.columns:
            if col.primary_key and col.autoincrement is not False:
                seq_name = f"{table_orm.name}_{col.name}_seq"
                try:
                    # Tim gia tri MAX hien tai
                    result = conn_pg.execute(
                        text(f'SELECT MAX("{col.name}") FROM "{table_orm.name}"')
                    ).scalar()
                    if result is not None:
                        conn_pg.execute(
                            text(f"SELECT setval('{seq_name}', :val, true)"),
                            {"val": result},
                        )
                        print(f"    ✔ {seq_name} → {result}")
                except Exception:
                    # Bang khong co sequence (vd: khoa chinh la String) → bo qua
                    pass

# ---------------------------------------------------------------------------
# 8. Tong ket
# ---------------------------------------------------------------------------
elapsed = time.perf_counter() - t_start
print()
print("=" * 68)
print(f"  🎉  HOAN TAT!  {total_rows:,} dong  |  "
      f"{len(tables_to_migrate)} bang  |  {elapsed:.1f} giay")
print("=" * 68)
print()
print("👉  Buoc tiep theo:")
print("    1. Kiem tra du lieu tren Supabase (Table Editor).")
print("    2. Dam bao SMARTCAU_DATABASE_URL trong .env tro dung PG.")
print("    3. Khoi dong lai backend:  uvicorn backend.main:app --reload")
