from src.ingestion.collectors.job_collector import JobCollector
from src.ingestion.collectors.serpapi_google_search_collector import (
    SerpApiGoogleSearchCollector,
)


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


def test_google_search_collector_implements_job_collector():
    assert issubclass(SerpApiGoogleSearchCollector, JobCollector)


def test_collects_job_from_google_search_result():
    response = FakeResponse(
        {
            "organic_results": [
                {
                    "title": "Estágio em Desenvolvimento Python",
                    "link": "https://example.com/jobs/python",
                    "snippet": (
                        "Estágio para desenvolvimento Python, "
                        "SQL e APIs."
                    ),
                    "source": "Empresa Exemplo",
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiGoogleSearchCollector(
        api_key="test-key",
        query="estágio desenvolvimento Python",
        location="Recife, PE",
        limit=10,
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1

    job = jobs[0]

    assert job.title == "Estágio em Desenvolvimento Python"
    assert job.company == "Empresa Exemplo"
    assert job.url == "https://example.com/jobs/python"
    assert "Python" in job.description
    assert job.source == "serpapi_google_search"


def test_sends_expected_google_search_parameters():
    response = FakeResponse({"organic_results": []})
    client = FakeHttpClient(response)

    collector = SerpApiGoogleSearchCollector(
        api_key="test-key",
        query="estágio python",
        location="Recife, PE",
        limit=10,
        http_client=client,
    )

    collector.fetch_jobs()

    assert len(client.calls) == 1

    params = client.calls[0]["params"]

    assert params["api_key"] == "test-key"
    assert params["engine"] == "google"
    assert params["q"] == "estágio python"
    assert params["location"] == "Recife, PE"


def test_ignores_search_results_without_required_fields():
    response = FakeResponse(
        {
            "organic_results": [
                {
                    "title": "Resultado sem link",
                    "snippet": "Não é uma vaga completa.",
                },
                {
                    "title": "Resultado válido",
                    "link": "https://example.com/job",
                    "snippet": "Vaga para Python.",
                    "source": "Empresa",
                },
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiGoogleSearchCollector(
        api_key="test-key",
        query="python",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Resultado válido"


def test_rejects_empty_api_key():
    import pytest

    with pytest.raises(ValueError, match="api_key"):
        SerpApiGoogleSearchCollector(
            api_key="",
            query="python",
        )


def test_rejects_empty_query():
    import pytest

    with pytest.raises(ValueError, match="query"):
        SerpApiGoogleSearchCollector(
            api_key="test-key",
            query="",
        )

def test_collects_structured_job_from_google_search_jobs_results():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Python Backend Developer",
                    "company_name": "Empresa Exemplo",
                    "location": "Recife, PE",
                    "via": "LinkedIn",
                    "share_link": "https://example.com/jobs/python",
                    "description": "Desenvolvimento backend com Python e APIs.",
                    "detected_extensions": {
                        "posted_at": "2 days ago",
                        "schedule_type": "Full-time",
                    },
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiGoogleSearchCollector(
        api_key="test-key",
        query="python jobs",
        location="Recife, PE",
        limit=10,
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1

    job = jobs[0]

    assert job.title == "Python Backend Developer"
    assert job.company == "Empresa Exemplo"
    assert job.description == "Desenvolvimento backend com Python e APIs."
    assert job.location == "Recife, PE"
    assert job.url == "https://example.com/jobs/python"
    assert job.source == "serpapi_google_search"
    assert job.metadata["collector"] == "google_search"
    assert job.metadata["via"] == "LinkedIn"
    assert job.metadata["schedule_type"] == "Full-time"
