from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

import requests

from src.domain.models import Job
from src.ingestion.collectors.job_collector import JobCollector


class SerpApiGoogleSearchCollector(JobCollector):
    """Collects job candidates from SerpAPI Google Search results."""

    BASE_URL = "https://serpapi.com/search"

    def __init__(
        self,
        api_key,
        query,
        location=None,
        limit=10,
        timeout=30,
        http_client=None,
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
            "engine": "google",
            "q": self.query,
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

        jobs = []

        structured_results = payload.get("jobs_results", [])

        if isinstance(structured_results, list):
            for result in structured_results:
                if not isinstance(result, dict):
                    continue

                job = self._to_structured_job(result)

                if job is None:
                    continue

                jobs.append(job)

                if len(jobs) >= self.limit:
                    return jobs

        results = payload.get("organic_results", [])

        if not isinstance(results, list):
            return jobs

        for result in results:
            if not isinstance(result, dict):
                continue

            job = self._to_job(result)

            if job is None:
                continue

            jobs.append(job)

            if len(jobs) >= self.limit:
                break

        return jobs

    def _to_job(self, result: dict[str, Any]) -> Job | None:
        return self._to_organic_job(result)

    def _to_structured_job(
        self,
        result: dict[str, Any],
    ) -> Job | None:
        title = result.get("title")
        company = result.get("company_name")
        description = result.get("description")
        url = result.get("share_link")
        location = result.get("location")

        if not title or not company or not description:
            return None

        stable_key = (
            f"serpapi_google_jobs:"
            f"{result.get('job_id', '')}|"
            f"{title}|"
            f"{company}|"
            f"{location or ''}|"
            f"{url or ''}"
        )

        return self._build_job(
            result=result,
            title=title,
            company=company,
            description=description,
            location=location,
            url=url,
            stable_key=stable_key,
        )

    def _to_organic_job(
        self,
        result: dict[str, Any],
    ) -> Job | None:
        title = result.get("title")
        url = result.get("link")
        description = result.get("snippet")
        company = result.get("source")

        if not title or not url or not description or not company:
            return None

        return self._build_job(
            result=result,
            title=title,
            company=company,
            description=description,
            location=self.location,
            url=url,
            stable_key=f"serpapi_google:{url}",
        )

    def _build_job(
        self,
        result: dict[str, Any],
        title: str,
        company: str,
        description: str,
        location: str | None,
        url: str | None,
        stable_key: str,
    ) -> Job:
        job_id = hashlib.sha256(
            stable_key.encode("utf-8")
        ).hexdigest()

        now = datetime.now(timezone.utc)

        metadata = {
            "raw_result": result,
            "collector": "google_search",
        }

        for key in (
            "via",
            "schedule_type",
            "detected_extensions",
            "extensions",
            "position",
            "displayed_link",
            "date",
            "snippet",
        ):
            if key in result:
                metadata[key] = result[key]

        detected_extensions = result.get("detected_extensions")

        if isinstance(detected_extensions, dict):
            for key in (
                "posted_at",
                "schedule_type",
                "seniority",
                "work_from_home",
                "remote",
                "work_mode",
            ):
                if key in detected_extensions:
                    metadata[key] = detected_extensions[key]

        return Job(
            id=job_id,
            external_id=result.get("job_id"),
            source="serpapi_google_search",
            title=title,
            company=company,
            description=description,
            location=location,
            work_mode=self._extract_work_mode(result),
            seniority=self._extract_seniority(result),
            published_at=self._extract_published_at(result),
            discovered_at=now,
            updated_at=now,
            original_published_at=self._extract_published_at(result),
            url=url,
            metadata=metadata,
            normalized_hash=self._normalized_hash(
                title,
                company,
                description,
            ),
            created_at=now,
        )

    @staticmethod
    def _extract_work_mode(result: dict[str, Any]) -> str | None:
        extensions = result.get("detected_extensions", {})

        if not isinstance(extensions, dict):
            return None

        for key in ("work_from_home", "remote", "work_mode"):
            value = extensions.get(key)

            if isinstance(value, str):
                return value

            if value is True:
                return "remote"

        return None

    @staticmethod
    def _extract_seniority(result: dict[str, Any]) -> str | None:
        extensions = result.get("detected_extensions", {})

        if not isinstance(extensions, dict):
            return None

        value = extensions.get("seniority")

        return value if isinstance(value, str) else None

    @staticmethod
    def _extract_published_at(
        result: dict[str, Any],
    ) -> datetime | None:
        extensions = result.get("detected_extensions", {})

        if not isinstance(extensions, dict):
            return None

        posted_at = extensions.get("posted_at")

        if not isinstance(posted_at, str) or not posted_at.strip():
            return None

        value = posted_at.strip().lower()
        now = datetime.now(timezone.utc)

        if value in {"just now", "moments ago"}:
            return now

        if value == "today":
            return now.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        parts = value.split()

        if len(parts) != 3 or parts[2] != "ago":
            return None

        try:
            amount = int(parts[0])
        except ValueError:
            return None

        unit = parts[1]

        if amount < 0:
            return None

        if unit in {"minute", "minutes"}:
            return now - timedelta(minutes=amount)

        if unit in {"hour", "hours"}:
            return now - timedelta(hours=amount)

        if unit in {"day", "days"}:
            return now - timedelta(days=amount)

        if unit in {"week", "weeks"}:
            return now - timedelta(weeks=amount)

        if unit in {"month", "months"}:
            return now - timedelta(days=amount * 30)

        if unit in {"year", "years"}:
            return now - timedelta(days=amount * 365)

        return None

    @staticmethod
    def _normalized_hash(
        title: str,
        company: str,
        description: str,
    ) -> str:
        normalized = "|".join(
            [
                title.strip().lower(),
                company.strip().lower(),
                description.strip().lower(),
            ]
        )

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()
