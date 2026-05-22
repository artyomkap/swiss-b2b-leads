from processing.deduplicate import deduplicate
from models import Lead


def test_dedup_by_domain():
    leads = [
        Lead(company_name="Müller AG", website="https://mueller.ch"),
        Lead(company_name="Mueller AG", website="http://www.mueller.ch"),
    ]
    result = deduplicate(leads)
    assert len(result) == 1
    assert result[0].company_name == "Müller AG"


def test_dedup_by_email():
    leads = [
        Lead(company_name="Alpha GmbH", email="info@alpha.ch", website=""),
        Lead(company_name="Alpha GmbH", email="info@alpha.ch", website="https://alpha.ch"),
    ]
    result = deduplicate(leads)
    assert len(result) == 1
    assert result[0].website == "https://alpha.ch"


def test_dedup_by_phone():
    leads = [
        Lead(company_name="Beta SA", phone="+41441234567", website=""),
        Lead(company_name="Beta SA", phone="044 123 45 67", website="https://beta.ch"),
    ]
    result = deduplicate(leads)
    assert len(result) == 1


def test_dedup_by_name_city():
    leads = [
        Lead(company_name="Gamma AG", city="Zurich", website=""),
        Lead(company_name="Gamma AG", city="Zurich", website="https://gamma.ch"),
    ]
    result = deduplicate(leads)
    assert len(result) == 1


def test_dedup_merges_data():
    leads = [
        Lead(company_name="Delta AG", email="info@delta.ch", website="https://delta.ch", phone=""),
        Lead(company_name="Delta AG", email="info@delta.ch", phone="+41441234567", website=""),
    ]
    result = deduplicate(leads)
    assert len(result) == 1
    assert result[0].phone == "+41441234567"


def test_dedup_keeps_distinct():
    leads = [
        Lead(company_name="Alpha", city="Zurich", email="a@a.ch", website="https://a.ch"),
        Lead(company_name="Beta", city="Geneva", email="b@b.ch", website="https://b.ch"),
    ]
    result = deduplicate(leads)
    assert len(result) == 2
