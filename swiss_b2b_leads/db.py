import json
import os
import queue
import sqlite3
import threading
import time
from typing import List, Optional

from models import Lead

_BASE = os.path.dirname(os.path.abspath(__file__))
_DB_PATH = os.path.join(_BASE, "output", "leads.db")

_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not hasattr(_local, "conn"):
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        c = sqlite3.connect(_DB_PATH, check_same_thread=False)
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA synchronous=NORMAL")
        c.row_factory = sqlite3.Row
        _local.conn = c
    return _local.conn


def init() -> None:
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS searches (
            id          TEXT PRIMARY KEY,
            timestamp   TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'running',
            params      TEXT NOT NULL DEFAULT '{}',
            target_count    INTEGER DEFAULT 0,
            raw_count       INTEGER DEFAULT 0,
            qualifying_count INTEGER DEFAULT 0,
            lead_count      INTEGER DEFAULT 0,
            error_msg       TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS leads (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id   TEXT NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
            domain      TEXT DEFAULT '',
            company_name TEXT DEFAULT '',
            industry    TEXT DEFAULT '',
            street      TEXT DEFAULT '',
            postal_code TEXT DEFAULT '',
            city        TEXT DEFAULT '',
            canton      TEXT DEFAULT '',
            country     TEXT DEFAULT 'Switzerland',
            phone       TEXT DEFAULT '',
            email       TEXT DEFAULT '',
            website     TEXT DEFAULT '',
            source      TEXT DEFAULT '',
            source_url  TEXT DEFAULT '',
            contact_page_url TEXT DEFAULT '',
            status      TEXT DEFAULT '',
            notes       TEXT DEFAULT '',
            linkedin_company_url TEXT DEFAULT '',
            contact_person TEXT DEFAULT '',
            contact_role   TEXT DEFAULT '',
            quality_score  INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_leads_search  ON leads(search_id);
        CREATE INDEX IF NOT EXISTS idx_leads_domain  ON leads(domain);
        CREATE INDEX IF NOT EXISTS idx_leads_email   ON leads(email);
        CREATE INDEX IF NOT EXISTS idx_leads_phone   ON leads(phone);

        CREATE TABLE IF NOT EXISTS stats (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id   TEXT NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
            source      TEXT DEFAULT '',
            records_collected INTEGER DEFAULT 0,
            phones_found  INTEGER DEFAULT 0,
            emails_found  INTEGER DEFAULT 0,
            phone_rate    REAL DEFAULT 0,
            email_rate    REAL DEFAULT 0,
            average_quality_score REAL DEFAULT 0
        );
    """)
    c.commit()


def mark_interrupted() -> None:
    c = _conn()
    c.execute("UPDATE searches SET status='interrupted' WHERE status='running'")
    c.commit()


def create_search(search_id: str, timestamp: str, params: dict, target_count: int) -> None:
    c = _conn()
    c.execute(
        "INSERT OR REPLACE INTO searches (id, timestamp, status, params, target_count) VALUES (?,?,?,?,?)",
        (search_id, timestamp, "running", json.dumps(params, ensure_ascii=False), target_count),
    )
    c.commit()


def update_search(search_id: str, **kwargs) -> None:
    if not kwargs:
        return
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [search_id]
    _conn().execute(f"UPDATE searches SET {cols} WHERE id=?", vals)
    _conn().commit()


def upsert_stats(search_id: str, stats: list) -> None:
    c = _conn()
    c.execute("DELETE FROM stats WHERE search_id=?", (search_id,))
    for s in stats:
        c.execute(
            """INSERT INTO stats (search_id, source, records_collected, phones_found, emails_found,
               phone_rate, email_rate, average_quality_score)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                search_id,
                s.get("source", ""),
                s.get("records_collected", 0),
                s.get("phones_found", 0),
                s.get("emails_found", 0),
                s.get("phone_rate_%", 0),
                s.get("email_rate_%", 0),
                s.get("average_quality_score", 0),
            ),
        )
    c.commit()


def get_visited_domains(search_id: str) -> set:
    rows = _conn().execute(
        "SELECT DISTINCT domain FROM leads WHERE search_id=? AND domain!=''", (search_id,)
    ).fetchall()
    return {r["domain"] for r in rows}


def list_searches() -> list:
    rows = _conn().execute(
        "SELECT * FROM searches ORDER BY timestamp DESC"
    ).fetchall()
    result = []
    for r in rows:
        stats_rows = _conn().execute(
            "SELECT * FROM stats WHERE search_id=?", (r["id"],)
        ).fetchall()
        result.append({
            "id": r["id"],
            "timestamp": r["timestamp"],
            "status": r["status"],
            "params": json.loads(r["params"]),
            "summary": {
                "raw_count": r["raw_count"],
                "qualifying_count": r["qualifying_count"],
                "lead_count": r["lead_count"],
            },
            "stats": [_stat_row(s) for s in stats_rows],
        })
    return result


