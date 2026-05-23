from app_server import _export_leads_for_scope
from models import Lead


def test_export_scope_target_uses_target_list():
    results = {
        "final": [Lead(company_name="Target One")],
        "all_qualified": [Lead(company_name="Target One"), Lead(company_name="Extra One")],
    }

    leads, filename = _export_leads_for_scope(results, "target")

    assert filename == "leads_target.xlsx"
    assert [lead["company_name"] for lead in leads] == ["Target One"]


def test_export_scope_all_qualified_uses_full_qualified_list():
    results = {
        "final": [Lead(company_name="Target One")],
        "all_qualified": [Lead(company_name="Target One"), Lead(company_name="Extra One")],
    }

    leads, filename = _export_leads_for_scope(results, "all_qualified")

    assert filename == "leads_all_qualified.xlsx"
    assert [lead["company_name"] for lead in leads] == ["Target One", "Extra One"]
