import json

from src.domain.models import JobAnalysis
from src.infrastructure.database import Database


class JobAnalysisRepository:
    def __init__(self, database: Database):
        self.database = database

    def save(self, analysis: JobAnalysis) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO job_analysis (
                    id,
                    job_id,
                    compatibility_score,
                    priority_score,
                    confidence_score,
                    breakdown,
                    strengths,
                    gaps,
                    unknown_requirements,
                    hard_blocker,
                    match_status,
                    classification,
                    raw_output,
                    scoring_version,
                    extractor_version,
                    normalizer_version,
                    embedding_model_version,
                    analyzed_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    job_id = excluded.job_id,
                    compatibility_score = excluded.compatibility_score,
                    priority_score = excluded.priority_score,
                    confidence_score = excluded.confidence_score,
                    breakdown = excluded.breakdown,
                    strengths = excluded.strengths,
                    gaps = excluded.gaps,
                    unknown_requirements = excluded.unknown_requirements,
                    hard_blocker = excluded.hard_blocker,
                    match_status = excluded.match_status,
                    classification = excluded.classification,
                    raw_output = excluded.raw_output,
                    scoring_version = excluded.scoring_version,
                    extractor_version = excluded.extractor_version,
                    normalizer_version = excluded.normalizer_version,
                    embedding_model_version = excluded.embedding_model_version,
                    analyzed_at = excluded.analyzed_at
                """,
                (
                    analysis.id,
                    analysis.job_id,
                    analysis.compatibility_score,
                    analysis.priority_score,
                    analysis.confidence_score,
                    json.dumps(analysis.breakdown),
                    json.dumps(analysis.strengths),
                    json.dumps(analysis.gaps),
                    json.dumps(analysis.unknown_requirements),
                    int(analysis.hard_blocker),
                    analysis.match_status,
                    analysis.classification,
                    analysis.raw_output,
                    analysis.scoring_version,
                    analysis.extractor_version,
                    analysis.normalizer_version,
                    analysis.embedding_model_version,
                    (
                        analysis.analyzed_at.isoformat()
                        if analysis.analyzed_at is not None
                        else None
                    ),
                ),
            )

    def get_by_id(self, analysis_id: str) -> JobAnalysis | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    job_id,
                    compatibility_score,
                    priority_score,
                    confidence_score,
                    breakdown,
                    strengths,
                    gaps,
                    unknown_requirements,
                    hard_blocker,
                    match_status,
                    classification,
                    raw_output,
                    scoring_version,
                    extractor_version,
                    normalizer_version,
                    embedding_model_version,
                    analyzed_at
                FROM job_analysis
                WHERE id = ?
                """,
                (analysis_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    def get_by_job_id(self, job_id: str) -> JobAnalysis | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    job_id,
                    compatibility_score,
                    priority_score,
                    confidence_score,
                    breakdown,
                    strengths,
                    gaps,
                    unknown_requirements,
                    hard_blocker,
                    match_status,
                    classification,
                    raw_output,
                    scoring_version,
                    extractor_version,
                    normalizer_version,
                    embedding_model_version,
                    analyzed_at
                FROM job_analysis
                WHERE job_id = ?
                ORDER BY analyzed_at DESC, id DESC
                LIMIT 1
                """,
                (job_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    @staticmethod
    def _row_to_model(row) -> JobAnalysis:
        return JobAnalysis(
            id=row[0],
            job_id=row[1],
            compatibility_score=row[2],
            priority_score=row[3],
            confidence_score=row[4],
            breakdown=json.loads(row[5]) if row[5] else {},
            strengths=json.loads(row[6]) if row[6] else [],
            gaps=json.loads(row[7]) if row[7] else [],
            unknown_requirements=json.loads(row[8]) if row[8] else [],
            hard_blocker=bool(row[9]),
            match_status=row[10],
            classification=row[11],
            raw_output=row[12],
            scoring_version=row[13],
            extractor_version=row[14],
            normalizer_version=row[15],
            embedding_model_version=row[16],
            analyzed_at=row[17],
        )