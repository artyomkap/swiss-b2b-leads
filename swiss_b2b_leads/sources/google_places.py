import re
import time
import requests
from typing import List, Callable, Optional
from models import Lead
from config import Config
from api_limits import ApiLimitEvent, classify_api_error, missing_key_event

TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
FIELD_MASK = (
    "places.displayName,places.formattedAddress,"
    "places.nationalPhoneNumber,places.websiteUri,"
    "places.id,nextPageToken"
)


def collect(
    cities: List[str],
    categories: List[str],
    max_results: int = 50,
    log: Optional[Callable] = None,
    event_callback: Optional[Callable[[dict], None]] = None,
) -> List[Lead]:
    def _log(msg: str) -> None:
        if log:
            log(msg)

    if not Config.GOOGLE_API_KEY:
        _log("[google_places] No API key. Skipping.")
        if event_callback:
            event_callback(missing_key_event("google_places").to_dict())
        return []
    all_leads: List[Lead] = []

    total_combos = len(cities) * len(categories)
    combo_num = 0

    for city in cities:
        for cat in categories:
            combo_num += 1
            if len(all_leads) >= max_results:
                break
            _log(f"[google_places] {combo_num}/{total_combos}: '{cat}' in {city}")
            page_token = None
            page_num = 0
            while len(all_leads) < max_results:
                payload = {
                    "textQuery": f"{cat} in {city}, Switzerland",
                    "regionCode": "CH",
                    "maxResultCount": min(20, max_results - len(all_leads)),
                }
                if page_token:
                    payload["pageToken"] = page_token
                try:
                    resp = requests.post(
                        TEXT_SEARCH_URL,
                        headers={
                            "X-Goog-Api-Key": Config.GOOGLE_API_KEY,
                            "X-Goog-FieldMask": FIELD_MASK,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=15,
                    )
                    data = resp.json()
                    if "error" in data:
                        message = data["error"].get("message", data["error"])
                        event_type = classify_api_error(str(message), resp.status_code)
                        _log(f"[google_places] Error: {message}")
                        if event_callback:
                            event_callback(ApiLimitEvent(
                                provider="google_places",
                                event_type=event_type,
                                message=str(message),
                                status_code=resp.status_code,
                                error_code=data["error"].get("status", ""),
                                severity="critical" if event_type in {"quota_exceeded", "invalid_key"} else "warning",
                                action_taken="source_disabled" if event_type in {"quota_exceeded", "rate_limited", "invalid_key"} else "recorded",
                            ).to_dict())
                        break
                    places = data.get("places", [])
                    if not places:
                        break
                    for place in places:
                        all_leads.append(_to_lead(place, city, cat))
                    page_num += 1
                    _log(f"[google_places] {city} / {cat}: page {page_num}, +{len(places)} ({len(all_leads)} total)")
                    page_token = data.get("nextPageToken")
                    if not page_token:
                        break
                    time.sleep(2)
                except Exception as e:
                    event_type = classify_api_error(str(e))
                    _log(f"[google_places] Error: {e}")
                    if event_callback and event_type != "unknown_error":
                        event_callback(ApiLimitEvent(
                            provider="google_places",
                            event_type=event_type,
                            message=str(e),
                            action_taken="source_disabled",
                        ).to_dict())
                    break

    _log(f"[google_places] Done: {len(all_leads)} leads collected")
    return all_leads[:max_results]


def _to_lead(place: dict, city: str, category: str) -> Lead:
    lead = Lead(source="google_places", city=city, industry=category, country="Switzerland")
    lead.company_name = place.get("displayName", {}).get("text", "")
    lead.phone = place.get("nationalPhoneNumber", "")
    lead.website = place.get("websiteUri", "")

    addr = place.get("formattedAddress", "")
    if addr:
        lead.notes = addr
        parts = addr.split(",")
        if parts:
            lead.street = parts[0].strip()
        m = re.search(r"(\d{4})\s+([A-Za-züäöÜÄÖ\s\-]+)", addr)
        if m:
            lead.postal_code = m.group(1)
            lead.city = m.group(2).strip()

    place_id = place.get("id", "")
    if place_id:
        lead.source_url = f"https://www.google.com/maps/place/?q=place_id:{place_id}"

    return lead
