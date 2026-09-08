from datetime import datetime

from src.domain.enums import NotificationChannel, NotificationStatus
from src.domain.notification import Notification


class NotificationRepository:
    def __init__(self, database):
        self.database = database

    def save(self, notification: Notification) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO notification (
                    id,
                    job_id,
                    title,
                    message,
                    score,
                    classification,
                    channel,
                    status,
                    created_at,
                    sent_at,
                    error,
                    attempts,
                    last_attempt_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id, channel)
                DO UPDATE SET
                    title = excluded.title,
                    message = excluded.message,
                    score = excluded.score,
                    classification = excluded.classification,
                    status = excluded.status,
                    sent_at = excluded.sent_at,
                    error = excluded.error,
                    attempts = excluded.attempts,
                    last_attempt_at = excluded.last_attempt_at
                """,
                (
                    notification.id,
                    notification.job_id,
                    notification.title,
                    notification.message,
                    notification.score,
                    notification.classification,
                    notification.channel.value,
                    notification.status.value,
                    notification.created_at.isoformat(),
                    (
                        notification.sent_at.isoformat()
                        if notification.sent_at is not None
                        else None
                    ),
                    notification.error,
                    notification.attempts,
                    (
                        notification.last_attempt_at.isoformat()
                        if notification.last_attempt_at is not None
                        else None
                    ),
                ),
            )

    def get_by_job_and_channel(
        self,
        job_id: str,
        channel: NotificationChannel,
    ) -> Notification | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    job_id,
                    title,
                    message,
                    score,
                    classification,
                    channel,
                    status,
                    created_at,
                    sent_at,
                    error,
                    attempts,
                    last_attempt_at
                FROM notification
                WHERE job_id = ?
                  AND channel = ?
                """,
                (
                    job_id,
                    channel.value,
                ),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if value is None:
            return None

        return datetime.fromisoformat(value)

    @classmethod
    def _row_to_model(cls, row) -> Notification:
        return Notification(
            id=row[0],
            job_id=row[1],
            title=row[2],
            message=row[3],
            score=row[4],
            classification=row[5],
            channel=NotificationChannel(row[6]),
            status=NotificationStatus(row[7]),
            created_at=cls._parse_datetime(row[8]),
            sent_at=cls._parse_datetime(row[9]),
            error=row[10],
            attempts=row[11],
            last_attempt_at=cls._parse_datetime(row[12]),
        )
