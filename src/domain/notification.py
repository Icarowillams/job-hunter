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

    def mark_retrying(
        self,
        attempted_at: datetime,
        error: str,
    ) -> None:
        self.status = NotificationStatus.RETRYING
        self.attempts += 1
        self.last_attempt_at = attempted_at
        self.error = error

    def mark_sent(
        self,
        sent_at: datetime,
        attempts: int,
    ) -> None:
        self.status = NotificationStatus.SENT
        self.sent_at = sent_at
        self.attempts = attempts
        self.last_attempt_at = sent_at
        self.error = None

    def mark_failed(
        self,
        failed_at: datetime,
        attempts: int,
        error: str,
    ) -> None:
        self.status = NotificationStatus.FAILED
        self.attempts = attempts
        self.last_attempt_at = failed_at
        self.error = error
