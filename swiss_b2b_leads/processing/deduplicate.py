import re
from typing import List
from models import Lead
from processing.normalize import extract_domain


def _phone_digits(phone: str) -> str:
    """Strip to digits only, normalize Swiss +41 prefix for comparison."""
    if not phone:
        return ""
    d = re.sub(r"[^\d]", "", phone)
    # "+41441234567" → digits "41441234567" (11 digits starting "41") → "0441234567"
    if d.startswith("41") and len(d) == 11:
        return "0" + d[2:]
    return d


def _merge(primary: Lead, duplicate: Lead) -> Lead:
    for field in [
        "phone", "email", "website", "contact_page_url",
        "street", "postal_code", "canton",
        "linkedin_company_url", "contact_person", "contact_role", "industry",
    ]:
        if not getattr(primary, field) and getattr(duplicate, field):
            setattr(primary, field, getattr(duplicate, field))
    return primary


def deduplicate(leads: List[Lead]) -> List[Lead]:
    seen_domains: dict = {}
    seen_emails: dict = {}
    seen_phones: dict = {}
    seen_name_city: dict = {}
    result: List[Lead] = []

    for lead in leads:
        domain = extract_domain(lead.website)
        email = lead.email.lower().strip() if lead.email else ""
        phone = _phone_digits(lead.phone)
        name_city = f"{lead.company_name.lower().strip()}|{lead.city.lower().strip()}"

        dup_idx = None
        if domain and domain in seen_domains:
            dup_idx = seen_domains[domain]
        elif email and email in seen_emails:
            dup_idx = seen_emails[email]
        elif phone and len(phone) >= 7 and phone in seen_phones:
            dup_idx = seen_phones[phone]
        elif name_city and name_city != "|" and name_city in seen_name_city:
            dup_idx = seen_name_city[name_city]

        if dup_idx is not None:
            _merge(result[dup_idx], lead)
        else:
            idx = len(result)
            result.append(lead)
            if domain:
                seen_domains[domain] = idx
            if email:
                seen_emails[email] = idx
            if phone and len(phone) >= 7:
                seen_phones[phone] = idx
            if name_city and name_city != "|":
                seen_name_city[name_city] = idx

    return result
