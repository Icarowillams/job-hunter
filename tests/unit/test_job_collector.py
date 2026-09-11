from src.domain.models import Job
from src.ingestion.collectors.job_collector import JobCollector


def test_job_collector_defines_fetch_jobs_contract():
    assert hasattr(JobCollector, "fetch_jobs")
    assert JobCollector.fetch_jobs.__isabstractmethod__


def test_concrete_collector_can_implement_contract():
    class FakeCollector(JobCollector):
        def fetch_jobs(self) -> list[Job]:
            return []

    collector = FakeCollector()

    assert collector.fetch_jobs() == []
from src.ingestion.collectors.job_collector import JobCollector
from src.ingestion.collectors.serpapi_job_collector import SerpApiJobCollector


def test_serpapi_collector_implements_job_collector():
    assert issubclass(SerpApiJobCollector, JobCollector)
