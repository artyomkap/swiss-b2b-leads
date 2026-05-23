import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable, Set

import requests

from models import Lead
from config import Config
from processing.normalize import normalize_lead, extract_domain
from processing.deduplicate import deduplicate
from processing.quality_score import calculate_quality_score
from processing.summary import compute_source_stats
from sources.website_parser import enrich_lead as _ws_enrich_lead
from api_limits import ApiLimitEvent, ProviderLimitError, classify_api_error, missing_key_event

_WS_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

_thread_local = threading.local()


def _get_session() -> requests.Session:
    if not hasattr(_thread_local, "session"):
        s = requests.Session()
        s.headers.update(_WS_HEADERS)
        _thread_local.session = s
    return _thread_local.session


def _meets_quality(lead: Lead, require_email: bool, require_phone: bool, require_website: bool) -> bool:
    if require_email and not lead.email:
        return False
    if require_phone and not lead.phone:
        return False
    if require_website and not lead.website:
        return False
    return True


def _check_pause(
    pause_event: Optional[threading.Event],
    resume_event: Optional[threading.Event],
    status_callback: Optional[Callable],
    log: Callable,
) -> None:
    if pause_event and pause_event.is_set():
        if status_callback:
            status_callback("paused")
        log("⏸ Paused — click Resume to continue ...")
        if resume_event:
            resume_event.wait()
            resume_event.clear()
        pause_event.clear()
        if status_callback:
            status_callback("running")
        log("▶ Resumed")


def _enrich_concurrent(
    leads: List[Lead],
    visited_domains: Set[str],
    log: Callable,
    lead_writer=None,
    max_workers: int = 5,
    pause_event: Optional[threading.Event] = None,
    resume_event: Optional[threading.Event] = None,
    status_callback: Optional[Callable] = None,
) -> None:
    """Enrich leads concurrently. Skips already-visited domains. Mutates leads in place.
    Writes each enriched lead to lead_writer immediately (if provided)."""
    to_enrich = [l for l in leads if l.website and extract_domain(l.website) not in visited_domains]
    total = len(to_enrich)
    if not total:
        return

    log(f"Enriching {total} websites ({max_workers} parallel workers) ...")
    done_count = [0]
    lock = threading.Lock()

    def _enrich_one(lead: Lead) -> None:
        if pause_event and pause_event.is_set():
            return
        try:
            session = _get_session()
            _ws_enrich_lead(lead, session)
        except Exception:
            pass
        with lock:
            domain = extract_domain(lead.website)
            if domain:
                visited_domains.add(domain)
            done_count[0] += 1
            n = done_count[0]
            if n % 20 == 0 or n == total:
                log(f"Website enrichment: {n}/{total}")
        # Write to DB immediately after enrichment (non-blocking)
        if lead_writer is not None:
            lead.quality_score = calculate_quality_score(lead)
            lead_writer.write(lead)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_enrich_one, lead): lead for lead in to_enrich}
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                pass
            if pause_event and pause_event.is_set():
                _check_pause(pause_event, resume_event, status_callback, log)


