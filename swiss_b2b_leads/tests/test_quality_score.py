from processing.quality_score import calculate_quality_score
from models import Lead


def test_empty_lead_scores_zero():
    assert calculate_quality_score(Lead()) == 0


def test_full_lead_scores_100():
    lead = Lead(
        company_name="Test AG",
        city="Zurich",
        phone="+41441234567",
        website="https://test.ch",
        email="info@test.ch",
        source_url="https://tel.search.ch/...",
    )
    assert calculate_quality_score(lead) == 100


def test_name_only_scores_20():
    assert calculate_quality_score(Lead(company_name="Test AG")) == 20


def test_name_and_city_scores_35():
    assert calculate_quality_score(Lead(company_name="Test AG", city="Zurich")) == 35


def test_website_and_email_scores_40():
    assert calculate_quality_score(Lead(website="https://test.ch", email="info@test.ch")) == 40


def test_contact_page_url_gives_10():
    assert calculate_quality_score(Lead(contact_page_url="https://test.ch/contact")) == 10
