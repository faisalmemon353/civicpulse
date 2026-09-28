from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Category(str, Enum):
    water = "water"
    electricity = "electricity"
    sanitation = "sanitation"
    roads = "roads"
    streetlights = "streetlights"
    other = "other"


class Priority(str, Enum):
    high = "high"
    normal = "normal"
    low = "low"


class Status(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    rejected = "rejected"


class ComplaintCreate(BaseModel):
    text: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = None


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    location: str
    reporter_contact: str | None
    category: Category
    priority: Priority
    status: Status
    ai_summary: str | None
    triaged_by: str
    triage_latency_ms: int
    created_at: datetime
    updated_at: datetime


class StatusUpdate(BaseModel):
    status: Status
