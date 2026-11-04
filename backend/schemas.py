"""
backend/schemas.py  (MODULE M2 - Nen tang backend, phu trach: Minh)
---------------------------------------------------------------------
Khuon du lieu (Pydantic) cho cac API DA CO. Schema cua API MOI dat ngay
trong file router cua module do (cung ly do nhu models.py).
"""

from typing import Optional

from pydantic import BaseModel


class VisitEventIn(BaseModel):
    track_id: Optional[int] = None
    age: Optional[int] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None


class OccupancyIn(BaseModel):
    count: int
    status: str


class SystemEventIn(BaseModel):
    event_type: str
    count: Optional[int] = None
    message: Optional[str] = None


class RegionStatIn(BaseModel):
    region: str


class ConfigIn(BaseModel):
    alert_threshold: int
