import os
from typing import List, Dict
from datetime import datetime
from models import Lead


def compute_source_stats(source_leads: Dict[str, List[Lead]]) -> List[Dict]:
    """
    source_leads: dict mapping source name → list of enriched, scored leads
                  evaluated independently per source (no cross-source dedup).
    """
    stats = []
    for src, leads in source_leads.items():
        stats.append({
            "source": src,
            "records_collected": len(leads),
            "emails_found": sum(1 for l in leads if l.email),
            "phones_found": sum(1 for l in leads if l.phone),
            "websites_found": sum(1 for l in leads if l.website),
            "email_rate_%": round(100 * sum(1 for l in leads if l.email) / len(leads), 1) if leads else 0,
            "phone_rate_%": round(100 * sum(1 for l in leads if l.phone) / len(leads), 1) if leads else 0,
            "average_quality_score": (
                round(sum(l.quality_score for l in leads) / len(leads), 1) if leads else 0
            ),
        })
    return stats


def generate_summary_md(
    raw_count: int,
    final_leads: List[Lead],
    source_stats: List[Dict],
    output_path: str,
) -> str:
    total_email = sum(1 for l in final_leads if l.email)
    total_phone = sum(1 for l in final_leads if l.phone)
    total_web = sum(1 for l in final_leads if l.website)

    best_quality = max(source_stats, key=lambda x: x["average_quality_score"], default={})
    best_email = max(source_stats, key=lambda x: x["email_rate_%"], default={})
    best_phone = max(source_stats, key=lambda x: x["phone_rate_%"], default={})

    lines = [
        "# Swiss B2B Lead Source Validation — Summary",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Overall Statistics",
        f"- Raw records collected: **{raw_count}**",
        f"- After cross-source deduplication: **{len(final_leads)}**",
        f"- Records with phone: **{total_phone}**",
        f"- Records with email: **{total_email}**",
        f"- Records with website: **{total_web}**",
        "",
        "## Per-Source Comparison (independent evaluation)",
        "",
        "| Source | Leads | Phones | Phone% | Emails | Email% | Avg Score |",
        "|--------|------:|-------:|-------:|-------:|-------:|----------:|",
    ]
    for s in source_stats:
        lines.append(
            f"| {s['source']} | {s['records_collected']} "
            f"| {s['phones_found']} | {s['phone_rate_%']}% "
            f"| {s['emails_found']} | {s['email_rate_%']}% "
            f"| {s['average_quality_score']} |"
        )

    lines += [
        "",
        "## Source Breakdown",
    ]
    for stat in source_stats:
        lines += [
            f"### {stat['source']}",
            f"- Unique leads (after within-source dedup): {stat['records_collected']}",
            f"- With phone: {stat['phones_found']} ({stat['phone_rate_%']}%)",
            f"- With email: {stat['emails_found']} ({stat['email_rate_%']}%)",
            f"- With website: {stat['websites_found']}",
            f"- Avg quality score: {stat['average_quality_score']} / 100",
            "",
        ]

    lines += [
        "## Conclusions",
        f"- Best source for overall quality: **{best_quality.get('source', 'n/a')}** "
        f"(avg score: {best_quality.get('average_quality_score', 0)})",
        f"- Best source for emails: **{best_email.get('source', 'n/a')}** "
        f"({best_email.get('email_rate_%', 0)}% email rate)",
        f"- Best source for phones: **{best_phone.get('source', 'n/a')}** "
        f"({best_phone.get('phone_rate_%', 0)}% phone rate)",
        "",
        "## Recommended Next Steps",
        "- Scale the best-performing source",
        "- Evaluate API cost per 1,000 leads for each source",
        "- Consider proxy rotation for large-scale search.ch scraping",
        "- Add fuzzy name matching to deduplication (rapidfuzz)",
    ]

    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[summary] Written to {output_path}")
    return content
