from datetime import datetime, timezone
from types import SimpleNamespace

from src.domain.enums import NotificationChannel, NotificationStatus
from src.domain.notification import Notification


def test_notification_can_track_delivery_state():
    notification = Notification(
        id="notification-1",
        job_id="job-1",
        title="Python Developer",
        message="Nova vaga encontrada.",
        score=85,
        classification="PRIORITY",
        channel=NotificationChannel.EMAIL,
        created_at=datetime.now(timezone.utc),
    )

    assert notification.status == NotificationStatus.PENDING
    assert notification.attempts == 0
    assert notification.sent_at is None
    assert notification.last_attempt_at is None
    assert notification.error is None

def test_notification_can_be_marked_as_sent():
    notification = Notification(
        id="notification-2",
        job_id="job-2",
        title="Backend Developer",
        message="Nova vaga encontrada.",
        score=90,
        classification="PRIORITY",
        channel=NotificationChannel.EMAIL,
        created_at=datetime.now(timezone.utc),
    )

    sent_at = datetime.now(timezone.utc)

    notification.status = NotificationStatus.SENT
    notification.sent_at = sent_at
    notification.attempts = 1
    notification.last_attempt_at = sent_at
    notification.error = None

    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at == sent_at
    assert notification.attempts == 1
    assert notification.last_attempt_at == sent_at
    assert notification.error is None

def test_notification_can_be_marked_as_retrying():
    notification = Notification(
        id="notification-3",
        job_id="job-3",
        title="Python Developer",
        message="Nova vaga encontrada.",
        score=80,
        classification="PRIORITY",
        channel=NotificationChannel.EMAIL,
        created_at=datetime.now(timezone.utc),
    )

    attempted_at = datetime.now(timezone.utc)

    notification.status = NotificationStatus.RETRYING
    notification.attempts = 1
    notification.last_attempt_at = attempted_at
    notification.error = "SMTP connection failed"

    assert notification.status == NotificationStatus.RETRYING
    assert notification.attempts == 1
    assert notification.last_attempt_at == attempted_at
    assert notification.error == "SMTP connection failed"

def test_notification_can_be_marked_as_failed():
    notification = Notification(
        id="notification-4",
        job_id="job-4",
        title="Backend Developer",
        message="Nova vaga encontrada.",
        score=75,
        classification="REVIEW",
        channel=NotificationChannel.EMAIL,
        created_at=datetime.now(timezone.utc),
    )

    failed_at = datetime.now(timezone.utc)

    notification.status = NotificationStatus.FAILED
    notification.attempts = 3
    notification.last_attempt_at = failed_at
    notification.error = "SMTP authentication failed"

    assert notification.status == NotificationStatus.FAILED
    assert notification.attempts == 3
    assert notification.last_attempt_at == failed_at
    assert notification.error == "SMTP authentication failed"

def test_notification_mark_retrying():
    notification = Notification(
        id="notification-5",
        job_id="job-5",
        title="Python Developer",
        message="Nova vaga encontrada.",
        score=80,
        classification="PRIORITY",
        channel=NotificationChannel.EMAIL,
        created_at=datetime.now(timezone.utc),
    )

    attempted_at = datetime.now(timezone.utc)

    notification.mark_retrying(
        attempted_at=attempted_at,
        error="SMTP connection failed",
    )

    assert notification.status == NotificationStatus.RETRYING
    assert notification.attempts == 1
    assert notification.last_attempt_at == attempted_at
    assert notification.error == "SMTP connection failed"


def test_notification_mark_sent():
    notification = Notification(
        id="notification-6",
        job_id="job-6",
        title="Backend Developer",
        message="Nova vaga encontrada.",
        score=90,
        classification="PRIORITY",
        channel=NotificationChannel.EMAIL,
        created_at=datetime.now(timezone.utc),
    )

    sent_at = datetime.now(timezone.utc)

    notification.mark_sent(
        sent_at=sent_at,
        attempts=1,
    )

    assert notification.status == NotificationStatus.SENT
    assert notification.sent_at == sent_at
    assert notification.attempts == 1
    assert notification.last_attempt_at == sent_at
    assert notification.error is None


def test_notification_mark_failed():
    notification = Notification(
        id="notification-7",
        job_id="job-7",
        title="Backend Developer",
        message="Nova vaga encontrada.",
        score=75,
        classification="REVIEW",
        channel=NotificationChannel.EMAIL,
        created_at=datetime.now(timezone.utc),
    )

    failed_at = datetime.now(timezone.utc)

    notification.mark_failed(
        failed_at=failed_at,
        attempts=3,
        error="SMTP authentication failed",
    )

    assert notification.status == NotificationStatus.FAILED
    assert notification.attempts == 3
    assert notification.last_attempt_at == failed_at
    assert notification.error == "SMTP authentication failed"
