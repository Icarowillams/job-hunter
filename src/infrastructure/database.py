import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: str = "data/job_hunter.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS candidate_profile (
                    id TEXT PRIMARY KEY,
                    target_roles TEXT,
                    desired_seniority TEXT,
                    location TEXT,
                    work_modes TEXT,
                    salary_expectation TEXT,
                    relocation_availability INTEGER,
                    availability_date TEXT,
                    skills TEXT,
                    explicit_gaps TEXT,
                    experiences TEXT,
                    educations TEXT,
                    projects TEXT,
                    languages TEXT,
                    certifications TEXT,
                    preferences TEXT,
                    restrictions TEXT,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS job (
                    id TEXT PRIMARY KEY,
                    external_id TEXT,
                    source TEXT,
                    title TEXT,
                    company TEXT,
                    description TEXT,
                    location TEXT,
                    work_mode TEXT,
                    seniority TEXT,
                    published_at TEXT,
                    discovered_at TEXT,
                    updated_at TEXT,
                    original_published_at TEXT,
                    url TEXT,
                    metadata TEXT,
                    normalized_hash TEXT,
                    created_at TEXT
                );

                CREATE TABLE IF NOT EXISTS job_requirement (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    name TEXT,
                    category TEXT,
                    mandatory INTEGER,
                    extraction_confidence REAL,
                    FOREIGN KEY (job_id)
                        REFERENCES job(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS job_analysis (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    compatibility_score INTEGER,
                    priority_score INTEGER,
                    confidence_score INTEGER,
                    breakdown TEXT,
                    strengths TEXT,
                    gaps TEXT,
                    unknown_requirements TEXT,
                    hard_blocker INTEGER,
                    match_status TEXT,
                    classification TEXT,
                    raw_output TEXT,
                    scoring_version TEXT,
                    extractor_version TEXT,
                    normalizer_version TEXT,
                    embedding_model_version TEXT,
                    analyzed_at TEXT,
                    FOREIGN KEY (job_id)
                        REFERENCES job(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    job_analysis_id TEXT,
                    type TEXT,
                    comment TEXT,
                    created_at TEXT,
                    FOREIGN KEY (job_analysis_id)
                        REFERENCES job_analysis(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS pipeline_execution (
                    id TEXT PRIMARY KEY,
                    execution_id TEXT,
                    schedule_id TEXT,
                    started_at TEXT,
                    ended_at TEXT,
                    status TEXT,
                    total_jobs INTEGER,
                    processed_jobs INTEGER,
                    failed_jobs INTEGER,
                    error_log TEXT,
                    FOREIGN KEY (schedule_id)
                        REFERENCES search_schedule(id)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS search_schedule (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    query TEXT,
                    location TEXT,
                    interval_minutes INTEGER,
                    enabled INTEGER,
                    created_at TEXT,
                    last_run_at TEXT,
                    next_run_at TEXT
                );

                CREATE TABLE IF NOT EXISTS notification (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    title TEXT,
                    message TEXT,
                    score INTEGER,
                    classification TEXT,
                    channel TEXT,
                    status TEXT,
                    created_at TEXT,
                    sent_at TEXT,
                    error TEXT,
                    attempts INTEGER DEFAULT 0,
                    last_attempt_at TEXT,
                    FOREIGN KEY (job_id)
                        REFERENCES job(id)
                        ON DELETE CASCADE,
                    UNIQUE(job_id, channel)
                );

                CREATE TABLE IF NOT EXISTS metric (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    execution_id TEXT,
                    FOREIGN KEY (execution_id)
                        REFERENCES pipeline_execution(id)
                        ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_job_url
                    ON job(url);

                CREATE INDEX IF NOT EXISTS idx_job_published_at
                    ON job(published_at);

                CREATE INDEX IF NOT EXISTS idx_job_source
                    ON job(source);

                CREATE INDEX IF NOT EXISTS idx_job_analysis_job_id
                    ON job_analysis(job_id);

                CREATE INDEX IF NOT EXISTS idx_job_analysis_classification
                    ON job_analysis(classification);

                CREATE INDEX IF NOT EXISTS idx_pipeline_execution_execution_id
                    ON pipeline_execution(execution_id);

                CREATE INDEX IF NOT EXISTS idx_notification_job_id
                    ON notification(job_id);

                CREATE INDEX IF NOT EXISTS idx_notification_channel
                    ON notification(channel);

                CREATE INDEX IF NOT EXISTS idx_notification_status
                    ON notification(status);

                CREATE INDEX IF NOT EXISTS idx_metric_name
                    ON metric(name);

                CREATE INDEX IF NOT EXISTS idx_metric_created_at
                    ON metric(created_at);

                CREATE INDEX IF NOT EXISTS idx_metric_execution_id
                    ON metric(execution_id);
                """
            )
