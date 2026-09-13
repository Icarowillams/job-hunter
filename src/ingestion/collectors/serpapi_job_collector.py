from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

import requests

from src.domain.models import Job
from src.ingestion.collectors.job_collector import JobCollector


class SerpApiJobCollector(JobCollector):
    """
    Collects job listings from SerpAPI Google Jobs.

    The collector is intentionally isolated from the application layer:
    it only performs ingestion and converts external results into domain
    Job objects.
    """

    BASE_URL = "https://serpapi.com/search"
    PAGE_SIZE = 10

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
        jobs: list[Job] = []
        next_page_token = None

        while len(jobs) < self.limit:
            params = {
                "api_key": self.api_key,
                "engine": "google_jobs",
                "q": self.query,
            }

            if self.location:
                params["location"] = self.location

            if next_page_token:
                params["next_page_token"] = next_page_token

            response = self.http_client.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
            )

            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, dict):
                break

            results = payload.get("jobs_results", [])

            if not isinstance(results, list):
                break

            remaining = self.limit - len(jobs)

            for result in results[:remaining]:
                if not isinstance(result, dict):
                    continue

                job = self._to_job(result)

                if job is not None:
                    jobs.append(job)

            if len(jobs) >= self.limit:
                break

            pagination = payload.get("serpapi_pagination", {})

            if not isinstance(pagination, dict):
                break

            next_page_token = pagination.get("next_page_token")

            if not next_page_token:
                break

        return jobs

    def _to_job(self, result: dict[str, Any]) -> Job | None:
        title = self._first_string(
            result,
            "title",
            "job_title",
        )

        company = self._first_string(
            result,
            "company_name",
            "company",
        )

        description = self._first_string(
            result,
            "description",
        )

        if not title or not company:
            return None

        if description is None:
            description = ""

        external_id = self._first_string(
            result,
            "job_id",
            "id",
        )

        url = self._extract_url(result)
        location = self._extract_location(result)
        published_at = self._extract_published_at(result)

        now = datetime.now(timezone.utc)

        job_id = self._generate_job_id(
            external_id=external_id,
            title=title,
            company=company,
            url=url,
        )

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
            location=location,
            work_mode=self._extract_work_mode(result),
            seniority=self._extract_seniority(result),
            published_at=published_at,
            discovered_at=now,
            updated_at=now,
            original_published_at=published_at,
            url=url,
            metadata=metadata,
            normalized_hash=self._generate_normalized_hash(
                title=title,
                company=company,
                description=description,
                location=location,
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
        apply_options = result.get("apply_options")

        if isinstance(apply_options, list):
            for option in apply_options:
                if not isinstance(option, dict):
                    continue

                url = option.get("link")

                if isinstance(url, str) and url.strip():
                    return url.strip()

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
                "work_mode",
            ):
                value = detected.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

                if value is True:
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
        detected = result.get("detected_extensions")

        if isinstance(detected, dict):
            value = detected.get("seniority")

            if isinstance(value, str) and value.strip():
                return value.strip()

        title = str(result.get("title", "")).lower()

        if any(
            term in title
            for term in (
                "intern",
                "est?gio",
                "estagio",
                "trainee",
            )
        ):
            return "internship"

        if "junior" in title or "j?nior" in title:
            return "junior"

        if "senior" in title or "s?nior" in title:
            return "senior"

        if "pleno" in title:
            return "mid"

        return None

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

        if value in {
            "just now",
            "moments ago",
            "now",
            "agora",
            "agora mesmo",
        }:
            return now

        if value in {"today", "hoje"}:
            return now.replace(
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

        parts = value.split()

        if len(parts) == 3 and parts[0] == "h?" and parts[2] in {
            "minuto",
            "minutos",
            "hora",
            "horas",
            "dia",
            "dias",
            "semana",
            "semanas",
            "m?s",
            "meses",
            "ano",
            "anos",
        }:
            amount_text = parts[1]
            unit = parts[2]

            try:
                amount = int(amount_text)
            except ValueError:
                return None

            if amount < 0:
                return None

            if unit in {"minuto", "minutos"}:
                return now - timedelta(minutes=amount)

            if unit in {"hora", "horas"}:
                return now - timedelta(hours=amount)

            if unit in {"dia", "dias"}:
                return now - timedelta(days=amount)

            if unit in {"semana", "semanas"}:
                return now - timedelta(weeks=amount)

            if unit in {"m?s", "meses"}:
                return now - timedelta(days=amount * 30)

            if unit in {"ano", "anos"}:
                return now - timedelta(days=amount * 365)

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
