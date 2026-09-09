# Job Deduplication Strategy

Career Radar ingests jobs from multiple sources daily.
The same job may appear in Greenhouse AND a GitHub repo AND JSearch.
Deduplication ensures each job is stored only once.

## How It Works

Each job has an external_job_id:
- Greenhouse: job ID from their API
- Lever: posting ID from their API
- Ashby: job UUID from their API
- WorkdayCXS: external path from Workday
- GitHub repos: MD5 hash of apply URL
- JSearch: job_id from OpenWebNinja

The DB has a unique constraint on (company_id, external_job_id).
ON CONFLICT DO UPDATE — updates last_seen_at if job already exists.

## Result
- No duplicate jobs in the DB
- Job descriptions update if source provides richer data
- last_seen_at tracks when job was last confirmed open
- Jobs not seen for 3 days marked as possibly_closed
