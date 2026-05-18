-- =============================================================================
-- PERSONAL JOB HUNTER — Full PostgreSQL / Supabase Database Schema
-- =============================================================================
-- Sections:
--   1.  Extensions
--   2.  Enum Types
--   3.  users
--   4.  company_categories
--   5.  companies
--   6.  company_category_assignments
--   7.  target_profiles
--   8.  target_profile_category_filters
--   9.  target_profile_company_filters
--  10.  jobs
--  11.  job_matches
--  12.  alerts
--  13.  application_statuses
--  14.  ingestion_runs
--  15.  company_check_logs
--  16.  source_errors
--  17.  resumes
--  18.  resume_versions
--  19.  resume_job_analyses
--  20.  resume_keywords
--  21.  resume_bullet_suggestions
--  22.  resume_exports
--  23.  Indexes
--  24.  Row-Level Security (Supabase RLS)
-- =============================================================================


-- =============================================================================
-- 1. EXTENSIONS
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";       -- fast LIKE / ILIKE on titles, keywords
CREATE EXTENSION IF NOT EXISTS "unaccent";       -- accent-insensitive search


-- =============================================================================
-- 2. ENUM TYPES
-- =============================================================================

CREATE TYPE ats_provider_enum AS ENUM (
    'greenhouse',
    'lever',
    'ashby',
    'workday',
    'icims',
    'smartrecruiters',
    'oracle_recruiting',
    'sap_successfactors',
    'custom_html',
    'unknown'
);

CREATE TYPE company_priority_enum AS ENUM (
    'high',
    'medium',
    'low'
);

CREATE TYPE job_status_enum AS ENUM (
    'open',
    'closed',
    'possibly_closed',
    'archived'
);

CREATE TYPE role_type_enum AS ENUM (
    'internship',
    'new_grad',
    'full_time',
    'coop',
    'contract'
);

CREATE TYPE remote_preference_enum AS ENUM (
    'remote',
    'hybrid',
    'onsite',
    'any'
);

CREATE TYPE search_mode_enum AS ENUM (
    'strict_software_ai',
    'balanced',
    'finance_tech_balanced',
    'finance_broad',
    'investment_only',
    'broad'
);

CREATE TYPE application_status_enum AS ENUM (
    'not_applied',
    'saved',
    'applied',
    'interview',
    'rejected',
    'offer',
    'archived'
);

CREATE TYPE alert_channel_enum AS ENUM (
    'email',
    'sms',
    'slack',
    'discord',
    'push'
);

CREATE TYPE alert_status_enum AS ENUM (
    'pending',
    'sent',
    'failed',
    'suppressed'
);

CREATE TYPE ingestion_run_status_enum AS ENUM (
    'running',
    'completed',
    'completed_with_errors',
    'failed'
);

CREATE TYPE company_check_status_enum AS ENUM (
    'success',
    'partial',
    'failed',
    'skipped'
);

CREATE TYPE keyword_importance_enum AS ENUM (
    'required',
    'preferred',
    'nice_to_have'
);

CREATE TYPE recruiter_verdict_enum AS ENUM (
    'strong_move_forward',
    'move_forward',
    'maybe',
    'weak_maybe',
    'likely_reject'
);

CREATE TYPE resume_export_format_enum AS ENUM (
    'pdf',
    'docx',
    'txt',
    'json'
);

CREATE TYPE category_filter_type_enum AS ENUM (
    'included',
    'excluded'
);


-- =============================================================================
-- 3. USERS
-- =============================================================================

