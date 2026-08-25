from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CandidateProfile(BaseModel):
    id: str
    target_roles: List[str] = Field(default_factory=list)
    desired_seniority: List[str] = Field(default_factory=list)
    location: Optional[str] = None
    work_modes: List[str] = Field(default_factory=list)
    salary_expectation: Optional[str] = None
    relocation_availability: bool = False
    availability_date: Optional[datetime] = None
    skills: List[str] = Field(default_factory=list)
    explicit_gaps: List[str] = Field(default_factory=list)
    experiences: List[Dict[str, Any]] = Field(default_factory=list)
    educations: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    languages: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    restrictions: List[str] = Field(default_factory=list)
    updated_at: Optional[datetime] = None


class Job(BaseModel):
    id: str
    external_id: Optional[str] = None
    source: str
    title: str
    company: str
    description: str
    location: Optional[str] = None
    work_mode: Optional[str] = None
    seniority: Optional[str] = None
    published_at: Optional[datetime] = None
    discovered_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    original_published_at: Optional[datetime] = None
    url: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    normalized_hash: Optional[str] = None
    created_at: Optional[datetime] = None


class JobRequirement(BaseModel):
    id: str
    job_id: str
    name: str
    category: str
    mandatory: bool = False
    extraction_confidence: float = 0.0


class JobAnalysis(BaseModel):
    id: str
    job_id: str
    compatibility_score: int
    priority_score: int
    confidence_score: int
    breakdown: Dict[str, Any] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    unknown_requirements: List[str] = Field(default_factory=list)
    hard_blocker: bool = False
    match_status: Optional[str] = None
    classification: Optional[str] = None
    raw_output: Optional[str] = None
    scoring_version: Optional[str] = None
    extractor_version: Optional[str] = None
    normalizer_version: Optional[str] = None
    embedding_model_version: Optional[str] = None
    analyzed_at: Optional[datetime] = None


class Feedback(BaseModel):
    id: str
    job_analysis_id: str
    type: str
    comment: Optional[str] = None
    created_at: datetime


class PipelineExecution(BaseModel):
    id: str
    execution_id: Optional[str] = None
    schedule_id: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str
    total_jobs: int = 0
    processed_jobs: int = 0
    failed_jobs: int = 0
    error_log: Optional[str] = None


class SearchSchedule(BaseModel):
    id: str
    name: str
    query: str
    location: Optional[str] = None
    interval_minutes: int
    enabled: bool = True
    created_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
