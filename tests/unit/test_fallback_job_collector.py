import pytest

from src.domain.models import Job
from src.ingestion.collectors.fallback_job_collector import (
    FallbackJobCollector,
)


class SuccessfulCollector:
    def __init__(self, jobs):
        self.jobs = jobs
        self.calls = 0

    def fetch_jobs(self):
        self.calls += 1
        return self.jobs


class FailingCollector:
    def __init__(self, error):
        self.error = error
        self.calls = 0

    def fetch_jobs(self):
        self.calls += 1
        raise self.error


def make_job(job_id="job-1"):
    return Job(
        id=job_id,
        external_id=None,
        source="test",
        title="Python Developer",
        company="Empresa",
        description="Desenvolvimento Python.",
    )


def test_returns_primary_results_without_using_fallback():
    primary = SuccessfulCollector([make_job()])
    fallback = SuccessfulCollector([make_job("fallback")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == "job-1"
    assert primary.calls == 1
    assert fallback.calls == 0


def test_uses_fallback_when_primary_fails():
    from requests.exceptions import Timeout

    primary = FailingCollector(Timeout("SerpApi unavailable"))
    fallback = SuccessfulCollector([make_job("fallback")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].id == "fallback"
    assert primary.calls == 1
    assert fallback.calls == 1


def test_non_recoverable_primary_error_propagates_without_using_fallback():
    primary_error = RuntimeError("Primary failed")

    primary = FailingCollector(primary_error)
    fallback = SuccessfulCollector([make_job("fallback")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    with pytest.raises(RuntimeError, match="Primary failed"):
        collector.fetch_jobs()

    assert primary.calls == 1
    assert fallback.calls == 0


def test_fallback_is_not_used_when_primary_returns_empty_list():
    primary = SuccessfulCollector([])
    fallback = SuccessfulCollector([make_job("fallback")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    jobs = collector.fetch_jobs()

    assert jobs == []
    assert primary.calls == 1
    assert fallback.calls == 0


def test_fallback_collector_can_be_used_as_job_collector():
    from src.ingestion.collectors.job_collector import JobCollector

    primary = SuccessfulCollector([])
    fallback = SuccessfulCollector([])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    assert isinstance(collector, JobCollector)


def test_fallback_uses_fallback_on_timeout():
    from requests.exceptions import Timeout

    primary = FailingCollector(Timeout("request timed out"))
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    jobs = collector.fetch_jobs()

    assert [job.id for job in jobs] == ["fallback-job"]
    assert primary.calls == 1
    assert fallback.calls == 1


def test_fallback_uses_fallback_on_connection_error():
    from requests.exceptions import ConnectionError

    primary = FailingCollector(ConnectionError("connection failed"))
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    jobs = collector.fetch_jobs()

    assert [job.id for job in jobs] == ["fallback-job"]
    assert primary.calls == 1
    assert fallback.calls == 1


def test_fallback_does_not_hide_programming_errors():
    primary = FailingCollector(ValueError("invalid internal state"))
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    try:
        collector.fetch_jobs()
    except ValueError as exc:
        assert str(exc) == "invalid internal state"
    else:
        raise AssertionError("ValueError should propagate")

    assert primary.calls == 1
    assert fallback.calls == 0


def make_http_error(status_code):
    from requests import Response
    from requests.exceptions import HTTPError

    response = Response()
    response.status_code = status_code

    return HTTPError(
        f"HTTP {status_code}",
        response=response,
    )


@pytest.mark.parametrize("status_code", [429, 500, 502, 503, 504])
def test_fallback_uses_fallback_on_recoverable_http_error(status_code):
    primary = FailingCollector(make_http_error(status_code))
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    jobs = collector.fetch_jobs()

    assert [job.id for job in jobs] == ["fallback-job"]
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.parametrize("status_code", [400, 401, 403])
def test_fallback_does_not_hide_non_recoverable_http_error(status_code):
    primary_error = make_http_error(status_code)

    primary = FailingCollector(primary_error)
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    with pytest.raises(type(primary_error), match=f"HTTP {status_code}"):
        collector.fetch_jobs()

    assert primary.calls == 1
    assert fallback.calls == 0


@pytest.mark.parametrize("status_code", [501, 505, 599])
def test_fallback_uses_fallback_on_any_5xx_http_error(status_code):
    primary = FailingCollector(make_http_error(status_code))
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    jobs = collector.fetch_jobs()

    assert [job.id for job in jobs] == ["fallback-job"]
    assert primary.calls == 1
    assert fallback.calls == 1


@pytest.mark.parametrize("status_code", [400, 404, 408, 409, 422, 499])
def test_fallback_does_not_use_fallback_for_other_4xx_http_errors(status_code):
    primary_error = make_http_error(status_code)

    primary = FailingCollector(primary_error)
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    with pytest.raises(type(primary_error), match=f"HTTP {status_code}"):
        collector.fetch_jobs()

    assert primary.calls == 1
    assert fallback.calls == 0


def test_fallback_does_not_use_fallback_when_http_error_has_no_response():
    from requests.exceptions import HTTPError

    primary_error = HTTPError("HTTP error without response")

    primary = FailingCollector(primary_error)
    fallback = SuccessfulCollector([make_job("fallback-job")])

    collector = FallbackJobCollector(
        primary=primary,
        fallback=fallback,
    )

    with pytest.raises(HTTPError, match="HTTP error without response"):
        collector.fetch_jobs()

    assert primary.calls == 1
    assert fallback.calls == 0
