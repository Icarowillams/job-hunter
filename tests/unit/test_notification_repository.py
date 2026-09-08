from datetime import datetime

import pytest

from src.domain.enums import NotificationChannel, NotificationStatus
from src.domain.models import Job
from src.domain.notification import Notification
from src.infrastructure.database import Database
from src.infrastructure.notification_repository import NotificationRepository


@pytest.fixture
def database(tmp_path):
    return Database(str(tmp_path / "test.db"))


@pytest.fixture
def repository(database):
    return NotificationRepository(database)


@pytest.fixture
def job(database):
    created_at = datetime(2026, 9, 3, 10, 0, 0)

    job = Job(
        id="job-1",
        external_id="external-1",
        source="test",
        title="Python Developer",
        company="Test Company",
        description="Python development position.",
        location="Sao Paulo, SP",
        work_mode="remote",
        seniority="junior",
        created_at=created_at,
    )

    with database.connect() as conn:
        conn.execute(
            """
            INSERT INTO job (
                id,
                external_id,
                source,
                title,
                company,
                description,
                location,
                work_mode,
                seniority,
                published_at,
                discovered_at,
                updated_at,
                original_published_at,
                url,
                metadata,
                normalized_hash,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.external_id,
                job.source,
                job.title,
                job.company,
                job.description,
                job.location,
                job.work_mode,
                job.seniority,
                None,
                None,
                None,
                None,
                job.url,
                "{}",
                job.normalized_hash,
                job.created_at.isoformat(),
            ),
        )

    return job


@pytest.fixture
def notification(job):
    return Notification(
        id="notification-1",
        job_id=job.id,
        title="Nova vaga encontrada",
        message="Python Developer - Test Company",
        score=85,
        classification="PRIORITY",
        channel=NotificationChannel.TELEGRAM,
        status=NotificationStatus.PENDING,
        created_at=datetime(2026, 9, 3, 10, 30, 0),
    )


def test_save_notification(repository, notification):
    repository.save(notification)

    saved = repository.get_by_job_and_channel(
        notification.job_id,
        notification.channel,
    )

    assert saved is not None
    assert saved.id == notification.id
    assert saved.job_id == notification.job_id
    assert saved.title == notification.title
    assert saved.message == notification.message
    assert saved.score == notification.score
    assert saved.classification == notification.classification
    assert saved.channel == notification.channel
    assert saved.status == notification.status


def test_update_notification(repository, notification):
    repository.save(notification)

    notification.status = NotificationStatus.SENT
    notification.sent_at = datetime(2026, 9, 3, 10, 35, 0)
    notification.attempts = 1

    repository.save(notification)

    saved = repository.get_by_job_and_channel(
        notification.job_id,
        notification.channel,
    )

    assert saved is not None
    assert saved.status == NotificationStatus.SENT
    assert saved.sent_at == notification.sent_at
    assert saved.attempts == 1


def test_preserve_sent_at_when_updating(repository, notification):
    sent_at = datetime(2026, 9, 3, 10, 35, 0)

    notification.status = NotificationStatus.SENT
    notification.sent_at = sent_at
    repository.save(notification)

    notification.status = NotificationStatus.SENT
    notification.attempts = 2
    repository.save(notification)

    saved = repository.get_by_job_and_channel(
        notification.job_id,
        notification.channel,
    )

    assert saved is not None
    assert saved.sent_at == sent_at


def test_save_is_idempotent_by_job_and_channel(repository, notification):
    repository.save(notification)

    first = repository.get_by_job_and_channel(
        notification.job_id,
        notification.channel,
    )

    notification.id = "notification-2"
    notification.message = "Updated message"

    repository.save(notification)

    second = repository.get_by_job_and_channel(
        notification.job_id,
        notification.channel,
    )

    assert first is not None
    assert second is not None

    assert second.id == first.id
    assert second.message == "Updated message"


def test_different_channels_create_different_notifications(
    repository,
    notification,
):
    repository.save(notification)

    second = notification.model_copy(
        update={
            "id": "notification-2",
            "channel": NotificationChannel.CONSOLE,
        }
    )

    repository.save(second)

    telegram = repository.get_by_job_and_channel(
        notification.job_id,
        NotificationChannel.TELEGRAM,
    )

    console = repository.get_by_job_and_channel(
        notification.job_id,
        NotificationChannel.CONSOLE,
    )

    assert telegram is not None
    assert console is not None
    assert telegram.id != console.id
    assert telegram.channel == NotificationChannel.TELEGRAM
    assert console.channel == NotificationChannel.CONSOLE
