from types import SimpleNamespace

from src.infrastructure.email_notifier import EmailNotifier


class FakeSMTP:
    def __init__(self):
        self.calls = []

    def send_message(self, message):
        self.calls.append(message)


def test_email_notifier_sends_analysis_by_email():
    smtp = FakeSMTP()

    notifier = EmailNotifier(
        smtp_client=smtp,
        sender="hunter@example.com",
        recipient="user@example.com",
    )

    analysis = SimpleNamespace(
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        strengths=["Python", "Backend"],
        gaps=["Docker"],
        hard_blocker=False,
        classification="PRIORITY",
    )

    job = SimpleNamespace(
        id="job-1",
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/job-1",
        description="Python backend developer.",
    )

    notifier.send_notification(analysis, job)

    assert len(smtp.calls) == 1

    message = smtp.calls[0]

    assert message["From"] == "hunter@example.com"
    assert message["To"] == "user@example.com"
    assert "Python Developer" in message["Subject"]
    assert "Acme" in message.get_body().get_content()
    assert "85" in message.get_body().get_content()
    assert "Python" in message.get_body().get_content()
    assert "Docker" in message.get_body().get_content()
    assert "https://example.com/job-1" in message.get_body().get_content()
from types import SimpleNamespace

from src.infrastructure.email_notifier import EmailNotifier
from src.infrastructure.smtp_client import SMTPClient


def test_email_notifier_accepts_smtp_client():
    smtp_client = SMTPClient(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secret",
    )

    notifier = EmailNotifier(
        smtp_client=smtp_client,
        sender="user@example.com",
        recipient="recipient@example.com",
    )

    assert notifier.smtp_client is smtp_client
from types import SimpleNamespace

from src.application.retry.retry_policy import RetryPolicy
from src.infrastructure.email_notifier import EmailNotifier


class FlakySMTP:
    def __init__(self):
        self.attempts = 0

    def send_message(self, message):
        self.attempts += 1

        if self.attempts < 3:
            raise RuntimeError("SMTP temporarily unavailable")


def test_email_notifier_uses_retry_policy():
    smtp = FlakySMTP()

    retry_policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=0,
        backoff_multiplier=1,
    )

    notifier = EmailNotifier(
        smtp_client=smtp,
        sender="hunter@example.com",
        recipient="user@example.com",
        retry_policy=retry_policy,
    )

    analysis = SimpleNamespace(
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        strengths=["Python"],
        gaps=["Docker"],
        hard_blocker=False,
        classification="PRIORITY",
    )

    job = SimpleNamespace(
        id="job-retry",
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/job-retry",
        description="Python backend developer.",
    )

    notifier.send_notification(analysis, job)

    assert smtp.attempts == 3
from datetime import datetime, timezone
from types import SimpleNamespace

from src.domain.enums import NotificationChannel, NotificationStatus
from src.infrastructure.email_notifier import EmailNotifier


class FakeSMTP:
    def __init__(self):
        self.calls = []

    def send_message(self, message):
        self.calls.append(message)


class FakeNotificationRepository:
    def __init__(self):
        self.notifications = {}
        self.history = []

    def save(self, notification):
        self.notifications[notification.job_id] = notification
        self.history.append(
            (
                notification.job_id,
                notification.status,
                notification.attempts,
                notification.error,
            )
        )


def test_email_notifier_persists_sent_notification():
    smtp = FakeSMTP()
    repository = FakeNotificationRepository()

    notifier = EmailNotifier(
        smtp_client=smtp,
        sender="hunter@example.com",
        recipient="user@example.com",
        notification_repository=repository,
    )

    analysis = SimpleNamespace(
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        strengths=["Python"],
        gaps=["Docker"],
        hard_blocker=False,
        classification="PRIORITY",
    )

    job = SimpleNamespace(
        id="job-persist",
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/job-persist",
        description="Python backend developer.",
    )

    notifier.send_notification(analysis, job)

    assert len(repository.notifications) == 1

    notification = repository.notifications["job-persist"]

    assert notification.job_id == "job-persist"
    assert notification.channel == NotificationChannel.EMAIL
    assert notification.status == NotificationStatus.SENT
    assert notification.attempts == 1
    assert notification.sent_at is not None
    assert notification.error is None

