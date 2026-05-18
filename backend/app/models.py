"""
SQLAlchemy ORM models mirroring the Supabase schema.
All UUIDs use server-side uuid_generate_v4() as default.
"""

import uuid
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Text, Boolean, SmallInteger, Integer, Float,
    DateTime, Date, ForeignKey, UniqueConstraint, Enum as SAEnum,
    ARRAY, JSON,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base

# ── Shared helper ──────────────────────────────────────────────────────────────

def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

def now_col():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

def fk(ref: str, nullable: bool = False):
    return mapped_column(UUID(as_uuid=True), ForeignKey(ref, ondelete="CASCADE"), nullable=nullable)


# ── Enum string values (match SQL enums) ──────────────────────────────────────

ATS_PROVIDERS = ("greenhouse","lever","ashby","workday","icims",
                 "smartrecruiters","oracle_recruiting","sap_successfactors",
                 "custom_html","unknown")

COMPANY_PRIORITIES  = ("high","medium","low")
JOB_STATUSES        = ("open","closed","possibly_closed","archived")
ROLE_TYPES          = ("internship","new_grad","full_time","coop","contract")
REMOTE_PREFS        = ("remote","hybrid","onsite","any")
SEARCH_MODES        = ("strict_software_ai","balanced","finance_tech_balanced",
                       "finance_broad","investment_only","broad")
APP_STATUSES        = ("not_applied","saved","applied","interview","rejected","offer","archived")
ALERT_CHANNELS      = ("email","sms","slack","discord","push")
ALERT_STATUSES      = ("pending","sent","failed","suppressed")
INGEST_RUN_STATUSES = ("running","completed","completed_with_errors","failed")
CHECK_STATUSES      = ("success","partial","failed","skipped")
KW_IMPORTANCES      = ("required","preferred","nice_to_have")
RECRUITER_VERDICTS  = ("strong_move_forward","move_forward","maybe","weak_maybe","likely_reject")
EXPORT_FORMATS      = ("pdf","docx","txt","json")
FILTER_TYPES        = ("included","excluded")


# =============================================================================
# USERS
# =============================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID]               = uuid_pk()
    email: Mapped[str]                  = mapped_column(String, nullable=False, unique=True)
    full_name: Mapped[Optional[str]]    = mapped_column(String)
    graduation_year: Mapped[Optional[int]] = mapped_column(SmallInteger)
    school: Mapped[Optional[str]]       = mapped_column(String)
    major: Mapped[Optional[str]]        = mapped_column(String)
    minor: Mapped[Optional[str]]        = mapped_column(String)
    preferred_locations: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    preferred_role_types: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    preferred_company_categories: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    alert_email: Mapped[Optional[str]]  = mapped_column(String)
    alert_frequency: Mapped[str]        = mapped_column(String, default="daily")
    minimum_match_score: Mapped[int]    = mapped_column(SmallInteger, default=70)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    resume_export_format: Mapped[str]   = mapped_column(String, default="pdf")
    created_at: Mapped[datetime]        = now_col()
    updated_at: Mapped[datetime]        = now_col()

    companies: Mapped[List["Company"]]  = relationship(back_populates="user")
    target_profiles: Mapped[List["TargetProfile"]] = relationship(back_populates="user")
    resumes: Mapped[List["Resume"]]     = relationship(back_populates="user")


# =============================================================================
# COMPANY CATEGORIES
# =============================================================================

class CompanyCategory(Base):
    __tablename__ = "company_categories"

    id: Mapped[uuid.UUID]               = uuid_pk()
    slug: Mapped[str]                   = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str]                   = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]]  = mapped_column(Text)
    sort_order: Mapped[int]             = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime]        = now_col()

    assignments: Mapped[List["CompanyCategoryAssignment"]] = relationship(back_populates="category")


