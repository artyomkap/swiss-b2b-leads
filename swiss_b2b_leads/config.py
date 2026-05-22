import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
    SERP_API_KEY = os.getenv("SERP_API_KEY", "")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY", "")

    COUNTRY = "Switzerland"
    CITIES = ["Zurich", "Geneva", "Basel"]
    CATEGORIES = ["garages", "schools", "corporate gifts"]
    MAX_RESULTS_PER_QUERY = int(os.getenv("MAX_RESULTS_PER_QUERY", "50"))
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")

    ENABLE_SEARCH_CH = True
    ENABLE_GOOGLE_SEARCH = bool(os.getenv("SERP_API_KEY") or os.getenv("TAVILY_API_KEY"))
    ENABLE_GOOGLE_PLACES = bool(os.getenv("GOOGLE_API_KEY"))
    ENABLE_WEBSITE_PARSER = True
    ENABLE_FIRECRAWL = bool(os.getenv("FIRECRAWL_API_KEY"))
