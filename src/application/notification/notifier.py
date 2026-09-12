from abc import ABC, abstractmethod

from src.domain.models import Job, JobAnalysis


class Notifier(ABC):
    """Contract for job notification channels."""

    @abstractmethod
    def send_notification(
        self,
        analysis: JobAnalysis,
        job: Job,
    ) -> None:
        """Send a notification for an analyzed job."""
        raise NotImplementedError
