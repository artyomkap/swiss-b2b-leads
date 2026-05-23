import re
import time
import math
import requests
from bs4 import BeautifulSoup
from typing import List, Callable, Optional
from models import Lead

BASE_URL = "https://tel.search.ch/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,de;q=0.8",
}


def _parse_results(html: str, source_url: str, city: str, category: str) -> List[Lead]:
    soup = BeautifulSoup(html, "lxml")
    leads = []

    for item in soup.select("article.tel-resultentry"):
        lead = Lead(source="search.ch", source_url=source_url, city=city, industry=category)

        name_el = item.select_one("h1 a") or item.select_one("h2 a")
        if name_el:
            lead.company_name = name_el.get_text(strip=True)

        tel_link = item.select_one('a[href^="tel:"]')
        if tel_link:
            lead.phone = tel_link.get("href", "")[4:].strip()
        else:
            phone_el = item.select_one(".value.tel-callable, .tel-number")
            if phone_el:
                lead.phone = phone_el.get_text(strip=True).rstrip("*").strip()

        postal_el = item.select_one(".postal-code")
        if postal_el:
            lead.postal_code = postal_el.get_text(strip=True)

        locality_el = item.select_one(".locality")
        if locality_el:
            lead.city = locality_el.get_text(strip=True)

        region_el = item.select_one(".region")
        if region_el:
            lead.canton = region_el.get_text(strip=True)

        addr_el = item.select_one(".tel-address")
        if addr_el:
            full_addr = addr_el.get_text(separator=" ", strip=True)
            if lead.postal_code and lead.postal_code in full_addr:
                street_part = full_addr.split(lead.postal_code)[0].strip().rstrip(",").strip()
                if street_part:
                    lead.street = street_part

        cat_el = item.select_one(".tel-categories")
        if cat_el:
            lead.industry = cat_el.get_text(strip=True)[:100]

        for a in item.select('a[href^="http"]'):
            href = a.get("href", "")
            if "search.ch" not in href:
                lead.website = href
                break

        if lead.company_name:
            leads.append(lead)

    return leads


PAGE_SIZE = 10


def collect(
    cities: List[str],
    categories: List[str],
    max_results: int = 50,
    log: Optional[Callable] = None,
) -> List[Lead]:
    def _log(msg: str) -> None:
        if log:
            log(msg)

    all_leads: List[Lead] = []
    session = requests.Session()
    session.headers.update(HEADERS)

    total_combos = len(cities) * len(categories)
    per_combo_limit = max(PAGE_SIZE, math.ceil(max_results / max(1, total_combos)))
    combo_num = 0

    for city in cities:
        for category in categories:
            if len(all_leads) >= max_results:
                break
            combo_num += 1
            collected = 0
            pos = 0
            _log(f"[search.ch] {combo_num}/{total_combos}: '{category}' in {city}")
            combo_limit = min(per_combo_limit, max_results - len(all_leads))
            while collected < combo_limit and len(all_leads) < max_results:
                try:
                    resp = session.get(
                        BASE_URL,
                        params={"q": category, "where": city, "lang": "en", "pos": pos},
                        timeout=15,
                    )
                    if resp.status_code != 200:
                        _log(f"[search.ch] HTTP {resp.status_code}: {resp.url}")
                        break
                    page_leads = _parse_results(resp.text, resp.url, city, category)
                    if not page_leads:
                        _log(f"[search.ch] No results at pos={pos} for '{category}' in {city}")
                        break
                    limit = min(combo_limit - collected, max_results - len(all_leads))
                    all_leads.extend(page_leads[:limit])
                    collected += len(page_leads[:limit])
                    _log(
                        f"[search.ch] {city} / {category}: +{len(page_leads[:limit])} "
                        f"({collected}/{combo_limit} combo, {len(all_leads)}/{max_results} total)"
                    )
                    if collected >= combo_limit or len(all_leads) >= max_results:
                        break
                    pos += PAGE_SIZE
                    time.sleep(1.5)
                except requests.RequestException as e:
                    _log(f"[search.ch] Error: {e}")
                    break
        if len(all_leads) >= max_results:
            break

    _log(f"[search.ch] Done: {len(all_leads)} leads collected")
    return all_leads