def test_email_notifier_persists_real_retry_attempt_count():
    smtp = FlakySMTP()
    repository = FakeNotificationRepository()

    retry_policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=0,
        backoff_multiplier=1,
    )

    notifier = EmailNotifier(
        smtp_client=smtp,
        sender="hunter@example.com",
        recipient="user@example.com",
        retry_policy=retry_policy,
        notification_repository=repository,
    )

    analysis = SimpleNamespace(
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        strengths=["Python"],
        gaps=["Docker"],
        hard_blocker=False,
        classification="PRIORITY",
    )

    job = SimpleNamespace(
        id="job-retry-persist",
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/job-retry-persist",
        description="Python backend developer.",
    )

    notifier.send_notification(analysis, job)

    notification = repository.notifications["job-retry-persist"]

    assert notification.status == NotificationStatus.SENT
    assert notification.attempts == 3

class AlwaysFailSMTP:
    def __init__(self):
        self.attempts = 0

    def send_message(self, message):
        self.attempts += 1
        raise RuntimeError("SMTP authentication failed")


def test_email_notifier_persists_failed_notification_after_retries():
    smtp = AlwaysFailSMTP()
    repository = FakeNotificationRepository()

    retry_policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=0,
        backoff_multiplier=1,
    )

    notifier = EmailNotifier(
        smtp_client=smtp,
        sender="hunter@example.com",
        recipient="user@example.com",
        retry_policy=retry_policy,
        notification_repository=repository,
    )

    analysis = SimpleNamespace(
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        strengths=["Python"],
        gaps=["Docker"],
        hard_blocker=False,
        classification="PRIORITY",
    )

    job = SimpleNamespace(
        id="job-failed",
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/job-failed",
        description="Python backend developer.",
    )

    try:
        notifier.send_notification(analysis, job)
    except RuntimeError:
        pass

    notification = repository.notifications["job-failed"]

    assert smtp.attempts == 3
    assert notification.status == NotificationStatus.FAILED
    assert notification.attempts == 3
    assert notification.last_attempt_at is not None
    assert notification.error == "SMTP authentication failed"
from types import SimpleNamespace

from src.application.retry.retry_policy import RetryPolicy
from src.infrastructure.email_notifier import EmailNotifier
from src.domain.enums import NotificationStatus


class FlakySMTP:
    def __init__(self):
        self.attempts = 0

    def send_message(self, message):
        self.attempts += 1

        if self.attempts < 3:
            raise RuntimeError("SMTP temporarily unavailable")


class FakeNotificationRepository:
    def __init__(self):
        self.notifications = {}
        self.history = []

    def save(self, notification):
        self.notifications[notification.job_id] = notification
        self.history.append(
            (
                notification.job_id,
                notification.status,
                notification.attempts,
                notification.error,
            )
        )


def test_email_notifier_persists_retrying_status_during_retries():
    smtp = FlakySMTP()
    repository = FakeNotificationRepository()

    retry_policy = RetryPolicy(
        max_attempts=3,
        delay_seconds=0,
        backoff_multiplier=1,
    )

    notifier = EmailNotifier(
        smtp_client=smtp,
        sender="hunter@example.com",
        recipient="user@example.com",
        retry_policy=retry_policy,
        notification_repository=repository,
    )

    analysis = SimpleNamespace(
        compatibility_score=85,
        priority_score=90,
        confidence_score=95,
        strengths=["Python"],
        gaps=["Docker"],
        hard_blocker=False,
        classification="PRIORITY",
    )

    job = SimpleNamespace(
        id="job-retrying",
        title="Python Developer",
        company="Acme",
        location="Remote",
        url="https://example.com/job-retrying",
        description="Python backend developer.",
    )

    notifier.send_notification(analysis, job)

    notification = repository.notifications["job-retrying"]

    assert smtp.attempts == 3
    assert notification.status == NotificationStatus.SENT
    assert notification.attempts == 3

    statuses = [status for _, status, _, _ in repository.history]

    assert statuses[0] == NotificationStatus.PENDING
    assert NotificationStatus.RETRYING in statuses
    assert statuses[-1] == NotificationStatus.SENT
