# Career Radar — Matching Engine Scoring

## Score Breakdown (100 points total)

| Component | Points | Description |
|---|---|---|
| Title Match | 25 | Job title matches desired titles |
| Role Type | 15 | new_grad, internship, entry_level match |
| Keywords | 15 | Description contains profile keywords |
| Location | 10 | Job location matches desired locations |
| Category | 10 | Company category matches profile filters |
| Domain | 10 | Technical signals in description |
| Priority | 5 | Company priority (high/medium/low) |
| Freshness | 5 | How recently the job was posted |
| Campus | 5 | Campus/new grad signals detected |

## Penalties
- International job when US desired: -15 points
- Exclusion keyword found: -20 per term (max -40)
- Vague title with no technical signal: score capped at 0

## Minimum Score
- Default: 60 points to appear in matches
- Configurable per profile
