from models import Lead


def calculate_quality_score(lead: Lead) -> int:
    score = 0
    if lead.company_name:
        score += 20
    if lead.city:
        score += 15
    if lead.phone:
        score += 15
    if lead.website:
        score += 20
    if lead.email:
        score += 20
    if lead.source_url or lead.contact_page_url:
        score += 10
    return score
