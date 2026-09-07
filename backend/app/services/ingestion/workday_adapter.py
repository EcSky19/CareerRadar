"""
Workday CXS API Adapter
Uses Workday's internal CXS (Candidate Experience Service) API
which is publicly accessible without authentication.
URL pattern: https://{company}.wd{N}.myworkdayjobs.com/wday/cxs/{company}/{board}/jobs
"""
import logging
import httpx
import re
from datetime import datetime, timezone
from typing import Optional
from .base import BaseAdapter, NormalizedJob, AdapterError, AdapterEmpty

logger = logging.getLogger(__name__)

WORKDAY_HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}

# Known Workday CXS endpoints for specific companies
WORKDAY_CXS_MAP = {
    "atlassian":     ("atlassian.wd5.myworkdayjobs.com", "Atlassian", "FY22_Recruiting"),
    "crowdstrike":   ("crowdstrike.wd5.myworkdayjobs.com", "crowdstrike", "crowdstrikecareers"),
    "doordash":      ("doordash.wd5.myworkdayjobs.com", "DoorDash", "DoorDashCareers"),
    "snap":          ("snap.wd5.myworkdayjobs.com", "Snap", "snap"),
    "visa":          ("visa.wd5.myworkdayjobs.com", "Visa", "Visa-Careers"),
    "draftkings":    ("draftkings.wd5.myworkdayjobs.com", "DraftKings", "DraftKings"),
    "ebay":          ("ebay.wd5.myworkdayjobs.com", "eBay", "eBayCareers"),
    "salesforce":    ("salesforce.wd12.myworkdayjobs.com", "Salesforce", "External_Career_Site"),
    "servicenow":    ("servicenow.wd5.myworkdayjobs.com", "ServiceNow", "External"),
    "adobe":         ("adobe.wd5.myworkdayjobs.com", "Adobe", "external_experienced"),
    "workiva":       ("workiva.wd5.myworkdayjobs.com", "Workiva", "External"),
    "sentry":        ("sentry.wd5.myworkdayjobs.com", "Sentry", "Sentry"),
    "nasdaq":        ("nasdaq.wd1.myworkdayjobs.com", "Nasdaq", "Nasdaq_Careers"),
    "cboe":          ("cboe.wd1.myworkdayjobs.com", "Cboe", "External"),
    "lam":           ("lamresearch.wd1.myworkdayjobs.com", "LamResearch", "External"),
    "marvell":       ("marvell.wd1.myworkdayjobs.com", "Marvell", "MarvellCareers"),
    "micron":        ("micron.wd1.myworkdayjobs.com", "Micron", "External"),
    "qualcomm":      ("qualcomm.wd5.myworkdayjobs.com", "Qualcomm", "External"),
    "redhat":        ("redhat.wd5.myworkdayjobs.com", "RedHat", "External"),
}

class WorkdayCXSAdapter(BaseAdapter):
    ATS_PROVIDER = "workday"

    async def fetch_jobs(self, company) -> list[NormalizedJob]:
        name_lower = company.name.lower().replace(" ", "").replace("-", "")
        
        # Find the CXS config




python3 << 'PYEOF'
with open('/opt/CareerRadar/backend/app/services/ingestion/lever.py') as f:
    content = f.read()

content = content.replace(
    "        cats     = raw.get(\"categories\", {})",
    "        cats     = raw.get(\"categories\") or {}\n        if not isinstance(cats, dict): cats = {}"
)

with open('/opt/CareerRadar/backend/app/services/ingestion/lever.py', 'w') as f:
    f.write(content)
print("Fixed:", "isinstance(cats, dict)" in content)
