from abc import ABC, abstractmethod

from src.domain.models import Job


class JobCollector(ABC):
    """Contract for job listing collectors."""

    @abstractmethod
    def fetch_jobs(self) -> list[Job]:
        """Fetch job listings from an external source."""
        raise NotImplementedError