# =============================================================================
# COMPANIES
# =============================================================================

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID]               = uuid_pk()
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    name: Mapped[str]                   = mapped_column(String, nullable=False)
    domain: Mapped[Optional[str]]       = mapped_column(String)
    careers_url: Mapped[Optional[str]]  = mapped_column(Text)
    ats_provider: Mapped[str]           = mapped_column(
                                            SAEnum(*ATS_PROVIDERS, name="ats_provider_enum"),
                                            default="unknown", nullable=False)
    ats_slug: Mapped[Optional[str]]     = mapped_column(String)
    source_url: Mapped[Optional[str]]   = mapped_column(Text)
    ats_detection_confidence: Mapped[Optional[float]] = mapped_column(Float)
    ats_detection_warning: Mapped[Optional[str]]      = mapped_column(Text)
    priority: Mapped[str]               = mapped_column(
                                            SAEnum(*COMPANY_PRIORITIES, name="company_priority_enum"),
                                            default="medium", nullable=False)
    is_active: Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]]        = mapped_column(Text)
    last_checked_at: Mapped[Optional[datetime]]          = mapped_column(DateTime(timezone=True))
    last_successful_check_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]]   = mapped_column(Text)
    consecutive_errors: Mapped[int]     = mapped_column(SmallInteger, default=0, nullable=False)
    total_jobs_found: Mapped[int]       = mapped_column(Integer, default=0, nullable=False)
    total_matching_jobs: Mapped[int]    = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime]        = now_col()
    updated_at: Mapped[datetime]        = now_col()

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="companies_user_name_unique"),
    )

    user: Mapped["User"]                = relationship(back_populates="companies")
    category_assignments: Mapped[List["CompanyCategoryAssignment"]] = relationship(
                                            back_populates="company", cascade="all, delete-orphan")
    jobs: Mapped[List["Job"]]           = relationship(back_populates="company")


# =============================================================================
# COMPANY CATEGORY ASSIGNMENTS
# =============================================================================

class CompanyCategoryAssignment(Base):
    __tablename__ = "company_category_assignments"

    id: Mapped[uuid.UUID]           = uuid_pk()
    company_id: Mapped[uuid.UUID]   = fk("companies.id")
    category_id: Mapped[uuid.UUID]  = fk("company_categories.id")
    assigned_at: Mapped[datetime]   = now_col()

    __table_args__ = (
        UniqueConstraint("company_id", "category_id", name="company_category_unique"),
    )

    company: Mapped["Company"]              = relationship(back_populates="category_assignments")
    category: Mapped["CompanyCategory"]     = relationship(back_populates="assignments")


# =============================================================================
# TARGET PROFILES
# =============================================================================

class TargetProfile(Base):
    __tablename__ = "target_profiles"

    id: Mapped[uuid.UUID]               = uuid_pk()
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    name: Mapped[str]                   = mapped_column(String, nullable=False)
    desired_titles: Mapped[List[str]]   = mapped_column(ARRAY(String), default=list)
    desired_keywords: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    desired_locations: Mapped[List[str]]= mapped_column(ARRAY(String), default=list)
    excluded_keywords: Mapped[List[str]]= mapped_column(ARRAY(String), default=list)
    role_types: Mapped[List[str]]       = mapped_column(ARRAY(String), default=list)
    remote_preference: Mapped[str]      = mapped_column(
                                            SAEnum(*REMOTE_PREFS, name="remote_preference_enum"),
                                            default="any", nullable=False)
    minimum_match_score: Mapped[int]    = mapped_column(SmallInteger, default=70, nullable=False)
    search_mode: Mapped[str]            = mapped_column(
                                            SAEnum(*SEARCH_MODES, name="search_mode_enum"),
                                            default="balanced", nullable=False)
    alerts_enabled: Mapped[bool]        = mapped_column(Boolean, default=True, nullable=False)
    is_active: Mapped[bool]             = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime]        = now_col()
    updated_at: Mapped[datetime]        = now_col()

    user: Mapped["User"]                = relationship(back_populates="target_profiles")
    category_filters: Mapped[List["TargetProfileCategoryFilter"]] = relationship(
                                            back_populates="profile", cascade="all, delete-orphan")
    company_filters: Mapped[List["TargetProfileCompanyFilter"]]   = relationship(
                                            back_populates="profile", cascade="all, delete-orphan")
    job_matches: Mapped[List["JobMatch"]] = relationship(back_populates="target_profile")


class TargetProfileCategoryFilter(Base):
    __tablename__ = "target_profile_category_filters"

    id: Mapped[uuid.UUID]           = uuid_pk()
    profile_id: Mapped[uuid.UUID]   = fk("target_profiles.id")
    category_id: Mapped[uuid.UUID]  = fk("company_categories.id")
    filter_type: Mapped[str]        = mapped_column(
                                        SAEnum(*FILTER_TYPES, name="category_filter_type_enum"),
                                        nullable=False)

    __table_args__ = (
        UniqueConstraint("profile_id", "category_id", name="profile_category_unique"),
    )
    profile: Mapped["TargetProfile"]    = relationship(back_populates="category_filters")


