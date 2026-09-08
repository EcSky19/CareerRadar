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