def get_search(search_id: str) -> Optional[dict]:
    r = _conn().execute("SELECT * FROM searches WHERE id=?", (search_id,)).fetchone()
    if not r:
        return None
    leads_rows = _conn().execute(
        "SELECT * FROM leads WHERE search_id=?", (search_id,)
    ).fetchall()
    stats_rows = _conn().execute(
        "SELECT * FROM stats WHERE search_id=?", (search_id,)
    ).fetchall()
    return {
        "id": r["id"],
        "timestamp": r["timestamp"],
        "status": r["status"],
        "params": json.loads(r["params"]),
        "summary": {
            "raw_count": r["raw_count"],
            "qualifying_count": r["qualifying_count"],
            "lead_count": r["lead_count"],
        },
        "stats": [_stat_row(s) for s in stats_rows],
        "leads": [_lead_row(l) for l in leads_rows],
    }


def get_leads_for_searches(search_ids: List[str]) -> List[dict]:
    placeholders = ",".join("?" * len(search_ids))
    rows = _conn().execute(
        f"SELECT * FROM leads WHERE search_id IN ({placeholders})", search_ids
    ).fetchall()
    return [_lead_row(r) for r in rows]


def delete_search(search_id: str) -> bool:
    c = _conn()
    cur = c.execute("DELETE FROM searches WHERE id=?", (search_id,))
    c.commit()
    return cur.rowcount > 0


def _stat_row(r) -> dict:
    return {
        "source": r["source"],
        "records_collected": r["records_collected"],
        "phones_found": r["phones_found"],
        "emails_found": r["emails_found"],
        "phone_rate_%": r["phone_rate"],
        "email_rate_%": r["email_rate"],
        "average_quality_score": r["average_quality_score"],
    }


def _lead_row(r) -> dict:
    return {
        "company_name": r["company_name"],
        "industry": r["industry"],
        "street": r["street"],
        "postal_code": r["postal_code"],
        "city": r["city"],
        "canton": r["canton"],
        "country": r["country"],
        "phone": r["phone"],
        "email": r["email"],
        "website": r["website"],
        "source": r["source"],
        "source_url": r["source_url"],
        "contact_page_url": r["contact_page_url"],
        "status": r["status"],
        "notes": r["notes"],
        "linkedin_company_url": r["linkedin_company_url"],
        "contact_person": r["contact_person"],
        "contact_role": r["contact_role"],
        "quality_score": r["quality_score"],
    }


class LeadWriter:
    """Single-writer thread that batches leads from a Queue into SQLite."""

    _BATCH = 20
    _TIMEOUT = 1.0
    _SENTINEL = None

    def __init__(self, search_id: str):
        self.search_id = search_id
        self._q: queue.Queue = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def write(self, lead: Lead) -> None:
        """Non-blocking — puts lead to queue, returns immediately."""
        self._q.put(lead)

    def flush(self) -> None:
        """Block until all queued leads have been written."""
        self._q.join()

    def close(self) -> None:
        """Flush then stop the writer thread."""
        self.flush()
        self._q.put(self._SENTINEL)
        self._thread.join()

    def _run(self) -> None:
        conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        batch: List[Lead] = []

        def _flush_batch():
            if not batch:
                return
            conn.executemany(
                """INSERT INTO leads (
                    search_id, domain, company_name, industry, street, postal_code,
                    city, canton, country, phone, email, website, source, source_url,
                    contact_page_url, status, notes, linkedin_company_url,
                    contact_person, contact_role, quality_score
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                [_lead_tuple(self.search_id, l) for l in batch],
            )
            conn.commit()
            for _ in batch:
                self._q.task_done()
            batch.clear()

        while True:
            try:
                item = self._q.get(timeout=self._TIMEOUT)
            except queue.Empty:
                _flush_batch()
                continue

            if item is self._SENTINEL:
                _flush_batch()
                self._q.task_done()
                break

            batch.append(item)
            if len(batch) >= self._BATCH:
                _flush_batch()

        conn.close()


def _lead_tuple(search_id: str, lead: Lead) -> tuple:
    from processing.normalize import extract_domain
    return (
        search_id,
        extract_domain(lead.website) or "",
        lead.company_name,
        lead.industry,
        lead.street,
        lead.postal_code,
        lead.city,
        lead.canton,
        lead.country,
        lead.phone,
        lead.email,
        lead.website,
        lead.source,
        lead.source_url,
        lead.contact_page_url,
        lead.status,
        lead.notes,
        lead.linkedin_company_url,
        lead.contact_person,
        lead.contact_role,
        lead.quality_score,
    )
