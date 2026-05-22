import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from processing.normalize import normalize_lead
from processing.deduplicate import deduplicate
from processing.quality_score import calculate_quality_score
from processing.summary import compute_source_stats, generate_summary_md
from exporters.csv_exporter import export as export_csv
from exporters.excel_exporter import export as export_excel


def _process_source(leads, source_name, enrich_websites=True, enrich_firecrawl=True):
    """Normalize → dedup → enrich → re-normalize → score for one source."""
    if not leads:
        return []
    leads = [normalize_lead(l) for l in leads]
    leads = deduplicate(leads)
    print(f"  [{source_name}] After dedup: {len(leads)} unique leads")

    if enrich_websites and Config.ENABLE_WEBSITE_PARSER:
        from sources.website_parser import enrich_leads
        leads = enrich_leads(leads)

    if enrich_firecrawl and Config.ENABLE_FIRECRAWL:
        from sources.firecrawl_parser import enrich_leads as fc_enrich
        leads = fc_enrich(leads)

    leads = [normalize_lead(l) for l in leads]
    for lead in leads:
        lead.quality_score = calculate_quality_score(lead)
    return leads


def main():
    print("=" * 60)
    print("Swiss B2B Lead Source Validation Script")
    print("=" * 60)
    print(f"Cities    : {Config.CITIES}")
    print(f"Categories: {Config.CATEGORIES}")
    print(f"Max/query : {Config.MAX_RESULTS_PER_QUERY}")
    print()

    os.makedirs(Config.OUTPUT_DIR, exist_ok=True)

    # ── Collect raw leads per source ─────────────────────────────
    raw_by_source = {}

    if Config.ENABLE_SEARCH_CH:
        print("[main] Collecting: search.ch ...")
        from sources.search_ch import collect as c
        raw_by_source["search.ch"] = c(Config.CITIES, Config.CATEGORIES, Config.MAX_RESULTS_PER_QUERY)
    else:
        print("[main] search.ch disabled")

    if Config.ENABLE_GOOGLE_SEARCH:
        print("[main] Collecting: Google Search ...")
        from sources.google_search import collect as c
        raw_by_source["google_search"] = c(Config.CITIES, Config.CATEGORIES, Config.MAX_RESULTS_PER_QUERY)
    else:
        print("[main] Google Search disabled (no API key)")

    if Config.ENABLE_GOOGLE_PLACES:
        print("[main] Collecting: Google Places ...")
        from sources.google_places import collect as c
        raw_by_source["google_places"] = c(Config.CITIES, Config.CATEGORIES, Config.MAX_RESULTS_PER_QUERY)
    else:
        print("[main] Google Places disabled (no API key)")

    all_raw = [l for leads in raw_by_source.values() for l in leads]
    print(f"\n[main] Total raw: {len(all_raw)} leads across {len(raw_by_source)} source(s)")

    # Save raw CSV before any processing
    all_normalized_raw = [normalize_lead(l) for l in all_raw]
    export_csv(all_normalized_raw, os.path.join(Config.OUTPUT_DIR, "leads_raw.csv"))

    # ── Process each source independently for comparison ─────────
    print("\n[main] Processing each source independently ...")
    clean_by_source = {}
    for source_name, leads in raw_by_source.items():
        print(f"\n  [{source_name}] Processing {len(leads)} raw leads ...")
        clean_by_source[source_name] = _process_source(leads, source_name)

    # ── Compute per-source stats (before cross-source merge) ──────
    source_stats = compute_source_stats(clean_by_source)

    # ── Cross-source dedup for final combined output ──────────────
    print("\n[main] Cross-source deduplication ...")
    all_clean = [l for leads in clean_by_source.values() for l in leads]
    final = deduplicate(all_clean)
    print(f"[main] Final unique leads: {len(final)}")

    # ── Export ────────────────────────────────────────────────────
    export_excel(final, os.path.join(Config.OUTPUT_DIR, "leads_clean.xlsx"), source_stats)
    generate_summary_md(
        raw_count=len(all_raw),
        final_leads=final,
        source_stats=source_stats,
        output_path=os.path.join(Config.OUTPUT_DIR, "summary.md"),
    )

    print()
    print("=" * 60)
    print(f"Output: {Config.OUTPUT_DIR}/")
    print(f"  leads_raw.csv    — {len(all_raw)} raw records")
    print(f"  leads_clean.xlsx — {len(final)} final unique leads")
    print(f"  summary.md       — per-source comparison report")
    print()
    print("Per-source results:")
    for stat in source_stats:
        print(
            f"  {stat['source']:20s}: {stat['records_collected']:3d} leads | "
            f"phone {stat['phone_rate_%']:5.1f}% | "
            f"email {stat['email_rate_%']:5.1f}% | "
            f"score {stat['average_quality_score']}"
        )
    print("=" * 60)


if __name__ == "__main__":
    main()
