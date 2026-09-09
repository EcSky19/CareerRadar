# Changelog

## v0.2.0 — 2026-09-08
### Added
- JSearch adapter via OpenWebNinja API for 57 companies
- WorkdayCXS adapter for Adobe, Salesforce, Cisco, Intel, NVIDIA, Crowdstrike
- Smart scan scheduling — JSearch weekly tiers, Greenhouse/Lever/Ashby daily
- Comprehensive US location matching (200+ cities, states, metros)
- International location penalty (-15 points for non-US jobs)
- scan_tier column for JSearch Tier 1/2 management
- Company edit form with JSearch scan tier dropdown
- Dashboard last scan date/time display
- Problem Companies tab in Logs page
- Location picker with all US states, metros and EU countries

### Fixed
- Ashby adapter switched from POST to GET
- Lever descriptionBody string parsing
- HTML adapter int title field conversion
- ATSProvider schema missing workday_cxs and jsearch
- Matching engine user_id profile query fix

## v0.1.0 — 2026-09-04
### Added
- Initial platform launch
- Greenhouse, Lever, Ashby adapters
- Matching engine with 100-point scoring
- Frontend with Dashboard, Companies, Jobs, Profiles, Logs pages

## v0.3.0 — 2026-09-09
### Added
- GitHub jobs adapter — scrapes 7 community repos daily (free, unlimited)
- JSearch broad search — 5 queries cover all companies (5 calls/scan)
- Direct ATS filter — only Greenhouse/Lever/Ashby/WorkdayCXS scan per-company
- Fresh session per company — prevents transaction corruption
- Timeout handling per company — scan never hangs

### Changed
- JSearch no longer searches per-company (was 55 calls, now 5)
- All custom_html companies now covered by GitHub + JSearch broad
- Scan architecture: Direct ATS + GitHub + JSearch broad

### Sources
- SimplifyJobs/New-Grad-Positions
- SimplifyJobs/Summer2027-Internships
- jobright-ai/2026-Software-Engineer-New-Grad
- zapplyjobs/New-Grad-Software-Engineering-Jobs-2027
- vanshb03/New-Grad-2027
- vanshb03/Summer2027-Internships
- speedyapply/2027-SWE-College-Jobs
