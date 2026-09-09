# JSearch Strategy — Broad Search Approach

## Old Approach (Deprecated)
- 1 API call per company = 55 calls per scan
- Searched "software engineer new grad {company}"
- Often returned 0 results or garbage data
- Wasted API quota

## New Approach (Broad Search)
- 5 fixed queries per scan regardless of company count
- Results filtered to match our monitored companies
- 5 calls per scan = ~150 calls/month on daily scanning
- Free tier = 200 calls/month ✅

## 5 Search Queries
1. "software engineer new grad 2026 2027 United States"
2. "entry level software engineer early career United States"
3. "new graduate software engineer campus hire United States"
4. "junior software developer associate engineer United States"
5. "software engineer intern return offer full time 2027 United States"

## Sources
JSearch aggregates from:
- LinkedIn Jobs
- Indeed
- Glassdoor
- ZipRecruiter
- Google for Jobs
- Company career pages

## API Budget
- 5 calls × 30 days = 150 calls/month
- Free tier: 200 calls/month
- Buffer: 50 calls for testing/debugging
