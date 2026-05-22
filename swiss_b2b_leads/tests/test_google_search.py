import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.google_search import collect
from unittest.mock import patch


def test_no_api_key():
    """Test that collect returns empty list when no API keys are configured."""
    with patch("sources.google_search.Config") as mock_cfg:
        mock_cfg.SERP_API_KEY = ""
        mock_cfg.TAVILY_API_KEY = ""
        result = collect(['Zurich'], ['garage'], max_results=5)
    assert isinstance(result, list)
    assert len(result) == 0


def test_import():
    """Test that the module can be imported."""
    from sources.google_search import collect, _queries, _serpapi, _tavily
    assert callable(collect)
    assert callable(_queries)
    assert callable(_serpapi)
    assert callable(_tavily)


if __name__ == "__main__":
    test_import()
    print("Import test: OK")
    test_no_api_key()
    print("No API key test: OK")
