"""
backend/database.py  (MODULE M2 - Nen tang backend, phu trach: Minh)
----------------------------------------------------------------------
Ket noi CSDL dung chung cho moi router. Tach ra tu api_server.py cu.

- Mac dinh dung SQLite: file backend/smartcau.db (tu tao khi chay lan dau,
  KHONG dua len GitHub - da co trong .gitignore).
- Muon doi sang PostgreSQL/MySQL: chi can set bien moi truong
  SMARTCAU_DATABASE_URL, code cac router giu nguyen (loi ich cua ORM).
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_DB = f"sqlite:///{os.path.join(_THIS_DIR, 'smartcau.db')}"
DATABASE_URL = os.environ.get("SMARTCAU_DATABASE_URL", _DEFAULT_DB)

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """Dependency cua FastAPI: mo 1 phien lam viec CSDL cho moi request va
    TU DONG dong lai sau khi xong (ke ca khi loi). Dung trong router:

        def my_endpoint(db: Session = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
