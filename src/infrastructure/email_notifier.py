from email.message import EmailMessage
from datetime import datetime, timezone
from uuid import uuid4

from src.application.notification.notifier import Notifier
from src.application.retry.retry_policy import RetryExhaustedError, RetryPolicy
from src.domain.enums import NotificationChannel
from src.domain.models import Job, JobAnalysis
from src.domain.notification import Notification


class EmailNotifier(Notifier):
    """Send analyzed job notifications by email."""

    def __init__(
        self,
        smtp_client,
        sender: str,
        recipient: str,
        retry_policy: RetryPolicy | None = None,
        notification_repository=None,
    ):
        self.smtp_client = smtp_client
        self.sender = sender
        self.recipient = recipient
        self.retry_policy = retry_policy
        self.notification_repository = notification_repository

    def send_notification(self, analysis: JobAnalysis, job: Job) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = self.recipient
        message["Subject"] = f"[Job Hunter] {job.title} - {job.company}"
        message.set_content(self._build_body(analysis, job))

        if self.notification_repository is None:
            self._send(message)
            return

        notification = Notification(
            id=str(uuid4()),
            job_id=job.id,
            title=job.title,
            message=message.get_body().get_content(),
            score=analysis.compatibility_score,
            classification=analysis.classification,
            channel=NotificationChannel.EMAIL,
            created_at=datetime.now(timezone.utc),
        )

        self.notification_repository.save(notification)

        try:
            if self.retry_policy is None:
                self.smtp_client.send_message(message)
                attempts = 1
            else:
                retry_policy = RetryPolicy(
                    max_attempts=self.retry_policy.max_attempts,
                    delay_seconds=self.retry_policy.delay_seconds,
                    backoff_multiplier=self.retry_policy.backoff_multiplier,
                    wait=self.retry_policy.wait,
                    on_retry=lambda attempt, error: self._persist_retry(
                        notification,
                        attempt,
                        error,
                    ),
                )

                result = retry_policy.execute_with_attempts(
                    lambda: self.smtp_client.send_message(message)
                )
                attempts = result.attempts

        except Exception as exc:
            failed_at = datetime.now(timezone.utc)

            if isinstance(exc, RetryExhaustedError):
                attempts = exc.attempts
                error = str(exc.original_exception)
            else:
                attempts = 1
                error = str(exc)

            notification.mark_failed(
                failed_at=failed_at,
                attempts=attempts,
                error=error,
            )

            self.notification_repository.save(notification)

            raise

        sent_at = datetime.now(timezone.utc)

        notification.mark_sent(
            sent_at=sent_at,
            attempts=attempts,
        )

        self.notification_repository.save(notification)

    def _persist_retry(
        self,
        notification: Notification,
        attempt: int,
        error: Exception,
    ) -> None:
        notification.mark_retrying(
            attempted_at=datetime.now(timezone.utc),
            error=str(error),
        )
        notification.attempts = attempt

        if self.notification_repository is not None:
            self.notification_repository.save(notification)

    def _send(self, message: EmailMessage) -> None:
        if self.retry_policy is None:
            self.smtp_client.send_message(message)
            return

        self.retry_policy.execute(
            lambda: self.smtp_client.send_message(message)
        )

    @staticmethod
    def _build_body(analysis: JobAnalysis, job: Job) -> str:
        strengths = ", ".join(analysis.strengths) or "Nenhuma"
        gaps = ", ".join(analysis.gaps) or "Nenhuma"

        return (
            f"Nova vaga encontrada pelo Job Hunter.\n\n"
            f"Vaga: {job.title}\n"
            f"Empresa: {job.company}\n"
            f"Localização: {job.location}\n"
            f"Compatibilidade: {analysis.compatibility_score}\n"
            f"Prioridade: {analysis.priority_score}\n"
            f"Confiança: {analysis.confidence_score}\n"
            f"Classificação: {analysis.classification}\n"
            f"Hard blocker: {analysis.hard_blocker}\n\n"
            f"Pontos fortes: {strengths}\n"
            f"Lacunas: {gaps}\n\n"
            f"Descrição:\n{job.description}\n\n"
            f"Link: {job.url}\n"
        )
