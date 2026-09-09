from datetime import datetime

import pytest

from src.ingestion.collectors.serpapi_job_collector import SerpApiJobCollector


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeHttpClient:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )
        return self.response


def test_collects_jobs_from_serpapi():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": "abc123",
                    "title": "Estágio em Desenvolvimento Python",
                    "company_name": "Empresa Exemplo",
                    "description": "Vaga para desenvolvimento com Python e SQL.",
                    "location": "São Paulo, SP",
                    "via": "LinkedIn",
                    "share_link": "https://example.com/job/abc123",
                    "detected_extensions": {
                        "posted_at": "2 days ago",
                    },
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="estágio desenvolvimento python",
        location="São Paulo, SP",
        limit=20,
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1

    job = jobs[0]

    assert job.external_id == "abc123"
    assert job.source == "serpapi"
    assert job.title == "Estágio em Desenvolvimento Python"
    assert job.company == "Empresa Exemplo"
    assert "Python" in job.description
    assert job.location == "São Paulo, SP"
    assert job.url == "https://example.com/job/abc123"
    assert job.discovered_at is not None
    assert isinstance(job.discovered_at, datetime)

    assert job.metadata["via"] == "LinkedIn"


def test_sends_expected_serpapi_parameters():
    response = FakeResponse({"jobs_results": []})
    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="estágio python",
        location="São Paulo, SP",
        limit=10,
        http_client=client,
    )

    collector.fetch_jobs()

    assert len(client.calls) == 1

    call = client.calls[0]

    assert call["params"]["api_key"] == "test-key"
    assert call["params"]["engine"] == "google_jobs"
    assert call["params"]["q"] == "estágio python"
    assert call["params"]["location"] == "São Paulo, SP"
    assert call["params"]["num"] == 10


def test_returns_empty_list_when_serpapi_returns_no_jobs():
    response = FakeResponse({})
    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="São Paulo, SP",
        http_client=client,
    )

    assert collector.fetch_jobs() == []


def test_rejects_empty_api_key():
    with pytest.raises(ValueError, match="api_key"):
        SerpApiJobCollector(
            api_key="",
            query="python",
            location="São Paulo, SP",
        )


def test_rejects_empty_query():
    with pytest.raises(ValueError, match="query"):
        SerpApiJobCollector(
            api_key="test-key",
            query="",
            location="São Paulo, SP",
        )


def test_http_error_is_propagated():
    response = FakeResponse(
        {},
        status_code=500,
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="São Paulo, SP",
        http_client=client,
    )

    with pytest.raises(RuntimeError, match="HTTP 500"):
        collector.fetch_jobs()


def test_job_id_is_stable_for_same_external_job():
    payload = {
        "jobs_results": [
            {
                "job_id": "abc123",
                "title": "Python Developer",
                "company_name": "Empresa",
                "description": "Python developer.",
            }
        ]
    }

    collector1 = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="São Paulo, SP",
        http_client=FakeHttpClient(FakeResponse(payload)),
    )

    collector2 = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="São Paulo, SP",
        http_client=FakeHttpClient(FakeResponse(payload)),
    )

    job1 = collector1.fetch_jobs()[0]
    job2 = collector2.fetch_jobs()[0]

    assert job1.id == job2.id


def test_preserves_original_result_in_metadata():
    result = {
        "job_id": "abc123",
        "title": "Python Developer",
        "company_name": "Empresa",
        "description": "Python developer.",
        "via": "LinkedIn",
        "schedule_type": "Full-time",
    }

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="São Paulo, SP",
        http_client=FakeHttpClient(
            FakeResponse({"jobs_results": [result]})
        ),
    )

    job = collector.fetch_jobs()[0]

    assert job.metadata["raw_result"] == result
    assert job.metadata["via"] == "LinkedIn"
    assert job.metadata["schedule_type"] == "Full-time"
