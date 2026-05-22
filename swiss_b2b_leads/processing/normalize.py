import re
from urllib.parse import urlparse, urlunparse
from models import Lead


def normalize_company_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip())


def normalize_phone(phone: str) -> str:
    if not phone:
        return ""
    digits = re.sub(r"[^\d+]", "", phone.strip())
    if digits.startswith("0041"):
        digits = "+41" + digits[4:]
    elif digits.startswith("00"):
        pass  # other international prefix, keep as-is
    elif digits.startswith("0") and len(digits) >= 9:
        digits = "+41" + digits[1:]
    return digits


def normalize_website(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
    if not url.lower().startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    clean = urlunparse(("https", parsed.netloc.lower(), parsed.path, "", "", ""))
    return clean.rstrip("/")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def extract_domain(url: str) -> str:
    if not url:
        return ""
    normalized = normalize_website(url)
    parsed = urlparse(normalized)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def normalize_lead(lead: Lead) -> Lead:
    lead.company_name = normalize_company_name(lead.company_name)
    if lead.phone:
        lead.phone = normalize_phone(lead.phone)
    if lead.website:
        lead.website = normalize_website(lead.website)
    if lead.email:
        lead.email = normalize_email(lead.email)
    lead.country = "Switzerland"
    return lead
