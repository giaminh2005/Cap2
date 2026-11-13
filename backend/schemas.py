"""
backend/schemas.py  (MODULE M2 - Nen tang backend, phu trach: Minh)
---------------------------------------------------------------------
Khuon du lieu (Pydantic) cho cac API dung chung. Schema rieng cua 1 module
dat ngay trong file router cua module do.
"""

from typing import Optional

from pydantic import BaseModel


class VisitEventIn(BaseModel):
    track_id: Optional[int] = None
    age: Optional[int] = None
    age_range: Optional[str] = None
    gender: Optional[str] = None
    origin: Optional[str] = None          # "Trong nuoc" | "Nuoc ngoai" | None
    camera_id: Optional[int] = None


class OccupancyIn(BaseModel):
    count: int
    status: str


class SystemEventIn(BaseModel):
    event_type: str
    count: Optional[int] = None
    message: Optional[str] = None
    camera_id: Optional[int] = None

