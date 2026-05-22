import pytest
from fastapi import HTTPException

from api_limits import classify_api_error
from app_server import SearchParams, _enforce_cost_guardrails, _normalize_params
from search_estimator import estimate_search


def test_estimate_low_for_small_city_search():
    estimate = estimate_search({
        "locations": [{"type": "city", "value": "Zurich", "label": "Zurich", "coverage_mode": "top_cities"}],
        "categories": ["banks"],
        "max_rounds": 1,
        "enable_search_ch": True,
        "enable_google_places": False,
        "enable_google_search": False,
    })
    assert estimate["warning_level"] == "low"
    assert estimate["estimated_queries"] == 1


def test_estimate_blocks_large_search():
    estimate = estimate_search({
        "locations": [{"type": "region", "value": "de_ch", "label": "German-speaking Switzerland", "coverage_mode": "all_available_cities"}],
        "categories": ["banks", "hotels", "garages", "schools", "fitness"],
        "max_rounds": 3,
        "enable_search_ch": True,
        "enable_google_places": True,
        "enable_google_search": True,
    })
    assert estimate["warning_level"] == "blocked"
    assert estimate["estimated_queries"] > 300


def test_cost_guardrail_rejects_unconfirmed_high_search():
    params, estimate = _normalize_params(SearchParams(
        locations=[{"type": "region", "value": "de_ch", "label": "German-speaking Switzerland", "coverage_mode": "all_available_cities"}],
        categories=["banks", "hotels", "garages", "schools", "fitness"],
        max_rounds=3,
        enable_search_ch=True,
        enable_google_places=True,
        enable_google_search=True,
    ))
    with pytest.raises(HTTPException):
        _enforce_cost_guardrails(params, estimate)


def test_api_error_classifier():
    assert classify_api_error("quota exceeded") == "quota_exceeded"
    assert classify_api_error("Too many requests", 429) == "rate_limited"
    assert classify_api_error("API key not valid", 401) == "invalid_key"
