from datetime import datetime, timedelta

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
    assert "num" not in call["params"]


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


def test_paginates_until_requested_limit():
    first_response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": f"job{i}",
                    "title": f"Python Developer {i}",
                    "company_name": "Empresa",
                    "description": "Python developer.",
                }
                for i in range(10)
            ],
            "serpapi_pagination": {
                "next_page_token": "next-token-123",
            },
        }
    )

    second_response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": f"job{i}",
                    "title": f"Python Developer {i}",
                    "company_name": "Empresa",
                    "description": "Python developer.",
                }
                for i in range(10, 20)
            ]
        }
    )

    class PaginatedHttpClient:
        def __init__(self):
            self.calls = []
            self.responses = [first_response, second_response]

        def get(self, url, params=None, timeout=None):
            self.calls.append(
                {
                    "url": url,
                    "params": dict(params),
                    "timeout": timeout,
                }
            )
            return self.responses.pop(0)

    client = PaginatedHttpClient()

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="S?o Paulo, SP",
        limit=20,
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 20
    assert len(client.calls) == 2
    assert "next_page_token" not in client.calls[0]["params"]
    assert client.calls[1]["params"]["next_page_token"] == "next-token-123"


def test_pagination_respects_requested_limit():
    first_response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": f"job{i}",
                    "title": f"Python Developer {i}",
                    "company_name": "Empresa",
                    "description": "Python developer.",
                }
                for i in range(10)
            ],
            "serpapi_pagination": {
                "next_page_token": "next-token-123",
            },
        }
    )

    second_response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": f"job{i}",
                    "title": f"Python Developer {i}",
                    "company_name": "Empresa",
                    "description": "Python developer.",
                }
                for i in range(10, 20)
            ],
            "serpapi_pagination": {
                "next_page_token": "should-not-be-used",
            },
        }
    )

    class PaginatedHttpClient:
        def __init__(self):
            self.calls = []
            self.responses = [first_response, second_response]

        def get(self, url, params=None, timeout=None):
            self.calls.append(
                {
                    "url": url,
                    "params": dict(params),
                    "timeout": timeout,
                }
            )
            return self.responses.pop(0)

    client = PaginatedHttpClient()

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="S?o Paulo, SP",
        limit=15,
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 15
    assert len(client.calls) == 2


def test_sends_location_in_serpapi_canonical_format():
    response = FakeResponse({"jobs_results": []})
    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="est?gio python",
        location="Recife,State of Pernambuco,Brazil",
        limit=10,
        http_client=client,
    )

    collector.fetch_jobs()

    call = client.calls[0]

    assert call["params"]["location"] == (
        "Recife,State of Pernambuco,Brazil"
    )

def test_parses_relative_published_at():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": "abc123",
                    "title": "Python Developer",
                    "company_name": "Empresa",
                    "description": "Python developer.",
                    "detected_extensions": {
                        "posted_at": "2 days ago",
                    },
                }
            ]
        }
    )

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python",
        location="S?o Paulo, SP",
        http_client=FakeHttpClient(response),
    )

    job = collector.fetch_jobs()[0]

    assert job.published_at is not None
    assert job.original_published_at is not None
    assert job.published_at.tzinfo is not None

def test_accepts_job_title_as_title_fallback():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_title": "Python Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento com Python.",
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python jobs",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].title == "Python Developer"


def test_accepts_company_as_company_name_fallback():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Python Developer",
                    "company": "Empresa Exemplo",
                    "description": "Desenvolvimento com Python.",
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python jobs",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].company == "Empresa Exemplo"


def test_allows_missing_description():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Python Developer",
                    "company_name": "Empresa Exemplo",
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python jobs",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].description == ""


def test_uses_related_link_when_share_link_is_missing():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Python Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento com Python.",
                    "related_links": [
                        {
                            "link": "https://example.com/python-job"
                        }
                    ],
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python jobs",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].url == "https://example.com/python-job"


def test_infers_internship_seniority_from_title():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Est?gio em Desenvolvimento Python",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento com Python.",
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python est?gio",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].seniority == "internship"


