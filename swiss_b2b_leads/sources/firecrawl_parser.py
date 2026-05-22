import re
import time
import requests
from typing import List
from models import Lead
from config import Config

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?:\+41|0041|0[1-9])[\s\-\.]?\d{1,2}[\s\-\.]?\d{3}[\s\-\.]?\d{2}[\s\-\.]?\d{2}"
)
SCRAPE_URL = "https://api.firecrawl.dev/v0/scrape"


def enrich_lead(lead: Lead) -> Lead:
    if not Config.FIRECRAWL_API_KEY or not lead.website:
        return lead
    headers = {"Authorization": f"Bearer {Config.FIRECRAWL_API_KEY}"}
    for url in filter(None, [lead.website, lead.contact_page_url]):
        try:
            resp = requests.post(
                SCRAPE_URL,
                headers=headers,
                json={"url": url, "formats": ["markdown"]},
                timeout=30,
            )
            data = resp.json()
            if not data.get("success"):
                continue
            content = data.get("data", {}).get("markdown", "")
            if not lead.email:
                emails = EMAIL_RE.findall(content)
                if emails:
                    lead.email = emails[0].lower()
            if not lead.phone:
                phones = PHONE_RE.findall(content)
                if phones:
                    lead.phone = phones[0].strip()
            if lead.email and lead.phone:
                break
            time.sleep(0.5)
        except Exception as e:
            print(f"[firecrawl] Error for {url}: {e}")
    return lead


def enrich_leads(leads: List[Lead]) -> List[Lead]:
    if not Config.FIRECRAWL_API_KEY:
        print("[firecrawl] No API key. Skipping.")
        return leads
    return [enrich_lead(lead) for lead in leads]