def _collect_sources(
    cities: List[str],
    categories: List[str],
    max_results: int,
    enable_search_ch: bool,
    enable_google_places: bool,
    enable_google_search: bool,
    log: Callable,
    pause_event: Optional[threading.Event],
    resume_event: Optional[threading.Event],
    status_callback: Optional[Callable],
    api_event_callback: Optional[Callable[[dict], None]],
) -> Dict[str, List[Lead]]:
    raw: Dict[str, List[Lead]] = {}

    def emit_event(event: dict) -> None:
        if api_event_callback:
            api_event_callback(event)

    def _try_collect(name: str, fn: Callable) -> List[Lead]:
        try:
            results = fn()
            return results
        except ProviderLimitError as exc:
            event = exc.event.to_dict()
            emit_event(event)
            log(f"⚠️ [{name}] {event['event_type']}: {event['message']}")
            return []
        except Exception as exc:
            event_type = classify_api_error(str(exc))
            if event_type != "unknown_error":
                event = ApiLimitEvent(
                    provider=name,
                    event_type=event_type,
                    message=str(exc),
                    action_taken="source_disabled",
                ).to_dict()
                emit_event(event)
                log(f"⚠️ [{name}] {event_type}: {exc}")
                return []
            log(f"[{name}] Error: {exc}")
            return []

    if enable_search_ch:
        log(f"Collecting from search.ch (up to {max_results}) ...")
        from sources.search_ch import collect as sc
        raw["search.ch"] = _try_collect("search.ch", lambda: sc(cities, categories, max_results, log=log))
        _check_pause(pause_event, resume_event, status_callback, log)

    if enable_google_places:
        if Config.GOOGLE_API_KEY:
            log(f"Collecting from Google Places (up to {max_results}) ...")
            from sources.google_places import collect as gp
            raw["google_places"] = _try_collect(
                "google_places",
                lambda: gp(cities, categories, max_results, log=log, event_callback=emit_event),
            )
            _check_pause(pause_event, resume_event, status_callback, log)
        else:
            log("Google Places skipped — no API key")
            emit_event(missing_key_event("google_places").to_dict())

    if enable_google_search:
        if Config.SERP_API_KEY or Config.TAVILY_API_KEY:
            log(f"Collecting from Google Search (up to {max_results}) ...")
            from sources.google_search import collect as gs
            raw["google_search"] = _try_collect(
                "google_search",
                lambda: gs(cities, categories, max_results, log=log, event_callback=emit_event),
            )
            _check_pause(pause_event, resume_event, status_callback, log)
        else:
            log("Google Search skipped — no API key")
            emit_event(missing_key_event("google_search").to_dict())

    return raw


def _process_all(
    all_raw_by_source: Dict[str, List[Lead]],
    visited_domains: Set[str],
    enable_website_parser: bool,
    enable_firecrawl: bool,
    enrich_workers: int,
    log: Callable,
    lead_writer,
    pause_event: Optional[threading.Event],
    resume_event: Optional[threading.Event],
    status_callback: Optional[Callable],
    api_event_callback: Optional[Callable[[dict], None]],
) -> Dict[str, List[Lead]]:
    clean_by_source: Dict[str, List[Lead]] = {}
    firecrawl_disabled = False

    for src, raw_leads in all_raw_by_source.items():
        leads = [normalize_lead(l) for l in raw_leads]
        leads = deduplicate(leads)

        if enable_website_parser:
            _enrich_concurrent(
                leads, visited_domains, log,
                lead_writer=lead_writer,
                max_workers=enrich_workers,
                pause_event=pause_event,
                resume_event=resume_event,
                status_callback=status_callback,
            )
            _check_pause(pause_event, resume_event, status_callback, log)

        if enable_firecrawl and Config.FIRECRAWL_API_KEY and not firecrawl_disabled:
            from sources.firecrawl_parser import enrich_lead as fc_enrich
            to_fc = [l for l in leads if l.website and extract_domain(l.website) not in visited_domains]
            for i, lead in enumerate(to_fc):
                log(f"[{src}] Firecrawl {i+1}/{len(to_fc)}: {lead.website}")
                try:
                    fc_enrich(lead)
                except ProviderLimitError as exc:
                    firecrawl_disabled = True
                    event = exc.event.to_dict()
                    if api_event_callback:
                        api_event_callback(event)
                    log(f"⚠️ Firecrawl {event['event_type']}: {event['message']}")
                    break
                except Exception as exc:
                    event_type = classify_api_error(str(exc))
                    if event_type != "unknown_error":
                        firecrawl_disabled = True
                        event = ApiLimitEvent(
                            provider="firecrawl",
                            event_type=event_type,
                            message=str(exc),
                            action_taken="source_disabled",
                        ).to_dict()
                        if api_event_callback:
                            api_event_callback(event)
                        log(f"⚠️ Firecrawl {event_type}: {exc}")
                        break
                d = extract_domain(lead.website)
                if d:
                    visited_domains.add(d)
                # Write to DB immediately after Firecrawl enrichment
                if lead_writer is not None:
                    lead.quality_score = calculate_quality_score(lead)
                    lead_writer.write(lead)

        leads = [normalize_lead(l) for l in leads]
        for lead in leads:
            lead.quality_score = calculate_quality_score(lead)
        clean_by_source[src] = leads

    return clean_by_source


