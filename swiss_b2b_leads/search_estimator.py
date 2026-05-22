from __future__ import annotations

from ui_locations import expand_locations, normalize_location_selections, summarize_locations


HIGH_COST_WARNING_THRESHOLD = 150
MAX_ESTIMATED_SOURCE_QUERIES = 300


def estimate_search(params: dict) -> dict:
    locations = normalize_location_selections(params.get("locations"), params.get("cities"))
    expanded = expand_locations(locations)
    categories = params.get("categories") or []
    max_rounds = int(params.get("max_rounds") or 1)

    enabled_source_count = sum([
        1 if params.get("enable_search_ch", True) else 0,
        1 if params.get("enable_google_places", True) else 0,
        1 if params.get("enable_google_search", True) else 0,
    ])
    combos = max(1, len(expanded)) * max(1, len(categories))
    source_queries = combos * max(1, enabled_source_count) * max(1, max_rounds)
    api_calls = source_queries
    if params.get("enable_firecrawl", False):
        api_calls += min(int(params.get("target_count") or 25) * max_rounds, 500)

    if source_queries > MAX_ESTIMATED_SOURCE_QUERIES:
        level = "blocked"
    elif source_queries > HIGH_COST_WARNING_THRESHOLD:
        level = "high"
    elif source_queries > 50:
        level = "medium"
    else:
        level = "low"

    return {
        "locations": locations,
        "expanded_locations": expanded,
        "location_summary": summarize_locations(locations),
        "expanded_locations_count": len(expanded),
        "categories_count": len(categories),
        "enabled_source_count": enabled_source_count,
        "max_rounds": max_rounds,
        "estimated_queries": source_queries,
        "estimated_api_calls": api_calls,
        "warning_level": level,
        "requires_confirmation": level in {"high", "blocked"},
        "blocked": level == "blocked",
        "limits": {
            "high_threshold": HIGH_COST_WARNING_THRESHOLD,
            "blocked_threshold": MAX_ESTIMATED_SOURCE_QUERIES,
        },
    }
