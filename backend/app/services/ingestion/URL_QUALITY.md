# URL Quality Standards

## Apply URL Priority (highest to lowest)

1. **Direct ATS links** — always preferred
   - greenhouse.io, lever.co, ashbyhq.com
   - myworkdayjobs.com, workday.com
   - icims.com, smartrecruiters.com, jobvite.com

2. **Job aggregators** — acceptable, redirect to real job
   - linkedin.com/jobs, indeed.com
   - glassdoor.com, ziprecruiter.com
   - monster.com, careerbuilder.com

3. **Company careers page** — fallback when no direct link
   - Used when apply URL is missing, bad, or homepage-only

4. **Empty** — never stored, always replaced with careers page

## Bad URLs (rejected automatically)
- arch.co, arch.com — unrelated site
- statefarm.com — wrong company
- HTML fragments ("><strong>Company</strong></a>)
- Company homepage with no path depth (url.count('/') <= 3)
- Google/Bing search URLs

## Implementation
- `_validate_apply_url()` in runner.py validates before storing
- GitHub adapter filters bad domains before normalizing
- Existing bad URLs fixed via DB migration on 2026-09-10
