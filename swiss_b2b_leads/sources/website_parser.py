import re
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Optional, Tuple
from urllib.parse import urljoin
from models import Lead

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(
    r"(?:\+41|0041|0[1-9])[\s\-\.]?\d{1,2}[\s\-\.]?\d{3}[\s\-\.]?\d{2}[\s\-\.]?\d{2}"
)
EMAIL_BLACKLIST = {"noreply", "no-reply", "donotreply", "example.com", "sentry", "@2x"}
CONTACT_PATHS = [
    "/contact", "/kontakt", "/impressum", "/about", "/about-us",
    "/company", "/unternehmen", "/team", "/contact-us",
    "/uber-uns", "/ueber-uns", "/kontaktieren",
]
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _get(session: requests.Session, url: str) -> Optional[str]:
    try:
        resp = session.get(url, timeout=10, allow_redirects=True)
        ct = resp.headers.get("Content-Type", "")
        if resp.status_code == 200 and "text/html" in ct:
            return resp.text
    except Exception:
        pass
    return None


def _extract_emails(text: str) -> List[str]:
    found = EMAIL_RE.findall(text)
    return [
        e.lower() for e in found
        if not any(bad in e.lower() for bad in EMAIL_BLACKLIST)
    ]


def _extract_phones(text: str) -> List[str]:
    return PHONE_RE.findall(text)


def _find_contact_page(session: requests.Session, base_url: str) -> Tuple[Optional[str], Optional[str]]:
    for path in CONTACT_PATHS:
        url = urljoin(base_url, path)
        html = _get(session, url)
        if html:
            return url, html
    # Fall back: look for contact link in homepage
    html = _get(session, base_url)
    if html:
        soup = BeautifulSoup(html, "lxml")
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            if any(kw in text for kw in ["contact", "kontakt", "impressum"]):
                full = urljoin(base_url, a["href"])
                page = _get(session, full)
                if page:
                    return full, page
    return None, None


def enrich_lead(lead: Lead, session: Optional[requests.Session] = None) -> Lead:
    if not lead.website:
        return lead
    if session is None:
        session = requests.Session()
        session.headers.update(HEADERS)

    homepage = _get(session, lead.website) or ""
    contact_url, contact_html = _find_contact_page(session, lead.website)
    all_text = homepage + (contact_html or "")

    if contact_url and not lead.contact_page_url:
        lead.contact_page_url = contact_url

    if not lead.email:
        emails = _extract_emails(all_text)
        if emails:
            lead.email = emails[0]

    if not lead.phone:
        phones = _extract_phones(all_text)
        if phones:
            lead.phone = phones[0].strip()

    return lead


def enrich_leads(leads: List[Lead], delay: float = 1.0) -> List[Lead]:
    session = requests.Session()
    session.headers.update(HEADERS)
    result = []
    total = len([l for l in leads if l.website])
    enriched_count = 0
    for lead in leads:
        if lead.website:
            enriched_count += 1
            print(f"[website_parser] {enriched_count}/{total}: {lead.website}")
            lead = enrich_lead(lead, session)
            time.sleep(delay)
        result.append(lead)
    return result
