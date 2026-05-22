import os
from typing import List, Dict
import pandas as pd
from models import Lead


def export(leads: List[Lead], filepath: str, source_stats: List[Dict] = None) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    if not leads:
        print("[excel_exporter] No leads to export")
        return

    df_leads = pd.DataFrame([l.to_dict() for l in leads])
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df_leads.to_excel(writer, sheet_name="leads", index=False)
        if source_stats:
            pd.DataFrame(source_stats).to_excel(writer, sheet_name="source_summary", index=False)

        for sheet_name, ws in writer.sheets.items():
            for col in ws.columns:
                max_len = max(len(str(cell.value or "")) for cell in col)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 50)

    print(f"[excel_exporter] {len(leads)} leads → {filepath}")