class TargetProfileCompanyFilter(Base):
    __tablename__ = "target_profile_company_filters"

    id: Mapped[uuid.UUID]           = uuid_pk()
    profile_id: Mapped[uuid.UUID]   = fk("target_profiles.id")
    company_id: Mapped[uuid.UUID]   = fk("companies.id")
    filter_type: Mapped[str]        = mapped_column(
                                        SAEnum(*FILTER_TYPES, name="category_filter_type_enum"),
                                        nullable=False)

    __table_args__ = (
        UniqueConstraint("profile_id", "company_id", name="profile_company_unique"),
    )
    profile: Mapped["TargetProfile"]    = relationship(back_populates="company_filters")


# =============================================================================
# JOBS
# =============================================================================

class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID]               = uuid_pk()
    company_id: Mapped[uuid.UUID]       = fk("companies.id")
    external_job_id: Mapped[Optional[str]] = mapped_column(String)
    company_name: Mapped[str]           = mapped_column(String, nullable=False)
    title: Mapped[str]                  = mapped_column(String, nullable=False)
    normalized_title: Mapped[Optional[str]] = mapped_column(String)
    location: Mapped[Optional[str]]     = mapped_column(String)
    is_remote: Mapped[Optional[bool]]   = mapped_column(Boolean)
    department: Mapped[Optional[str]]   = mapped_column(String)
    employment_type: Mapped[Optional[str]] = mapped_column(String)
    role_type: Mapped[Optional[str]]    = mapped_column(
                                            SAEnum(*ROLE_TYPES, name="role_type_enum"),
                                            nullable=True)
    description: Mapped[Optional[str]]  = mapped_column(Text)
    application_url: Mapped[str]        = mapped_column(Text, nullable=False)
    source_url: Mapped[Optional[str]]   = mapped_column(Text)
    ats_provider: Mapped[str]           = mapped_column(
                                            SAEnum(*ATS_PROVIDERS, name="ats_provider_enum"),
                                            default="unknown", nullable=False)
    posted_at: Mapped[Optional[date]]   = mapped_column(Date)
    first_seen_at: Mapped[datetime]     = now_col()
    last_seen_at: Mapped[datetime]      = now_col()
    status: Mapped[str]                 = mapped_column(
                                            SAEnum(*JOB_STATUSES, name="job_status_enum"),
                                            default="open", nullable=False)
    raw_data: Mapped[Optional[dict]]    = mapped_column(JSONB)
    created_at: Mapped[datetime]        = now_col()
    updated_at: Mapped[datetime]        = now_col()

    __table_args__ = (
        UniqueConstraint("company_id", "external_job_id", name="jobs_company_external_id_unique"),
    )

    company: Mapped["Company"]          = relationship(back_populates="jobs")
    job_matches: Mapped[List["JobMatch"]] = relationship(back_populates="job")


# =============================================================================
# JOB MATCHES
# =============================================================================

class JobMatch(Base):
    __tablename__ = "job_matches"

    id: Mapped[uuid.UUID]               = uuid_pk()
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    job_id: Mapped[uuid.UUID]           = fk("jobs.id")
    target_profile_id: Mapped[uuid.UUID]= fk("target_profiles.id")

    match_score: Mapped[int]            = mapped_column(SmallInteger, nullable=False)
    title_score: Mapped[Optional[int]]  = mapped_column(SmallInteger)
    role_type_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    location_score: Mapped[Optional[int]]  = mapped_column(SmallInteger)
    keyword_score: Mapped[Optional[int]]   = mapped_column(SmallInteger)
    category_score: Mapped[Optional[int]]  = mapped_column(SmallInteger)
    domain_score: Mapped[Optional[int]]    = mapped_column(SmallInteger)
    priority_score: Mapped[Optional[int]]  = mapped_column(SmallInteger)
    freshness_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    campus_score: Mapped[Optional[int]]    = mapped_column(SmallInteger)

    matched_title_terms: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    matched_keywords: Mapped[List[str]]    = mapped_column(ARRAY(String), default=list)
    matched_location_terms: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    matched_company_categories: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    excluded_terms_found: Mapped[List[str]]   = mapped_column(ARRAY(String), default=list)
    technical_signals_found: Mapped[List[str]]= mapped_column(ARRAY(String), default=list)
    domain_signals_found: Mapped[List[str]]   = mapped_column(ARRAY(String), default=list)

    match_reason: Mapped[Optional[str]] = mapped_column(Text)
    should_alert: Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    alert_sent: Mapped[bool]            = mapped_column(Boolean, default=False, nullable=False)
    alert_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_saved: Mapped[bool]              = mapped_column(Boolean, default=False, nullable=False)
    is_dismissed: Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime]        = now_col()
    updated_at: Mapped[datetime]        = now_col()

    __table_args__ = (
        UniqueConstraint("user_id","job_id","target_profile_id", name="job_match_unique"),
    )

    job: Mapped["Job"]                      = relationship(back_populates="job_matches")
    target_profile: Mapped["TargetProfile"] = relationship(back_populates="job_matches")
    alerts: Mapped[List["Alert"]]           = relationship(back_populates="job_match")


