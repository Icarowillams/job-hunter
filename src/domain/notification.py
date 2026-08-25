from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from src.domain.enums import NotificationChannel, NotificationStatus


class Notification(BaseModel):
    id: str
    job_id: str
    title: str
    message: str
    score: int
    classification: str
    channel: NotificationChannel
    status: NotificationStatus = NotificationStatus.PENDING
    created_at: datetime
    sent_at: Optional[datetime] = None
    error: Optional[str] = None
    attempts: int = 0
    last_attempt_at: Optional[datetime] = None
