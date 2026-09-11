from requests.exceptions import ConnectionError, HTTPError, Timeout

from src.domain.models import Job
from src.ingestion.collectors.job_collector import JobCollector


class FallbackJobCollector(JobCollector):
    """Uses a fallback collector for recoverable infrastructure failures."""

    RECOVERABLE_ERRORS = (
        Timeout,
        ConnectionError,
    )

    RECOVERABLE_HTTP_STATUS_CODES = {429}

    def __init__(self, primary: JobCollector, fallback: JobCollector):
        self.primary = primary
        self.fallback = fallback

    def fetch_jobs(self) -> list[Job]:
        try:
            return self.primary.fetch_jobs()
        except self.RECOVERABLE_ERRORS:
            return self.fallback.fetch_jobs()
        except HTTPError as exc:
            if self._is_recoverable_http_error(exc):
                return self.fallback.fetch_jobs()
            raise

    @classmethod
    def _is_recoverable_http_error(cls, error: HTTPError) -> bool:
        response = error.response
        if response is None:
            return False

        status_code = response.status_code

        return (
            status_code in cls.RECOVERABLE_HTTP_STATUS_CODES
            or 500 <= status_code <= 599
        )
