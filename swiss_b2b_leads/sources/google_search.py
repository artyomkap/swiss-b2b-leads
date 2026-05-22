import time
import requests
from typing import List, Callable, Optional
from models import Lead
from config import Config


def collect(
    cities: List[str],
    categories: List[str],
    max_results: int = 50,
    log: Optional[Callable] = None,
) -> List[Lead]:
    def _log(msg: str) -> None:
        if log:
            log(msg)

    if Config.SERP_API_KEY:
        return _serpapi(cities, categories, max_results, _log)
    if Config.TAVILY_API_KEY:
        return _tavily(cities, categories, max_results, _log)
    _log("[google_search] No API key. Skipping.")
    return []


def _queries(cities: List[str], categories: List[str]) -> List[tuple]:
    out = []
    for city in cities:
        for cat in categories:
            out.append((f"site:.ch {cat} {city} kontakt impressum", city, cat))
            out.append((f"{cat} {city} Switzerland email contact", city, cat))
    return out


def _serpapi(cities: List[str], categories: List[str], max_results: int, log: Callable) -> List[Lead]:
    all_leads: List[Lead] = []
    queries = _queries(cities, categories)
    for i, (query, city, cat) in enumerate(queries):
        if len(all_leads) >= max_results:
            break
        log(f"[google_search/serpapi] {i+1}/{len(queries)}: {query[:60]}...")
        try:
            resp = requests.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": Config.SERP_API_KEY, "num": 10, "gl": "ch", "hl": "en"},
                timeout=15,
            )
            data = resp.json()
            if data.get("error"):
                log(f"[google_search/serpapi] Error: {data['error']}")
                break
            results = data.get("organic_results", [])
            for r in results:
                all_leads.append(Lead(
                    company_name=r.get("title", ""),
                    website=r.get("link", ""),
                    source="google_search",
                    source_url=r.get("link", ""),
                    city=city,
                    industry=cat,
                    notes=r.get("snippet", "")[:200],
                ))
            log(f"[google_search/serpapi] +{len(results)} ({len(all_leads)} total)")
            time.sleep(1)
        except Exception as e:
            log(f"[google_search/serpapi] Error: {e}")
    log(f"[google_search] SerpAPI done: {len(all_leads)} leads")
    return all_leads[:max_results]


def _tavily(cities: List[str], categories: List[str], max_results: int, log: Callable) -> List[Lead]:
    all_leads: List[Lead] = []
    queries = _queries(cities, categories)
    for i, (query, city, cat) in enumerate(queries):
        if len(all_leads) >= max_results:
            break
        log(f"[google_search/tavily] {i+1}/{len(queries)}: {query[:60]}...")
        try:
            resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": Config.TAVILY_API_KEY, "query": query,
                      "search_depth": "basic", "max_results": 5},
                timeout=15,
            )
            results = resp.json().get("results", [])
            for r in results:
                all_leads.append(Lead(
                    company_name=r.get("title", ""),
                    website=r.get("url", ""),
                    source="google_search_tavily",
                    source_url=r.get("url", ""),
                    city=city,
                    industry=cat,
                    notes=r.get("content", "")[:200],
                ))
            log(f"[google_search/tavily] +{len(results)} ({len(all_leads)} total)")
            time.sleep(0.5)
        except Exception as e:
            log(f"[google_search/tavily] Error: {e}")
    log(f"[google_search] Tavily done: {len(all_leads)} leads")
    return all_leads[:max_results]