# =============================================================================
# ALERTS
# =============================================================================

class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID]               = uuid_pk()
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    job_match_id: Mapped[uuid.UUID]     = fk("job_matches.id")
    channel: Mapped[str]                = mapped_column(
                                            SAEnum(*ALERT_CHANNELS, name="alert_channel_enum"),
                                            default="email", nullable=False)
    recipient: Mapped[str]              = mapped_column(String, nullable=False)
    subject: Mapped[Optional[str]]      = mapped_column(String)
    body: Mapped[Optional[str]]         = mapped_column(Text)
    status: Mapped[str]                 = mapped_column(
                                            SAEnum(*ALERT_STATUSES, name="alert_status_enum"),
                                            default="pending", nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]]= mapped_column(Text)
    retry_count: Mapped[int]            = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime]        = now_col()

    __table_args__ = (
        UniqueConstraint("job_match_id","channel", name="alert_match_channel_unique"),
    )
    job_match: Mapped["JobMatch"] = relationship(back_populates="alerts")


# =============================================================================
# APPLICATION STATUSES
# =============================================================================

class ApplicationStatus(Base):
    __tablename__ = "application_statuses"

    id: Mapped[uuid.UUID]               = uuid_pk()
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    job_id: Mapped[uuid.UUID]           = fk("jobs.id")
    status: Mapped[str]                 = mapped_column(
                                            SAEnum(*APP_STATUSES, name="application_status_enum"),
                                            default="not_applied", nullable=False)
    applied_at: Mapped[Optional[datetime]]  = mapped_column(DateTime(timezone=True))
    follow_up_date: Mapped[Optional[date]]  = mapped_column(Date)
    notes: Mapped[Optional[str]]            = mapped_column(Text)
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
                                            UUID(as_uuid=True),
                                            ForeignKey("resume_versions.id", ondelete="SET NULL"),
                                            nullable=True)
    created_at: Mapped[datetime]        = now_col()
    updated_at: Mapped[datetime]        = now_col()

    __table_args__ = (
        UniqueConstraint("user_id","job_id", name="application_user_job_unique"),
    )


# =============================================================================
# INGESTION RUNS
# =============================================================================

class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[uuid.UUID]               = uuid_pk()
    triggered_by: Mapped[str]           = mapped_column(String, default="scheduler")
    status: Mapped[str]                 = mapped_column(
                                            SAEnum(*INGEST_RUN_STATUSES, name="ingestion_run_status_enum"),
                                            default="running", nullable=False)
    companies_checked: Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    jobs_found: Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    new_jobs_found: Mapped[int]         = mapped_column(Integer, default=0, nullable=False)
    matches_found: Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    alerts_sent: Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int]            = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[datetime]        = now_col()
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]]        = mapped_column(Text)

    check_logs: Mapped[List["CompanyCheckLog"]] = relationship(back_populates="ingestion_run")


class CompanyCheckLog(Base):
    __tablename__ = "company_check_logs"

    id: Mapped[uuid.UUID]               = uuid_pk()
    ingestion_run_id: Mapped[uuid.UUID] = fk("ingestion_runs.id")
    company_id: Mapped[uuid.UUID]       = mapped_column(
                                            UUID(as_uuid=True),
                                            ForeignKey("companies.id", ondelete="CASCADE"),
                                            nullable=False)
    status: Mapped[str]                 = mapped_column(
                                            SAEnum(*CHECK_STATUSES, name="company_check_status_enum"),
                                            default="success", nullable=False)
    jobs_found: Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    new_jobs_found: Mapped[int]         = mapped_column(Integer, default=0, nullable=False)
    matches_found: Mapped[int]          = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]]= mapped_column(Text)
    started_at: Mapped[datetime]        = now_col()
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    ingestion_run: Mapped["IngestionRun"] = relationship(back_populates="check_logs")