def test_detects_remote_from_extensions():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Python Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento com Python.",
                    "extensions": ["Remote", "Full-time"],
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python jobs",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].work_mode == "remote"


def test_preserves_extended_metadata():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Python Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento com Python.",
                    "salary": "R$ 4.000",
                    "job_highlights": ["Python", "APIs"],
                    "related_links": [
                        {"link": "https://example.com/job"}
                    ],
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python jobs",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].metadata["salary"] == "R$ 4.000"
    assert jobs[0].metadata["job_highlights"] == ["Python", "APIs"]
    assert jobs[0].metadata["related_links"][0]["link"] == (
        "https://example.com/job"
    )


def test_normalized_hash_includes_location():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "title": "Python Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento com Python.",
                    "location": "Recife, PE",
                }
            ]
        }
    )

    client = FakeHttpClient(response)

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="python jobs",
        http_client=client,
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1

    expected = collector._generate_normalized_hash(
        title="Python Developer",
        company="Empresa Exemplo",
        description="Desenvolvimento com Python.",
        location="Recife, PE",
    )

    assert jobs[0].normalized_hash == expected

def test_apply_link_has_priority_over_share_link():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": "priority-123",
                    "title": "Backend Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento backend.",
                    "share_link": "https://example.com/share-link",
                    "apply_options": [
                        {
                            "link": "https://example.com/apply-link"
                        }
                    ],
                }
            ]
        }
    )

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="backend developer",
        http_client=FakeHttpClient(response),
    )

    jobs = collector.fetch_jobs()

    assert len(jobs) == 1
    assert jobs[0].url == "https://example.com/apply-link"


def test_parses_portuguese_relative_published_at_days():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": "pt-days-123",
                    "title": "Backend Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento backend.",
                    "detected_extensions": {
                        "posted_at": "h? 2 dias",
                    },
                }
            ]
        }
    )

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="backend developer",
        http_client=FakeHttpClient(response),
    )

    job = collector.fetch_jobs()[0]

    assert job.published_at is not None
    assert job.original_published_at == job.published_at
    assert timedelta(days=1, hours=23) <= (job.discovered_at - job.published_at) <= timedelta(days=2, hours=1)
    assert job.published_at.tzinfo is not None


def test_parses_portuguese_relative_published_at_hours():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": "pt-hours-123",
                    "title": "Backend Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento backend.",
                    "detected_extensions": {
                        "posted_at": "h? 3 horas",
                    },
                }
            ]
        }
    )

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="backend developer",
        http_client=FakeHttpClient(response),
    )

    job = collector.fetch_jobs()[0]

    assert job.published_at is not None
    assert job.original_published_at == job.published_at
    assert timedelta(hours=2, minutes=59) <= (job.discovered_at - job.published_at) <= timedelta(hours=3, minutes=1)
    assert job.published_at.tzinfo is not None


def test_parses_portuguese_relative_published_at_now():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": "pt-now-123",
                    "title": "Backend Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Desenvolvimento backend.",
                    "detected_extensions": {
                        "posted_at": "agora",
                    },
                }
            ]
        }
    )

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="backend developer",
        http_client=FakeHttpClient(response),
    )

    job = collector.fetch_jobs()[0]

    assert job.published_at is not None
    assert job.original_published_at == job.published_at
    assert job.discovered_at - job.published_at <= timedelta(minutes=1)
    assert job.published_at.tzinfo is not None


def test_still_parses_english_relative_published_at():
    response = FakeResponse(
        {
            "jobs_results": [
                {
                    "job_id": "en-days-123",
                    "title": "Backend Developer",
                    "company_name": "Empresa Exemplo",
                    "description": "Backend development.",
                    "detected_extensions": {
                        "posted_at": "2 days ago",
                    },
                }
            ]
        }
    )

    collector = SerpApiJobCollector(
        api_key="test-key",
        query="backend developer",
        http_client=FakeHttpClient(response),
    )

    job = collector.fetch_jobs()[0]

    assert job.published_at is not None
    assert job.original_published_at == job.published_at
    assert timedelta(days=1, hours=23) <= (job.discovered_at - job.published_at) <= timedelta(days=2, hours=1)
    assert job.published_at.tzinfo is not None
