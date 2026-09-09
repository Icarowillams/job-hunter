import hashlib
from datetime import datetime, timezone
from typing import Any

import requests

from src.domain.models import Job


class SerpApiJobCollector:
    """
    Collects job listings from SerpAPI Google Jobs.

    The collector is intentionally isolated from the application layer:
    it only performs ingestion and converts external results into domain
    Job objects.
    """

    BASE_URL = "https://serpapi.com/search.json"

    def __init__(
        self,
        api_key: str,
        query: str,
        location: str | None = None,
        limit: int = 20,
        timeout: int = 10,
        http_client: Any | None = None,
    ):
        if not api_key or not api_key.strip():
            raise ValueError("api_key must not be empty")

        if not query or not query.strip():
            raise ValueError("query must not be empty")

        if limit <= 0:
            raise ValueError("limit must be greater than zero")

        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.api_key = api_key
        self.query = query.strip()
        self.location = location.strip() if location else None
        self.limit = limit
        self.timeout = timeout
        self.http_client = http_client or requests

    def fetch_jobs(self) -> list[Job]:
        params = {
            "api_key": self.api_key,
            "engine": "google_jobs",
            "q": self.query,
            "num": self.limit,
        }

        if self.location:
            params["location"] = self.location

        response = self.http_client.get(
            self.BASE_URL,
            params=params,
            timeout=self.timeout,
        )

        response.raise_for_status()

        payload = response.json()

        if not isinstance(payload, dict):
            return []

        results = payload.get("jobs_results", [])

        if not isinstance(results, list):
            return []

        jobs: list[Job] = []

        for result in results:
            if not isinstance(result, dict):
                continue

            job = self._to_job(result)

            if job is not None:
                jobs.append(job)

        return jobs

    @classmethod
    def _to_job(cls, result: dict[str, Any]) -> Job | None:
        title = cls._first_string(
            result,
            "title",
            "job_title",
        )

        company = cls._first_string(
            result,
            "company_name",
            "company",
        )

        description = cls._first_string(
            result,
            "description",
        )

        if not title or not company:
            return None

        if not description:
            description = ""

        external_id = cls._first_string(
            result,
            "job_id",
            "id",
        )

        url = cls._extract_url(result)

        now = datetime.now(timezone.utc)

        job_id = cls._generate_job_id(
            external_id=external_id,
            title=title,
            company=company,
            url=url,
        )

        published_at = cls._parse_published_at(result)

        metadata = {
            "raw_result": result,
        }

        for key in (
            "via",
            "schedule_type",
            "salary",
            "extensions",
            "detected_extensions",
            "job_highlights",
            "related_links",
        ):
            if key in result:
                metadata[key] = result[key]

        return Job(
            id=job_id,
            external_id=external_id,
            source="serpapi",
            title=title,
            company=company,
            description=description,
            location=cls._extract_location(result),
            work_mode=cls._extract_work_mode(result),
            seniority=cls._extract_seniority(result),
            published_at=published_at,
            discovered_at=now,
            updated_at=now,
            original_published_at=published_at,
            url=url,
            metadata=metadata,
            normalized_hash=cls._generate_normalized_hash(
                title=title,
                company=company,
                description=description,
                location=cls._extract_location(result),
            ),
            created_at=now,
        )

    @staticmethod
    def _first_string(
        result: dict[str, Any],
        *keys: str,
    ) -> str | None:
        for key in keys:
            value = result.get(key)

            if isinstance(value, str) and value.strip():
                return value.strip()

        return None

    @staticmethod
    def _extract_url(result: dict[str, Any]) -> str | None:
        share_link = result.get("share_link")

        if isinstance(share_link, str) and share_link.strip():
            return share_link.strip()

        related_links = result.get("related_links")

        if isinstance(related_links, list):
            for link in related_links:
                if not isinstance(link, dict):
                    continue

                url = link.get("link")

                if isinstance(url, str) and url.strip():
                    return url.strip()

        return None

    @staticmethod
    def _extract_location(result: dict[str, Any]) -> str | None:
        location = result.get("location")

        if isinstance(location, str) and location.strip():
            return location.strip()

        return None

    @staticmethod
    def _extract_work_mode(result: dict[str, Any]) -> str | None:
        detected = result.get("detected_extensions")

        if isinstance(detected, dict):
            for key in (
                "work_from_home",
                "remote",
            ):
                value = detected.get(key)

                if value:
                    return "remote"

        extensions = result.get("extensions")

        if isinstance(extensions, list):
            lowered = [
                str(item).lower()
                for item in extensions
            ]

            if any(
                "remote" in item
                or "remoto" in item
                for item in lowered
            ):
                return "remote"

        return None

    @staticmethod
    def _extract_seniority(result: dict[str, Any]) -> str | None:
        title = str(result.get("title", "")).lower()

        if any(
            term in title
            for term in (
                "intern",
                "estágio",
                "estagio",
                "trainee",
            )
        ):
            return "internship"

        if "junior" in title or "júnior" in title:
            return "junior"

        if "senior" in title or "sênior" in title:
            return "senior"

        if "pleno" in title:
            return "mid"

        return None

    @staticmethod
    def _parse_published_at(
        result: dict[str, Any],
    ) -> datetime | None:
        detected = result.get("detected_extensions")

        if not isinstance(detected, dict):
            return None

        # SerpAPI commonly returns relative values such as
        # "2 days ago". We intentionally do not invent an exact
        # publication timestamp from a relative value.
        return None

    @staticmethod
    def _generate_job_id(
        external_id: str | None,
        title: str,
        company: str,
        url: str | None,
    ) -> str:
        if external_id:
            identity = f"serpapi:{external_id}"
        elif url:
            identity = f"serpapi:url:{url}"
        else:
            identity = (
                f"serpapi:"
                f"{title.lower().strip()}|"
                f"{company.lower().strip()}"
            )

        return hashlib.sha256(
            identity.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def _generate_normalized_hash(
        title: str,
        company: str,
        description: str,
        location: str | None,
    ) -> str:
        normalized = "|".join(
            [
                title.strip().lower(),
                company.strip().lower(),
                description.strip().lower(),
                (location or "").strip().lower(),
            ]
        )

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()
