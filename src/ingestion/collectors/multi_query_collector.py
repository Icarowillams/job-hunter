"""Small bounded fan-out for a single user's searches, with cross-query deduplication."""
from src.ingestion.collectors.job_collector import JobCollector


class MultiQueryCollector(JobCollector):
    def __init__(self, collectors):
        self.collectors = list(collectors)

    def fetch_jobs(self):
        jobs = []
        seen = set()
        for collector in self.collectors:
            # A failing search is an operational failure, not 'zero jobs'.
            for job in collector.fetch_jobs():
                keys = {('id', job.id)}
                if job.url:
                    keys.add(('url', job.url.split('#', 1)[0]))
                if not keys.isdisjoint(seen):
                    continue
                seen.update(keys)
                jobs.append(job)
        return jobs
