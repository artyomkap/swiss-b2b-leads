from ui_locations import expand_locations, normalize_location_selections, search_location_options


def test_location_alias_search_finds_zurich_canton():
    results = search_location_options("ZH")
    assert results
    assert results[0]["type"] == "canton"
    assert results[0]["value"] == "ZH"


def test_canton_top_city_expansion():
    expanded = expand_locations([{
        "type": "canton",
        "value": "ZH",
        "label": "Canton Zürich",
        "coverage_mode": "top_cities",
    }])
    assert "Zurich" in expanded
    assert "Winterthur" in expanded


def test_region_expansion_includes_romandie_cities():
    expanded = expand_locations([{
        "type": "region",
        "value": "romandie",
        "label": "Romandie",
        "coverage_mode": "top_cities",
    }])
    assert "Geneva" in expanded
    assert "Lausanne" in expanded


def test_custom_location_passthrough():
    locations = normalize_location_selections([{"type": "custom", "value": "Lake Geneva area"}])
    assert locations[0]["type"] == "custom"
    assert expand_locations(locations) == ["Lake Geneva area"]


def test_legacy_city_input_becomes_location():
    locations = normalize_location_selections(None, ["Zurich"])
    assert locations[0]["type"] == "city"
    assert locations[0]["label"] == "Zurich"
