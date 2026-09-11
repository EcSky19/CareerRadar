# GitHub Jobs Parsing Notes

## URL Extraction Priority
1. Markdown links [text](url) — preferred
2. Bare https:// URLs — fallback

## Known Issues Fixed
- HTML fragments in URLs: `https://company.com"><strong>Name</strong>` — cleaned
- Homepage-only URLs: `https://company.com` — replaced with careers page
- Wrong company links: arch.co, statefarm.com — rejected

## Company Name Matching
- Exact match first
- Fuzzy match: db_company in raw_company or raw_company in db_company
- Case insensitive

## Closed Role Detection
- 🔒 emoji in row = skip
- "closed" keyword = skip

## Location Filtering
- International signals filtered: canada, uk, london, toronto, etc.
- US-only jobs kept