class SourceError(Base):
    __tablename__ = "source_errors"

    id: Mapped[uuid.UUID]               = uuid_pk()
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
                                            UUID(as_uuid=True),
                                            ForeignKey("companies.id", ondelete="SET NULL"),
                                            nullable=True)
    check_log_id: Mapped[Optional[uuid.UUID]] = mapped_column(
                                            UUID(as_uuid=True),
                                            ForeignKey("company_check_logs.id", ondelete="SET NULL"),
                                            nullable=True)
    error_type: Mapped[str]             = mapped_column(String, nullable=False)
    error_message: Mapped[str]          = mapped_column(Text, nullable=False)
    stack_trace: Mapped[Optional[str]]  = mapped_column(Text)
    source_url: Mapped[Optional[str]]   = mapped_column(Text)
    http_status: Mapped[Optional[int]]  = mapped_column(SmallInteger)
    occurred_at: Mapped[datetime]       = now_col()


# =============================================================================
# RESUMES
# =============================================================================

class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID]               = uuid_pk()
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    name: Mapped[str]                   = mapped_column(String, default="Base Resume", nullable=False)
    original_file_url: Mapped[Optional[str]] = mapped_column(Text)
    file_format: Mapped[Optional[str]]  = mapped_column(String)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    parsed_text: Mapped[Optional[str]]  = mapped_column(Text)
    parsed_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    parse_warnings: Mapped[List[str]]   = mapped_column(ARRAY(String), default=list)
    is_base: Mapped[bool]               = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime]        = now_col()
    updated_at: Mapped[datetime]        = now_col()

    user: Mapped["User"]                = relationship(back_populates="resumes")
    versions: Mapped[List["ResumeVersion"]] = relationship(back_populates="resume")


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id: Mapped[uuid.UUID]               = uuid_pk()
    resume_id: Mapped[uuid.UUID]        = fk("resumes.id")
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    version_name: Mapped[str]           = mapped_column(String, nullable=False)
    target_company: Mapped[Optional[str]]    = mapped_column(String)
    target_job_title: Mapped[Optional[str]]  = mapped_column(String)
    target_job_url: Mapped[Optional[str]]    = mapped_column(Text)
    optimized_text: Mapped[Optional[str]]    = mapped_column(Text)
    optimized_json: Mapped[Optional[dict]]   = mapped_column(JSONB)
    ats_score: Mapped[Optional[int]]         = mapped_column(SmallInteger)
    recruiter_scan_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    keyword_coverage_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    metric_strength_score: Mapped[Optional[int]]  = mapped_column(SmallInteger)
    formatting_score: Mapped[Optional[int]]        = mapped_column(SmallInteger)
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
                                            UUID(as_uuid=True),
                                            ForeignKey("resume_job_analyses.id", ondelete="SET NULL"),
                                            nullable=True)
    is_archived: Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime]        = now_col()

    resume: Mapped["Resume"]            = relationship(back_populates="versions")


class ResumeJobAnalysis(Base):
    __tablename__ = "resume_job_analyses"

    id: Mapped[uuid.UUID]               = uuid_pk()
    user_id: Mapped[uuid.UUID]          = fk("users.id")
    resume_id: Mapped[uuid.UUID]        = fk("resumes.id")
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
                                            UUID(as_uuid=True),
                                            ForeignKey("jobs.id", ondelete="SET NULL"),
                                            nullable=True)
    job_description_text: Mapped[Optional[str]] = mapped_column(Text)
    job_title_input: Mapped[Optional[str]]       = mapped_column(String)
    job_company_input: Mapped[Optional[str]]     = mapped_column(String)
    overall_score: Mapped[Optional[int]]         = mapped_column(SmallInteger)
    ats_keyword_score: Mapped[Optional[int]]     = mapped_column(SmallInteger)
    recruiter_scan_score: Mapped[Optional[int]]  = mapped_column(SmallInteger)
    technical_depth_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    quantified_impact_score: Mapped[Optional[int]] = mapped_column(SmallInteger)
    formatting_score: Mapped[Optional[int]]        = mapped_column(SmallInteger)
    recruiter_verdict: Mapped[Optional[str]]       = mapped_column(String)
    recruiter_6s_impression: Mapped[Optional[str]] = mapped_column(Text)
    recruiter_main_reason: Mapped[Optional[str]]   = mapped_column(Text)
    recruiter_biggest_weakness: Mapped[Optional[str]] = mapped_column(Text)
    recruiter_fastest_fix: Mapped[Optional[str]]      = mapped_column(Text)
    required_keywords_found: Mapped[List[str]]    = mapped_column(ARRAY(String), default=list)
    required_keywords_missing: Mapped[List[str]]  = mapped_column(ARRAY(String), default=list)
    preferred_keywords_found: Mapped[List[str]]   = mapped_column(ARRAY(String), default=list)
    preferred_keywords_missing: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    overused_vague_terms: Mapped[List[str]]        = mapped_column(ARRAY(String), default=list)
    must_fix_items: Mapped[Optional[dict]]         = mapped_column(JSONB)
    should_fix_items: Mapped[Optional[dict]]       = mapped_column(JSONB)
    nice_to_have_items: Mapped[Optional[dict]]     = mapped_column(JSONB)
    full_analysis_json: Mapped[Optional[dict]]     = mapped_column(JSONB)
    honesty_warnings: Mapped[List[str]]            = mapped_column(ARRAY(String), default=list)
    created_at: Mapped[datetime]        = now_col()

    keywords: Mapped[List["ResumeKeyword"]]               = relationship(back_populates="analysis")
    bullet_suggestions: Mapped[List["ResumeBulletSuggestion"]] = relationship(back_populates="analysis")


