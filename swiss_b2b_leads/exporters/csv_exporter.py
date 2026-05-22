import os
import csv
from typing import List
from models import Lead


def export(leads: List[Lead], filepath: str) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    if not leads:
        print("[csv_exporter] No leads to export")
        return
    fieldnames = list(leads[0].to_dict().keys())
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow(lead.to_dict())
    print(f"[csv_exporter] {len(leads)} leads → {filepath}")
