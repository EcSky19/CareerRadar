// ── Core entity types matching the backend API responses ──────────────────────

export type AtsProvider =
  | 'greenhouse' | 'lever' | 'ashby' | 'workday' | 'icims'
  | 'smartrecruiters' | 'custom_html' | 'unknown'

export type CompanyPriority = 'high' | 'medium' | 'low'

export interface Category {
  id: string
  slug: string
  name: string
}

export interface Company {
  id: string
  user_id: string
  name: string
  domain?: string
  careers_url?: string
  ats_provider: AtsProvider
  ats_slug?: string
  source_url?: string
  ats_detection_confidence?: number
  ats_detection_warning?: string
  priority: CompanyPriority
  is_active: boolean
  notes?: string
  last_checked_at?: string
  last_successful_check_at?: string
  last_error?: string
  consecutive_errors: number
  total_jobs_found: number
  total_matching_jobs: number
  categories: Category[]
  created_at: string
  updated_at: string
}

export type RoleType = 'internship' | 'new_grad' | 'full_time' | 'coop' | 'contract'
export type SearchMode = 'strict_software_ai' | 'balanced' | 'finance_tech_balanced' | 'finance_broad' | 'investment_only' | 'broad'

export interface TargetProfile {
  id: string
  user_id: string
  name: string
  desired_titles: string[]
  desired_keywords: string[]
  desired_locations: string[]
  excluded_keywords: string[]
  role_types: RoleType[]
  remote_preference: 'remote' | 'hybrid' | 'onsite' | 'any'
  minimum_match_score: number
  search_mode: SearchMode
  alerts_enabled: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export type JobStatus = 'open' | 'closed' | 'possibly_closed' | 'archived'
export type ApplicationStatus = 'not_applied' | 'saved' | 'applied' | 'interview' | 'rejected' | 'offer' | 'archived'

export interface JobMatch {
  id: string
  job_id: string
  title: string
  company_name: string
  location?: string
  is_remote?: boolean
  application_url: string
  posted_at?: string
  job_status: JobStatus
  match_score: number
  match_reason?: string
  matched_title_terms: string[]
  matched_keywords: string[]
  domain_signals_found: string[]
  profile_name: string
  profile_id: string
  is_saved: boolean
  is_dismissed: boolean
  alert_sent: boolean
  application_status: ApplicationStatus
  first_seen_at: string
}

export interface TrackedApplication {
  id: string
  job_id: string
  title: string
  company_name: string
  location?: string
  application_url: string
  status: ApplicationStatus
  applied_at?: string
  follow_up_date?: string
  notes?: string
  updated_at: string
}

export interface MatchStats {
  total_matches: number
  high_score_matches: number
  new_today: number
  applied_count: number
}

export interface IngestionRun {
  id: string
  triggered_by: string
  status: 'running' | 'completed' | 'completed_with_errors' | 'failed'
  companies_checked: number
  new_jobs_found: number
  matches_found: number
  alerts_sent: number
  error_count: number
  started_at: string
  finished_at?: string
  duration_seconds?: number
}

export interface Resume {
  id: string
  name: string
  file_format?: string
  is_base: boolean
  parse_warnings: string[]
  created_at: string
}

export interface AnalysisScores {
  overall: number
  ats_keyword: number
  recruiter_scan: number
  technical_depth: number
  quantified_impact: number
  formatting: number
}

export interface AnalysisResult {
  analysis_id: string
  scores: AnalysisScores
  recruiter: {
    verdict: string
    impression: string
    main_reason: string
    biggest_weakness: string
    fastest_fix: string
  }
  keywords: {
    required_found: string[]
    required_missing: string[]
    preferred_found: string[]
    preferred_missing: string[]
    all: { keyword: string; importance: string; found: boolean }[]
  }
  priority_edits: {
    must_fix: { section: string; description: string }[]
    should_fix: { section: string; description: string }[]
    nice_to_have: { section: string; description: string }[]
  }
  formatting_warnings: string[]
  vague_terms: string[]
  weak_bullets_count: number
}

export interface UserProfile {
  id: string
  email: string
  full_name?: string
  graduation_year?: number
  school?: string
  major?: string
  preferred_locations: string[]
  alert_email?: string
  alert_frequency: string
  minimum_match_score: number
  notifications_enabled: boolean
  created_at?: string
}