CREATE TABLE users (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Auth (mirrors Supabase auth.users — link via this id)
    email                       TEXT NOT NULL UNIQUE,
    full_name                   TEXT,

    -- Academic background
    graduation_year             SMALLINT,
    school                      TEXT,
    major                       TEXT,
    minor                       TEXT,

    -- Preferences stored as arrays for simplicity in MVP
    preferred_locations         TEXT[]          DEFAULT '{}',
    preferred_role_types        role_type_enum[] DEFAULT '{}',
    preferred_company_categories TEXT[]          DEFAULT '{}',   -- mirrors category slugs

    -- Alert preferences
    alert_email                 TEXT,
    alert_frequency             TEXT            DEFAULT 'daily',   -- daily | realtime
    minimum_match_score         SMALLINT        DEFAULT 70
                                    CHECK (minimum_match_score BETWEEN 0 AND 100),
    notifications_enabled       BOOLEAN         DEFAULT TRUE,

    -- Resume export preferences
    resume_export_format        resume_export_format_enum DEFAULT 'pdf',

    created_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE users IS
    'One row per registered user. id matches Supabase auth.users.id.';

COMMENT ON COLUMN users.alert_email IS
    'Override email for alerts; falls back to users.email when NULL.';


-- =============================================================================
-- 4. COMPANY CATEGORIES
-- =============================================================================
-- Seed data provided below the table definition.

CREATE TABLE company_categories (
    id          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug        TEXT    NOT NULL UNIQUE,   -- e.g. "big_tech", "hedge_fund"
    name        TEXT    NOT NULL,          -- e.g. "Big Tech", "Hedge Fund"
    description TEXT,
    sort_order  SMALLINT DEFAULT 0,        -- for display ordering

    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE company_categories IS
    'Master list of company category labels. Many-to-many with companies.';

-- Seed all categories from spec
INSERT INTO company_categories (slug, name, sort_order) VALUES
    ('big_tech',                    'Big Tech',                         1),
    ('magnificent_7',               'Magnificent 7',                    2),
    ('nasdaq_100',                  'Nasdaq-100',                       3),
    ('saas',                        'SaaS',                             4),
    ('software_company',            'Software Company',                 5),
    ('data_company',                'Data Company',                     6),
    ('cloud_infrastructure',        'Cloud Infrastructure',             7),
    ('ai_ml_company',               'AI/ML Company',                    8),
    ('semiconductor',               'Semiconductor / AI Infrastructure',9),
    ('cybersecurity',               'Cybersecurity',                    10),
    ('financial_technology',        'Financial Technology',             11),
    ('banking_technology',          'Banking Technology',               12),
    ('capital_markets_technology',  'Capital Markets Technology',       13),
    ('exchange_market_infra',       'Exchange / Market Infrastructure', 14),
    ('financial_data_provider',     'Financial Data Provider',          15),
    ('private_equity',              'Private Equity',                   16),
    ('alt_asset_management',        'Alternative Asset Management',     17),
    ('hedge_fund',                  'Hedge Fund',                       18),
    ('multi_manager_hedge_fund',    'Multi-Manager Hedge Fund',         19),
    ('asset_management_technology', 'Asset Management Technology',      20),
    ('systematic_investing',        'Systematic Investing',             21),
    ('quant_trading',               'Quant Trading',                    22),
    ('algorithmic_trading',         'Algorithmic Trading',              23),
    ('high_frequency_trading',      'High-Frequency Trading',           24),
    ('proprietary_trading',         'Proprietary Trading',              25),
    ('market_making',               'Market Making',                    26),
    ('trading_infrastructure',      'Trading Infrastructure',           27),
    ('portfolio_company_technology','Portfolio Company Technology',     28),
    ('startup',                     'Startup',                          29),
    ('enterprise_software',         'Enterprise Software',              30);


-- =============================================================================
-- 5. COMPANIES
-- =============================================================================

CREATE TABLE companies (
    id                          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name                        TEXT    NOT NULL,
    domain                      TEXT,                    -- e.g. "stripe.com"
    careers_url                 TEXT,                    -- user-supplied careers page

    -- ATS detection results
    ats_provider                ats_provider_enum NOT NULL DEFAULT 'unknown',
    ats_slug                    TEXT,                    -- board token / employer slug
    source_url                  TEXT,                    -- resolved feed URL used by adapter

    -- Detection metadata
    ats_detection_confidence    NUMERIC(4,3),            -- 0.000–1.000
    ats_detection_warning       TEXT,

    -- User settings
    priority                    company_priority_enum NOT NULL DEFAULT 'medium',
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    notes                       TEXT,

    -- Monitoring state
    last_checked_at             TIMESTAMPTZ,
    last_successful_check_at    TIMESTAMPTZ,
    last_error                  TEXT,
    consecutive_errors          SMALLINT NOT NULL DEFAULT 0,

    -- Aggregate counters (denormalized for dashboard speed)
    total_jobs_found            INTEGER NOT NULL DEFAULT 0,
    total_matching_jobs         INTEGER NOT NULL DEFAULT 0,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT companies_user_name_unique UNIQUE (user_id, name)
);

COMMENT ON TABLE companies IS
    'One row per company in a user''s watchlist.';

COMMENT ON COLUMN companies.ats_slug IS
    'Greenhouse board token, Lever company slug, Ashby subdomain, etc.';

COMMENT ON COLUMN companies.source_url IS
    'The exact URL the ingestion adapter polls — may differ from careers_url.';


-- =============================================================================
-- 6. COMPANY CATEGORY ASSIGNMENTS
-- =============================================================================

CREATE TABLE company_category_assignments (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    category_id         UUID NOT NULL REFERENCES company_categories(id) ON DELETE CASCADE,
    assigned_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT company_category_unique UNIQUE (company_id, category_id)
);

COMMENT ON TABLE company_category_assignments IS
    'Many-to-many join between companies and company_categories.';


-- =============================================================================
-- 7. TARGET PROFILES
-- =============================================================================

CREATE TABLE target_profiles (
    id                          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name                        TEXT    NOT NULL,

    -- Title / keyword filters (stored as arrays)
    desired_titles              TEXT[]  NOT NULL DEFAULT '{}',
    desired_keywords            TEXT[]  NOT NULL DEFAULT '{}',
    desired_locations           TEXT[]  NOT NULL DEFAULT '{}',
    excluded_keywords           TEXT[]  NOT NULL DEFAULT '{}',

    -- Role type and work style
    role_types                  role_type_enum[] NOT NULL DEFAULT '{}',
    remote_preference           remote_preference_enum NOT NULL DEFAULT 'any',

    -- Matching configuration
    minimum_match_score         SMALLINT NOT NULL DEFAULT 70
                                    CHECK (minimum_match_score BETWEEN 0 AND 100),
    search_mode                 search_mode_enum NOT NULL DEFAULT 'balanced',

    -- Alert flag
    alerts_enabled              BOOLEAN NOT NULL DEFAULT TRUE,

    -- Soft-delete / archive
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE target_profiles IS
    'A named set of preferences used by the matching engine. Users may have many.';


-- =============================================================================
-- 8. TARGET PROFILE CATEGORY FILTERS
-- =============================================================================

CREATE TABLE target_profile_category_filters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id      UUID NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,
    category_id     UUID NOT NULL REFERENCES company_categories(id) ON DELETE CASCADE,
    filter_type     category_filter_type_enum NOT NULL,  -- 'included' or 'excluded'

    CONSTRAINT profile_category_unique UNIQUE (profile_id, category_id)
);

COMMENT ON TABLE target_profile_category_filters IS
    'Per-profile company category include/exclude rules.';


-- =============================================================================
-- 9. TARGET PROFILE COMPANY FILTERS
-- =============================================================================

CREATE TABLE target_profile_company_filters (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    profile_id      UUID NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    filter_type     category_filter_type_enum NOT NULL,  -- 'included' or 'excluded'

    CONSTRAINT profile_company_unique UNIQUE (profile_id, company_id)
);

COMMENT ON TABLE target_profile_company_filters IS
    'Per-profile company-level include/exclude overrides.';


-- =============================================================================
-- 10. JOBS
-- =============================================================================

CREATE TABLE jobs (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID    NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    -- Identity
    external_job_id     TEXT,                    -- ID from ATS source
    company_name        TEXT    NOT NULL,        -- denormalized for query convenience
    title               TEXT    NOT NULL,
    normalized_title    TEXT,                    -- after abbreviation expansion

    -- Location
    location            TEXT,
    is_remote           BOOLEAN,

    -- Classification
    department          TEXT,
    employment_type     TEXT,                    -- full-time, part-time, contract
    role_type           role_type_enum,

    -- Content
    description         TEXT,
    application_url     TEXT    NOT NULL,
    source_url          TEXT,
    ats_provider        ats_provider_enum NOT NULL DEFAULT 'unknown',

    -- Lifecycle
    posted_at           DATE,
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status              job_status_enum NOT NULL DEFAULT 'open',

    -- Raw payload from ATS (for debugging / re-parsing)
    raw_data            JSONB,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Deduplication: one row per (company, external_id) or (company, title+location+url)
    CONSTRAINT jobs_company_external_id_unique UNIQUE (company_id, external_job_id)
);

COMMENT ON TABLE jobs IS
    'Every job posting ever collected, across all users'' companies.';

COMMENT ON COLUMN jobs.normalized_title IS
    'Lowercase, abbreviation-expanded title used by the matching engine.';

COMMENT ON COLUMN jobs.raw_data IS
    'Full ATS response payload preserved for re-normalization and debugging.';


-- =============================================================================
-- 11. JOB MATCHES
-- =============================================================================

CREATE TABLE job_matches (
    id                          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id                      UUID    NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    target_profile_id           UUID    NOT NULL REFERENCES target_profiles(id) ON DELETE CASCADE,

    -- Scores
    match_score                 SMALLINT NOT NULL
                                    CHECK (match_score BETWEEN 0 AND 100),
    title_score                 SMALLINT,
    role_type_score             SMALLINT,
    location_score              SMALLINT,
    keyword_score               SMALLINT,
    category_score              SMALLINT,
    domain_score                SMALLINT,
    priority_score              SMALLINT,
    freshness_score             SMALLINT,
    campus_score                SMALLINT,

    -- Match detail arrays
    matched_title_terms         TEXT[]  DEFAULT '{}',
    matched_keywords            TEXT[]  DEFAULT '{}',
    matched_location_terms      TEXT[]  DEFAULT '{}',
    matched_company_categories  TEXT[]  DEFAULT '{}',
    excluded_terms_found        TEXT[]  DEFAULT '{}',
    technical_signals_found     TEXT[]  DEFAULT '{}',
    domain_signals_found        TEXT[]  DEFAULT '{}',

    -- Human-readable explanation
    match_reason                TEXT,

    -- Alert tracking
    should_alert                BOOLEAN NOT NULL DEFAULT FALSE,
    alert_sent                  BOOLEAN NOT NULL DEFAULT FALSE,
    alert_sent_at               TIMESTAMPTZ,

    -- User actions
    is_saved                    BOOLEAN NOT NULL DEFAULT FALSE,
    is_dismissed                BOOLEAN NOT NULL DEFAULT FALSE,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT job_match_unique UNIQUE (user_id, job_id, target_profile_id)
);

COMMENT ON TABLE job_matches IS
    'Output of the matching engine: one row per (user, job, profile) triple.';

COMMENT ON COLUMN job_matches.match_reason IS
    'Plain-English explanation generated by the matching engine, shown in the dashboard.';


-- =============================================================================
-- 12. ALERTS
-- =============================================================================

CREATE TABLE alerts (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_match_id    UUID    NOT NULL REFERENCES job_matches(id) ON DELETE CASCADE,

    channel         alert_channel_enum  NOT NULL DEFAULT 'email',
    recipient       TEXT    NOT NULL,   -- email address, phone, webhook URL
    subject         TEXT,
    body            TEXT,

    status          alert_status_enum   NOT NULL DEFAULT 'pending',
    sent_at         TIMESTAMPTZ,
    error_message   TEXT,
    retry_count     SMALLINT            NOT NULL DEFAULT 0,

    created_at      TIMESTAMPTZ         NOT NULL DEFAULT NOW(),

    -- One alert per (job_match, channel) — prevents duplicates
    CONSTRAINT alert_match_channel_unique UNIQUE (job_match_id, channel)
);

COMMENT ON TABLE alerts IS
    'Outbound notification records. Unique per (job_match, channel).';


-- =============================================================================
-- 13. APPLICATION STATUSES
-- =============================================================================

CREATE TABLE application_statuses (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id              UUID    NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,

    status              application_status_enum NOT NULL DEFAULT 'not_applied',
    applied_at          TIMESTAMPTZ,
    follow_up_date      DATE,
    notes               TEXT,

    -- Link to which resume version was used
    resume_version_id   UUID,    -- FK added after resume_versions table below

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT application_user_job_unique UNIQUE (user_id, job_id)
);

COMMENT ON TABLE application_statuses IS
    'User-managed application tracker. One row per (user, job).';


-- =============================================================================
-- 14. INGESTION RUNS
-- =============================================================================

CREATE TABLE ingestion_runs (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),

    triggered_by        TEXT    DEFAULT 'scheduler',  -- scheduler | manual | api
    status              ingestion_run_status_enum NOT NULL DEFAULT 'running',

    companies_checked   INTEGER NOT NULL DEFAULT 0,
    jobs_found          INTEGER NOT NULL DEFAULT 0,
    new_jobs_found      INTEGER NOT NULL DEFAULT 0,
    matches_found       INTEGER NOT NULL DEFAULT 0,
    alerts_sent         INTEGER NOT NULL DEFAULT 0,
    error_count         INTEGER NOT NULL DEFAULT 0,

    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ,

    notes               TEXT    -- e.g. "manual run for company X"
);

COMMENT ON TABLE ingestion_runs IS
    'One row per scheduler or manual ingestion run across all companies.';


-- =============================================================================
-- 15. COMPANY CHECK LOGS
-- =============================================================================

CREATE TABLE company_check_logs (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    ingestion_run_id    UUID    NOT NULL REFERENCES ingestion_runs(id) ON DELETE CASCADE,
    company_id          UUID    NOT NULL REFERENCES companies(id) ON DELETE CASCADE,

    status              company_check_status_enum NOT NULL DEFAULT 'success',
    jobs_found          INTEGER NOT NULL DEFAULT 0,
    new_jobs_found      INTEGER NOT NULL DEFAULT 0,
    matches_found       INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,

    started_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at         TIMESTAMPTZ
);

COMMENT ON TABLE company_check_logs IS
    'Per-company result within a single ingestion run.';


-- =============================================================================
-- 16. SOURCE ERRORS
-- =============================================================================

CREATE TABLE source_errors (
    id              UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID    REFERENCES companies(id) ON DELETE SET NULL,
    check_log_id    UUID    REFERENCES company_check_logs(id) ON DELETE SET NULL,

    error_type      TEXT    NOT NULL,   -- e.g. "http_error", "parse_error", "timeout"
    error_message   TEXT    NOT NULL,
    stack_trace     TEXT,
    source_url      TEXT,
    http_status     SMALLINT,

    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE source_errors IS
    'Detailed error log for failed or partial ingestion attempts.';


-- =============================================================================
-- 17. RESUMES
-- =============================================================================

CREATE TABLE resumes (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    name                TEXT    NOT NULL DEFAULT 'Base Resume',
    original_file_url   TEXT,       -- Supabase Storage path
    file_format         TEXT,       -- pdf | docx | txt | latex
    file_size_bytes     INTEGER,

    -- Parsed output
    parsed_text         TEXT,       -- full plain-text extraction
    parsed_json         JSONB,      -- structured sections: education, experience, etc.

    -- Parse quality flags
    parse_warnings      TEXT[],

    is_base             BOOLEAN NOT NULL DEFAULT TRUE,   -- user's canonical resume
    is_archived         BOOLEAN NOT NULL DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE resumes IS
    'A user''s uploaded resume file plus its parsed content.';

COMMENT ON COLUMN resumes.parsed_json IS
    'Structured sections: { contact, education, experience, projects, skills, certifications, leadership, awards }';


-- =============================================================================
-- 18. RESUME VERSIONS
-- =============================================================================

CREATE TABLE resume_versions (
    id                      UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    resume_id               UUID    NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    user_id                 UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    version_name            TEXT    NOT NULL,
    target_company          TEXT,
    target_job_title        TEXT,
    target_job_url          TEXT,

    -- Content
    optimized_text          TEXT,
    optimized_json          JSONB,

    -- Score summary at time of generation
    ats_score               SMALLINT CHECK (ats_score BETWEEN 0 AND 100),
    recruiter_scan_score    SMALLINT CHECK (recruiter_scan_score BETWEEN 0 AND 100),
    keyword_coverage_score  SMALLINT CHECK (keyword_coverage_score BETWEEN 0 AND 100),
    metric_strength_score   SMALLINT CHECK (metric_strength_score BETWEEN 0 AND 100),
    formatting_score        SMALLINT CHECK (formatting_score BETWEEN 0 AND 100),

    -- Link back to the analysis that produced this version
    analysis_id             UUID,   -- FK added after resume_job_analyses below

    is_archived             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE resume_versions IS
    'Job-specific optimized resume snapshots derived from a base resume.';


-- =============================================================================
-- 19. RESUME JOB ANALYSES
-- =============================================================================

CREATE TABLE resume_job_analyses (
    id                          UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id                   UUID    NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    job_id                      UUID    REFERENCES jobs(id) ON DELETE SET NULL,

    -- Job description may be pasted manually (no job_id required)
    job_description_text        TEXT,
    job_title_input             TEXT,
    job_company_input           TEXT,

    -- Overall scores
    overall_score               SMALLINT CHECK (overall_score BETWEEN 0 AND 100),
    ats_keyword_score           SMALLINT CHECK (ats_keyword_score BETWEEN 0 AND 100),
    recruiter_scan_score        SMALLINT CHECK (recruiter_scan_score BETWEEN 0 AND 100),
    technical_depth_score       SMALLINT CHECK (technical_depth_score BETWEEN 0 AND 100),
    quantified_impact_score     SMALLINT CHECK (quantified_impact_score BETWEEN 0 AND 100),
    formatting_score            SMALLINT CHECK (formatting_score BETWEEN 0 AND 100),

    -- Recruiter simulation
    recruiter_verdict           recruiter_verdict_enum,
    recruiter_6s_impression     TEXT,   -- 1–2 sentence first impression
    recruiter_main_reason       TEXT,   -- move forward or reject reason
    recruiter_biggest_weakness  TEXT,
    recruiter_fastest_fix       TEXT,

    -- Keyword lists (arrays of keyword strings)
    required_keywords_found     TEXT[]  DEFAULT '{}',
    required_keywords_missing   TEXT[]  DEFAULT '{}',
    preferred_keywords_found    TEXT[]  DEFAULT '{}',
    preferred_keywords_missing  TEXT[]  DEFAULT '{}',
    overused_vague_terms        TEXT[]  DEFAULT '{}',

    -- Recommended priority changes
    must_fix_items              JSONB,  -- [{ section, description }]
    should_fix_items            JSONB,
    nice_to_have_items          JSONB,

    -- Full analysis output
    full_analysis_json          JSONB,

    -- Honesty / verification warnings
    honesty_warnings            TEXT[]  DEFAULT '{}',

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE resume_job_analyses IS
    'One analysis run per (user, resume, job). Stores all scoring and diagnostic output.';

-- Add FK from resume_versions.analysis_id back to resume_job_analyses
ALTER TABLE resume_versions
    ADD CONSTRAINT fk_resume_version_analysis
    FOREIGN KEY (analysis_id) REFERENCES resume_job_analyses(id) ON DELETE SET NULL;


-- =============================================================================
-- 20. RESUME KEYWORDS
-- =============================================================================

CREATE TABLE resume_keywords (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id         UUID    NOT NULL REFERENCES resume_job_analyses(id) ON DELETE CASCADE,

    keyword             TEXT    NOT NULL,
    importance          keyword_importance_enum NOT NULL DEFAULT 'preferred',
    found_in_resume     BOOLEAN NOT NULL DEFAULT FALSE,
    current_location    TEXT,                   -- e.g. "Skills section", "Project 2"
    recommended_placement TEXT,                 -- e.g. "Skills section, Experience bullet"
    suggested_wording   TEXT,                   -- how to work it in naturally

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE resume_keywords IS
    'Per-keyword ATS coverage breakdown from an analysis run.';


-- =============================================================================
-- 21. RESUME BULLET SUGGESTIONS
-- =============================================================================

CREATE TABLE resume_bullet_suggestions (
    id                      UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id             UUID    NOT NULL REFERENCES resume_job_analyses(id) ON DELETE CASCADE,
    resume_version_id       UUID    REFERENCES resume_versions(id) ON DELETE SET NULL,

    -- Source
    section_name            TEXT,           -- e.g. "Experience — Acme Corp"
    original_bullet         TEXT    NOT NULL,

    -- Diagnosis
    problem_description     TEXT,           -- plain-English weakness
    weak_verb               BOOLEAN NOT NULL DEFAULT FALSE,
    missing_metric          BOOLEAN NOT NULL DEFAULT FALSE,
    buries_technology       BOOLEAN NOT NULL DEFAULT FALSE,
    too_vague               BOOLEAN NOT NULL DEFAULT FALSE,
    task_not_outcome        BOOLEAN NOT NULL DEFAULT FALSE,

    -- Improvement
    improved_bullet         TEXT    NOT NULL,
    why_stronger            TEXT,
    keywords_added          TEXT[]  DEFAULT '{}',
    metrics_added           TEXT[]  DEFAULT '{}',    -- may include "[X%]" placeholders

    -- Honesty flags
    requires_verification   BOOLEAN NOT NULL DEFAULT FALSE,
    verification_note       TEXT,   -- e.g. "Replace [X%] with actual measured value"

    -- Sort order within the analysis
    sort_order              SMALLINT DEFAULT 0,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE resume_bullet_suggestions IS
    'Per-bullet improvement suggestions generated by the Resume Intelligence Engine.';

-- Add FK from application_statuses.resume_version_id
ALTER TABLE application_statuses
    ADD CONSTRAINT fk_application_resume_version
    FOREIGN KEY (resume_version_id) REFERENCES resume_versions(id) ON DELETE SET NULL;


-- =============================================================================
-- 22. RESUME EXPORTS
-- =============================================================================

CREATE TABLE resume_exports (
    id                  UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID    NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_version_id   UUID    NOT NULL REFERENCES resume_versions(id) ON DELETE CASCADE,

    export_format       resume_export_format_enum NOT NULL DEFAULT 'pdf',
    file_url            TEXT,       -- Supabase Storage path
    file_size_bytes     INTEGER,
    exported_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE resume_exports IS
    'Record of every file export generated from an optimized resume version.';


-- =============================================================================
-- 23. INDEXES
-- =============================================================================

-- users
CREATE UNIQUE INDEX idx_users_email ON users(email);

-- companies
CREATE INDEX idx_companies_user_id         ON companies(user_id);
CREATE INDEX idx_companies_is_active       ON companies(is_active);
CREATE INDEX idx_companies_ats_provider    ON companies(ats_provider);
CREATE INDEX idx_companies_last_checked_at ON companies(last_checked_at);
CREATE INDEX idx_companies_priority        ON companies(priority);

-- company_category_assignments
CREATE INDEX idx_cca_company_id  ON company_category_assignments(company_id);
CREATE INDEX idx_cca_category_id ON company_category_assignments(category_id);

-- target_profiles
CREATE INDEX idx_target_profiles_user_id   ON target_profiles(user_id);
CREATE INDEX idx_target_profiles_is_active ON target_profiles(is_active);

-- target_profile_category_filters
CREATE INDEX idx_tpcf_profile_id ON target_profile_category_filters(profile_id);

-- target_profile_company_filters
CREATE INDEX idx_tpcof_profile_id  ON target_profile_company_filters(profile_id);
CREATE INDEX idx_tpcof_company_id  ON target_profile_company_filters(company_id);

-- jobs
CREATE INDEX idx_jobs_company_id         ON jobs(company_id);
CREATE INDEX idx_jobs_status             ON jobs(status);
CREATE INDEX idx_jobs_first_seen_at      ON jobs(first_seen_at DESC);
CREATE INDEX idx_jobs_posted_at          ON jobs(posted_at DESC);
CREATE INDEX idx_jobs_normalized_title   ON jobs USING gin(to_tsvector('english', COALESCE(normalized_title, '')));
CREATE INDEX idx_jobs_description_fts    ON jobs USING gin(to_tsvector('english', COALESCE(description, '')));
CREATE INDEX idx_jobs_title_trgm         ON jobs USING gin(title gin_trgm_ops);

-- Partial index for open jobs only (most common query)
CREATE INDEX idx_jobs_open ON jobs(company_id, first_seen_at DESC)
    WHERE status = 'open';

-- job_matches
CREATE INDEX idx_job_matches_user_id          ON job_matches(user_id);
CREATE INDEX idx_job_matches_job_id           ON job_matches(job_id);
CREATE INDEX idx_job_matches_profile_id       ON job_matches(target_profile_id);
CREATE INDEX idx_job_matches_score            ON job_matches(match_score DESC);
CREATE INDEX idx_job_matches_should_alert     ON job_matches(should_alert, alert_sent)
    WHERE should_alert = TRUE AND alert_sent = FALSE;

-- alerts
CREATE INDEX idx_alerts_user_id       ON alerts(user_id);
CREATE INDEX idx_alerts_status        ON alerts(status);
CREATE INDEX idx_alerts_sent_at       ON alerts(sent_at DESC);

-- application_statuses
CREATE INDEX idx_applications_user_id ON application_statuses(user_id);
CREATE INDEX idx_applications_status  ON application_statuses(status);
CREATE INDEX idx_applications_job_id  ON application_statuses(job_id);

-- ingestion_runs
CREATE INDEX idx_ingestion_runs_started_at ON ingestion_runs(started_at DESC);
CREATE INDEX idx_ingestion_runs_status     ON ingestion_runs(status);

-- company_check_logs
CREATE INDEX idx_ccl_run_id     ON company_check_logs(ingestion_run_id);
CREATE INDEX idx_ccl_company_id ON company_check_logs(company_id);
CREATE INDEX idx_ccl_status     ON company_check_logs(status);

-- source_errors
CREATE INDEX idx_source_errors_company_id  ON source_errors(company_id);
CREATE INDEX idx_source_errors_occurred_at ON source_errors(occurred_at DESC);

-- resumes
CREATE INDEX idx_resumes_user_id ON resumes(user_id);
CREATE INDEX idx_resumes_is_base ON resumes(user_id, is_base) WHERE is_base = TRUE;

-- resume_versions
CREATE INDEX idx_resume_versions_resume_id ON resume_versions(resume_id);
CREATE INDEX idx_resume_versions_user_id   ON resume_versions(user_id);

-- resume_job_analyses
CREATE INDEX idx_rja_user_id    ON resume_job_analyses(user_id);
CREATE INDEX idx_rja_resume_id  ON resume_job_analyses(resume_id);
CREATE INDEX idx_rja_job_id     ON resume_job_analyses(job_id);
CREATE INDEX idx_rja_created_at ON resume_job_analyses(created_at DESC);

-- resume_keywords
CREATE INDEX idx_rk_analysis_id     ON resume_keywords(analysis_id);
CREATE INDEX idx_rk_found_in_resume ON resume_keywords(analysis_id, found_in_resume);

-- resume_bullet_suggestions
CREATE INDEX idx_rbs_analysis_id ON resume_bullet_suggestions(analysis_id);

-- resume_exports
CREATE INDEX idx_re_user_id           ON resume_exports(user_id);
CREATE INDEX idx_re_resume_version_id ON resume_exports(resume_version_id);


-- =============================================================================
-- 24. ROW-LEVEL SECURITY (Supabase RLS)
-- =============================================================================
-- Enable RLS on every user-data table so that authenticated users can only
-- read and modify their own rows.  The policy predicate uses auth.uid()
-- which Supabase populates automatically from the JWT.
-- =============================================================================

ALTER TABLE users                           ENABLE ROW LEVEL SECURITY;
ALTER TABLE companies                       ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_category_assignments    ENABLE ROW LEVEL SECURITY;
ALTER TABLE target_profiles                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE target_profile_category_filters ENABLE ROW LEVEL SECURITY;
ALTER TABLE target_profile_company_filters  ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs                            ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_matches                     ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts                          ENABLE ROW LEVEL SECURITY;
ALTER TABLE application_statuses            ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingestion_runs                  ENABLE ROW LEVEL SECURITY;
ALTER TABLE company_check_logs              ENABLE ROW LEVEL SECURITY;
ALTER TABLE source_errors                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE resumes                         ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_versions                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_job_analyses             ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_keywords                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_bullet_suggestions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE resume_exports                  ENABLE ROW LEVEL SECURITY;

-- company_categories is read-only shared data — no RLS needed (public read)
-- No ENABLE on company_categories intentionally.

-- ---- users ----
CREATE POLICY users_select_own ON users
    FOR SELECT USING (id = auth.uid());

CREATE POLICY users_update_own ON users
    FOR UPDATE USING (id = auth.uid());

-- ---- companies ----
CREATE POLICY companies_all_own ON companies
    FOR ALL USING (user_id = auth.uid());

-- ---- company_category_assignments ----
-- User can manage assignments for their own companies
CREATE POLICY cca_all_own ON company_category_assignments
    FOR ALL USING (
        company_id IN (SELECT id FROM companies WHERE user_id = auth.uid())
    );

-- ---- target_profiles ----
CREATE POLICY tp_all_own ON target_profiles
    FOR ALL USING (user_id = auth.uid());

-- ---- target_profile_category_filters ----
CREATE POLICY tpcf_all_own ON target_profile_category_filters
    FOR ALL USING (
        profile_id IN (SELECT id FROM target_profiles WHERE user_id = auth.uid())
    );

-- ---- target_profile_company_filters ----
CREATE POLICY tpcof_all_own ON target_profile_company_filters
    FOR ALL USING (
        profile_id IN (SELECT id FROM target_profiles WHERE user_id = auth.uid())
    );

-- ---- jobs ----
-- Jobs belong to companies which belong to users
CREATE POLICY jobs_select_own ON jobs
    FOR SELECT USING (
        company_id IN (SELECT id FROM companies WHERE user_id = auth.uid())
    );

-- Backend service role updates job rows (use service_role key in ingestion worker)
-- Frontend / user cannot directly mutate jobs

-- ---- job_matches ----
CREATE POLICY job_matches_all_own ON job_matches
    FOR ALL USING (user_id = auth.uid());

-- ---- alerts ----
CREATE POLICY alerts_all_own ON alerts
    FOR ALL USING (user_id = auth.uid());

-- ---- application_statuses ----
CREATE POLICY applications_all_own ON application_statuses
    FOR ALL USING (user_id = auth.uid());

-- ---- ingestion_runs ----
-- Only readable by the user who owns the companies; inserts done by service role
CREATE POLICY ingestion_runs_select ON ingestion_runs
    FOR SELECT USING (TRUE);   -- all authenticated users can read run logs in MVP

-- ---- company_check_logs ----
CREATE POLICY ccl_select_own ON company_check_logs
    FOR SELECT USING (
        company_id IN (SELECT id FROM companies WHERE user_id = auth.uid())
    );

-- ---- source_errors ----
CREATE POLICY source_errors_select_own ON source_errors
    FOR SELECT USING (
        company_id IN (SELECT id FROM companies WHERE user_id = auth.uid())
    );

-- ---- resumes ----
CREATE POLICY resumes_all_own ON resumes
    FOR ALL USING (user_id = auth.uid());

-- ---- resume_versions ----
CREATE POLICY rv_all_own ON resume_versions
    FOR ALL USING (user_id = auth.uid());

-- ---- resume_job_analyses ----
CREATE POLICY rja_all_own ON resume_job_analyses
    FOR ALL USING (user_id = auth.uid());

-- ---- resume_keywords ----
CREATE POLICY rk_all_own ON resume_keywords
    FOR ALL USING (
        analysis_id IN (SELECT id FROM resume_job_analyses WHERE user_id = auth.uid())
    );

-- ---- resume_bullet_suggestions ----
CREATE POLICY rbs_all_own ON resume_bullet_suggestions
    FOR ALL USING (
        analysis_id IN (SELECT id FROM resume_job_analyses WHERE user_id = auth.uid())
    );

-- ---- resume_exports ----
CREATE POLICY re_all_own ON resume_exports
    FOR ALL USING (user_id = auth.uid());


-- =============================================================================
-- HELPER: updated_at trigger (reusable)
-- =============================================================================

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_companies_updated_at
    BEFORE UPDATE ON companies
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_target_profiles_updated_at
    BEFORE UPDATE ON target_profiles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_job_matches_updated_at
    BEFORE UPDATE ON job_matches
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_application_statuses_updated_at
    BEFORE UPDATE ON application_statuses
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_resumes_updated_at
    BEFORE UPDATE ON resumes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- =============================================================================
-- END OF SCHEMA
-- =============================================================================