class ResumeKeyword(Base):
    __tablename__ = "resume_keywords"

    id: Mapped[uuid.UUID]               = uuid_pk()
    analysis_id: Mapped[uuid.UUID]      = fk("resume_job_analyses.id")
    keyword: Mapped[str]                = mapped_column(String, nullable=False)
    importance: Mapped[str]             = mapped_column(
                                            SAEnum(*KW_IMPORTANCES, name="keyword_importance_enum"),
                                            default="preferred", nullable=False)
    found_in_resume: Mapped[bool]       = mapped_column(Boolean, default=False, nullable=False)
    current_location: Mapped[Optional[str]]       = mapped_column(String)
    recommended_placement: Mapped[Optional[str]]  = mapped_column(String)
    suggested_wording: Mapped[Optional[str]]      = mapped_column(Text)
    created_at: Mapped[datetime]        = now_col()

    analysis: Mapped["ResumeJobAnalysis"] = relationship(back_populates="keywords")


class ResumeBulletSuggestion(Base):
    __tablename__ = "resume_bullet_suggestions"

    id: Mapped[uuid.UUID]               = uuid_pk()
    analysis_id: Mapped[uuid.UUID]      = fk("resume_job_analyses.id")
    resume_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
                                            UUID(as_uuid=True),
                                            ForeignKey("resume_versions.id", ondelete="SET NULL"),
                                            nullable=True)
    section_name: Mapped[Optional[str]] = mapped_column(String)
    original_bullet: Mapped[str]        = mapped_column(Text, nullable=False)
    problem_description: Mapped[Optional[str]] = mapped_column(Text)
    weak_verb: Mapped[bool]             = mapped_column(Boolean, default=False, nullable=False)
    missing_metric: Mapped[bool]        = mapped_column(Boolean, default=False, nullable=False)
    buries_technology: Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    too_vague: Mapped[bool]             = mapped_column(Boolean, default=False, nullable=False)
    task_not_outcome: Mapped[bool]      = mapped_column(Boolean, default=False, nullable=False)
    improved_bullet: Mapped[str]        = mapped_column(Text, nullable=False)
    why_stronger: Mapped[Optional[str]] = mapped_column(Text)
    keywords_added: Mapped[List[str]]   = mapped_column(ARRAY(String), default=list)
    metrics_added: Mapped[List[str]]    = mapped_column(ARRAY(String), default=list)
    requires_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verification_note: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[int]             = mapped_column(SmallInteger, default=0)
    created_at: Mapped[datetime]        = now_col()

    analysis: Mapped["ResumeJobAnalysis"] = relationship(back_populates="bullet_suggestions")


class ResumeExport(Base):
    __tablename__ = "resume_exports"

    id: Mapped[uuid.UUID]                   = uuid_pk()
    user_id: Mapped[uuid.UUID]              = fk("users.id")
    resume_version_id: Mapped[uuid.UUID]    = fk("resume_versions.id")
    export_format: Mapped[str]              = mapped_column(
                                                SAEnum(*EXPORT_FORMATS, name="resume_export_format_enum"),
                                                default="pdf", nullable=False)
    file_url: Mapped[Optional[str]]         = mapped_column(Text)
    file_size_bytes: Mapped[Optional[int]]  = mapped_column(Integer)
    exported_at: Mapped[datetime]           = now_col()