def run_search(
    cities: List[str],
    categories: List[str],
    target_count: int = 25,
    require_email: bool = False,
    require_phone: bool = False,
    require_website: bool = False,
    max_rounds: int = 3,
    enrich_workers: int = 5,
    enable_search_ch: bool = True,
    enable_google_places: bool = True,
    enable_google_search: bool = True,
    enable_website_parser: bool = True,
    enable_firecrawl: bool = False,
    pause_event: Optional[threading.Event] = None,
    resume_event: Optional[threading.Event] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
    status_callback: Optional[Callable[[str], None]] = None,
    api_event_callback: Optional[Callable[[dict], None]] = None,
    lead_writer=None,
    prior_visited_domains: Optional[Set[str]] = None,
) -> Dict:
    """
    Collects leads in rounds until target_count qualifying leads are found.
    Supports pause/resume via threading.Event objects.
    Uses concurrent website enrichment (enrich_workers threads).
    Writes each lead to lead_writer immediately after enrichment.

    Returns dict with: raw_count, by_source, stats, final, target_count, qualifying_count
    """
    def log(msg: str) -> None:
        if progress_callback:
            progress_callback(msg)

    api_events: List[dict] = []

    def emit_api_event(event: dict) -> None:
        api_events.append(event)
        if api_event_callback:
            api_event_callback(event)

    criteria = [f for f, v in [("email", require_email), ("phone", require_phone), ("website", require_website)] if v]
    log(f"Target: {target_count} leads | Required fields: {', '.join(criteria) or 'none'} | "
        f"Workers: {enrich_workers} | Max rounds: {max_rounds}")

    if target_count > 500 and enable_website_parser:
        log(f"⚠️ Large target ({target_count}) with Website Parser — enrichment may take a long time")

    all_raw_by_source: Dict[str, List[Lead]] = {}
    visited_domains: Set[str] = prior_visited_domains.copy() if prior_visited_domains else set()
    final_qualifying: List[Lead] = []
    final_unique: List[Lead] = []
    clean_by_source: Dict[str, List[Lead]] = {}

    combos = max(1, len(cities) * len(categories))
    per_round = max(target_count * 2, combos * 10, 25)

    for attempt in range(max_rounds):
        log(f"--- Round {attempt+1}/{max_rounds}: up to {per_round} per source ---")
        _check_pause(pause_event, resume_event, status_callback, log)

        raw_this_round = _collect_sources(
            cities, categories, per_round,
            enable_search_ch, enable_google_places, enable_google_search,
            log, pause_event, resume_event, status_callback, emit_api_event,
        )

        for src, new_leads in raw_this_round.items():
            existing_domains = {
                extract_domain(l.website)
                for l in all_raw_by_source.get(src, [])
                if l.website
            }
            truly_new = [
                l for l in new_leads
                if not l.website or extract_domain(l.website) not in existing_domains
            ]
            all_raw_by_source.setdefault(src, []).extend(truly_new)
            if truly_new:
                log(f"[{src}] +{len(truly_new)} new leads accumulated")

        total_raw = sum(len(v) for v in all_raw_by_source.values())
        log(f"Processing {total_raw} accumulated raw leads ...")

        clean_by_source = _process_all(
            all_raw_by_source, visited_domains,
            enable_website_parser, enable_firecrawl, enrich_workers,
            log, lead_writer,
            pause_event, resume_event, status_callback, emit_api_event,
        )

        all_clean = [l for leads in clean_by_source.values() for l in leads]
        final_unique = deduplicate(all_clean)
        final_qualifying = [l for l in final_unique if _meets_quality(l, require_email, require_phone, require_website)]

        log(f"Round {attempt+1}: {len(final_qualifying)}/{target_count} qualifying | {len(final_unique)} total unique")

        if len(final_qualifying) >= target_count:
            log(f"✓ Target reached! Returning top {target_count} qualifying leads.")
            break

        if attempt < max_rounds - 1:
            gap = target_count - len(final_qualifying)
            log(f"Need {gap} more qualifying leads. Starting next round ...")
            per_round = min(int(per_round * 2), 1000)
        else:
            log(f"Max rounds reached. Found {len(final_qualifying)}/{target_count} qualifying leads.")

    raw_count = sum(len(v) for v in all_raw_by_source.values())
    stats = compute_source_stats(clean_by_source)

    return {
        "raw_count": raw_count,
        "by_source": clean_by_source,
        "stats": stats,
        "final": final_qualifying[:target_count],
        "all_qualified": final_qualifying,
        "unique_count": len(final_unique),
        "target_count": target_count,
        "qualifying_count": len(final_qualifying),
        "api_events": api_events,
    }
