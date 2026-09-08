# WorkdayCXS Companies

These companies use Workday's hidden CXS JSON API which allows
structured job fetching without bot detection.

## Active Companies (6)
| Company | CXS Board | Scan Frequency |
|---|---|---|
| Adobe | external_experienced | Every 48hrs |
| Salesforce | External_Career_Site | Every 48hrs |
| Cisco | Cisco_Careers | Every 48hrs |
| Crowdstrike | crowdstrikecareers | Every 48hrs |
| Intel | External | Every 48hrs |
| NVIDIA | NVIDIAExternalCareerSite | Every 48hrs |

## URL Format
`https://{tenant}.wd{n}.myworkdayjobs.com/wday/cxs/{tenant}/{board}/jobs`

## Notes
- Max 20 jobs per request (Workday limit)
- Uses POST with JSON body
- Free, no authentication required
