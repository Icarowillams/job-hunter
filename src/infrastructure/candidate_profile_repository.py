import json
from datetime import datetime

from src.domain.models import CandidateProfile
from src.infrastructure.database import Database


class CandidateProfileRepository:
    def __init__(self, database: Database):
        self.database = database

    def save(self, profile: CandidateProfile) -> None:
        with self.database.connect() as conn:
            conn.execute(
                """
                INSERT INTO candidate_profile (
                    id,
                    target_roles,
                    desired_seniority,
                    location,
                    work_modes,
                    salary_expectation,
                    relocation_availability,
                    availability_date,
                    skills,
                    explicit_gaps,
                    experiences,
                    educations,
                    projects,
                    languages,
                    certifications,
                    preferences,
                    restrictions,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    target_roles = excluded.target_roles,
                    desired_seniority = excluded.desired_seniority,
                    location = excluded.location,
                    work_modes = excluded.work_modes,
                    salary_expectation = excluded.salary_expectation,
                    relocation_availability = excluded.relocation_availability,
                    availability_date = excluded.availability_date,
                    skills = excluded.skills,
                    explicit_gaps = excluded.explicit_gaps,
                    experiences = excluded.experiences,
                    educations = excluded.educations,
                    projects = excluded.projects,
                    languages = excluded.languages,
                    certifications = excluded.certifications,
                    preferences = excluded.preferences,
                    restrictions = excluded.restrictions,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.id,
                    json.dumps(profile.target_roles),
                    json.dumps(profile.desired_seniority),
                    profile.location,
                    json.dumps(profile.work_modes),
                    profile.salary_expectation,
                    int(profile.relocation_availability),
                    (
                        profile.availability_date.isoformat()
                        if profile.availability_date
                         else None
                    ),
                    json.dumps(profile.skills),
                    json.dumps(profile.explicit_gaps),
                    json.dumps(profile.experiences),
                    json.dumps(profile.educations),
                    json.dumps(profile.projects),
                    json.dumps(profile.languages),
                    json.dumps(profile.certifications),
                    json.dumps(profile.preferences),
                    json.dumps(profile.restrictions),
                    (
                        profile.updated_at.isoformat()
                        if profile.updated_at
                         else None
                    ),
                ),
            )

    def get_by_id(self, profile_id: str) -> CandidateProfile | None:
        with self.database.connect() as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    target_roles,
                    desired_seniority,
                    location,
                    work_modes,
                    salary_expectation,
                    relocation_availability,
                    availability_date,
                    skills,
                    explicit_gaps,
                    experiences,
                    educations,
                    projects,
                    languages,
                    certifications,
                    preferences,
                    restrictions,
                    updated_at
                FROM candidate_profile
                WHERE id = ?
                """,
                (profile_id,),
            ).fetchone()

        if row is None:
            return None

        return self._row_to_model(row)

    @staticmethod
    def _row_to_model(row) -> CandidateProfile:
        return CandidateProfile(
            id=row[0],
            target_roles=json.loads(row[1]) if row[1] else [],
            desired_seniority=json.loads(row[2]) if row[2] else [],
            location=row[3],
            work_modes=json.loads(row[4]) if row[4] else [],
            salary_expectation=row[5],
            relocation_availability=bool(row[6]),
            availability_date=(
            datetime.fromisoformat(row[7])
            if row[7]
            else None
            ),
            skills=json.loads(row[8]) if row[8] else [],
            explicit_gaps=json.loads(row[9]) if row[9] else [],
            experiences=json.loads(row[10]) if row[10] else [],
            educations=json.loads(row[11]) if row[11] else [],
            projects=json.loads(row[12]) if row[12] else [],
            languages=json.loads(row[13]) if row[13] else [],
            certifications=json.loads(row[14]) if row[14] else [],
            preferences=json.loads(row[15]) if row[15] else {},
            restrictions=json.loads(row[16]) if row[16] else [],
            updated_at=(
            datetime.fromisoformat(row[17])
            if row[17]
            else None
             ),
        )