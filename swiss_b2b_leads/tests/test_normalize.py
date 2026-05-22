from processing.normalize import (
    normalize_company_name,
    normalize_phone,
    normalize_website,
    normalize_email,
    extract_domain,
    normalize_lead,
)
from models import Lead


def test_normalize_company_name_strips_spaces():
    assert normalize_company_name("  Müller AG  ") == "Müller AG"


def test_normalize_company_name_collapses_internal_spaces():
    assert normalize_company_name("Zürich  Garage   GmbH") == "Zürich Garage GmbH"


def test_normalize_phone_swiss_local_to_e164():
    assert normalize_phone("044 123 45 67") == "+41441234567"


def test_normalize_phone_0041_prefix():
    assert normalize_phone("0041441234567") == "+41441234567"


def test_normalize_phone_already_plus41():
    assert normalize_phone("+41441234567") == "+41441234567"


def test_normalize_phone_with_dashes():
    assert normalize_phone("044-123-45-67") == "+41441234567"


def test_normalize_website_adds_https():
    assert normalize_website("example.ch") == "https://example.ch"


def test_normalize_website_removes_utm():
    result = normalize_website("https://example.ch?utm_source=google&utm_medium=cpc")
    assert result == "https://example.ch"


def test_normalize_website_lowercases_domain():
    assert normalize_website("HTTPS://EXAMPLE.CH/Page") == "https://example.ch/Page"


def test_normalize_email_lowercase():
    assert normalize_email("  Test@Example.COM  ") == "test@example.com"


def test_extract_domain_removes_www():
    assert extract_domain("https://www.example.ch/contact") == "example.ch"


def test_extract_domain_no_www():
    assert extract_domain("https://example.ch") == "example.ch"


def test_normalize_lead_applies_all():
    lead = Lead(
        company_name="  Test AG  ",
        phone="044 111 22 33",
        website="http://test.ch?utm_source=foo",
        email="TEST@TEST.CH",
    )
    result = normalize_lead(lead)
    assert result.company_name == "Test AG"
    assert result.phone == "+41441112233"
    assert "utm_source" not in result.website
    assert result.email == "test@test.ch"
    assert result.country == "Switzerland"
