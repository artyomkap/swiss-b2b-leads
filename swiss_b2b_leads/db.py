import json
import os
import queue
import sqlite3
import threading
import time
from datetime import datetime
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

        CREATE TABLE IF NOT EXISTS search_locations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id   TEXT NOT NULL REFERENCES searches(id) ON DELETE CASCADE,
            input_type  TEXT DEFAULT '',
            input_value TEXT DEFAULT '',
            input_label TEXT DEFAULT '',
            coverage_mode TEXT DEFAULT '',
            expanded_terms_json TEXT DEFAULT '[]',
            expanded_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS api_key_status (
            provider    TEXT PRIMARY KEY,
            status      TEXT NOT NULL DEFAULT 'ok',
            last_error_msg TEXT DEFAULT '',
            last_status_code INTEGER,
            last_checked_at TEXT DEFAULT '',
            blocked_until TEXT DEFAULT '',
            failures_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS api_events (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            search_id   TEXT DEFAULT '',
            provider    TEXT DEFAULT '',
            event_type  TEXT DEFAULT '',
            status_code INTEGER,
            error_code  TEXT DEFAULT '',
            message     TEXT DEFAULT '',
            detected_at TEXT DEFAULT '',
            action_taken TEXT DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_search_locations_search ON search_locations(search_id);
        CREATE INDEX IF NOT EXISTS idx_api_events_search ON api_events(search_id);
        CREATE INDEX IF NOT EXISTS idx_api_events_provider ON api_events(provider);
    """)
    _ensure_search_columns(c)
    c.commit()


def _ensure_search_columns(c: sqlite3.Connection) -> None:
    existing = {row["name"] for row in c.execute("PRAGMA table_info(searches)").fetchall()}
    columns = {
        "location_summary": "TEXT DEFAULT ''",
        "estimated_queries": "INTEGER DEFAULT 0",
        "estimated_api_calls": "INTEGER DEFAULT 0",
        "cost_warning_level": "TEXT DEFAULT 'low'",
        "api_limit_warnings_count": "INTEGER DEFAULT 0",
    }
    for name, ddl in columns.items():
        if name not in existing:
            c.execute(f"ALTER TABLE searches ADD COLUMN {name} {ddl}")


def mark_interrupted() -> None:
    c = _conn()
    c.execute("UPDATE searches SET status='interrupted' WHERE status='running'")
    c.commit()


def create_search(
    search_id: str,
    timestamp: str,
    params: dict,
    target_count: int,
    estimate: Optional[dict] = None,
) -> None:
    estimate = estimate or {}
    c = _conn()
    c.execute(
        """INSERT OR REPLACE INTO searches (
            id, timestamp, status, params, target_count, location_summary,
            estimated_queries, estimated_api_calls, cost_warning_level
        ) VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            search_id,
            timestamp,
            "running",
            json.dumps(params, ensure_ascii=False),
            target_count,
            estimate.get("location_summary", ""),
            estimate.get("estimated_queries", 0),
            estimate.get("estimated_api_calls", 0),
            estimate.get("warning_level", "low"),
        ),
    )
    c.commit()


def save_search_locations(search_id: str, locations: list, expanded_locations: list) -> None:
    c = _conn()
    c.execute("DELETE FROM search_locations WHERE search_id=?", (search_id,))
    for loc in locations:
        expanded = loc.get("expanded_terms") or expanded_locations
        c.execute(
            """INSERT INTO search_locations (
                search_id, input_type, input_value, input_label, coverage_mode,
                expanded_terms_json, expanded_count
            ) VALUES (?,?,?,?,?,?,?)""",
            (
                search_id,
                loc.get("type", ""),
                loc.get("value", ""),
                loc.get("label", ""),
                loc.get("coverage_mode", ""),
                json.dumps(expanded, ensure_ascii=False),
                len(expanded),
            ),
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


def record_api_event(search_id: str, event: dict) -> None:
    c = _conn()
    detected_at = event.get("detected_at") or datetime.now().isoformat()
    c.execute(
        """INSERT INTO api_events (
            search_id, provider, event_type, status_code, error_code,
            message, detected_at, action_taken
        ) VALUES (?,?,?,?,?,?,?,?)""",
        (
            search_id,
            event.get("provider", ""),
            event.get("event_type", ""),
            event.get("status_code"),
            event.get("error_code", ""),
            event.get("message", ""),
            detected_at,
            event.get("action_taken", ""),
        ),
    )
    if event.get("event_type") in {"quota_exceeded", "rate_limited", "invalid_key", "unknown_error", "missing"}:
        upsert_api_key_status(
            event.get("provider", ""),
            event.get("event_type", "unknown_error"),
            event.get("message", ""),
            event.get("status_code"),
        )
    count = c.execute(
        "SELECT COUNT(*) AS n FROM api_events WHERE search_id=? AND event_type IN ('quota_exceeded','rate_limited','invalid_key')",
        (search_id,),
    ).fetchone()["n"]
    c.execute("UPDATE searches SET api_limit_warnings_count=? WHERE id=?", (count, search_id))
    c.commit()


def upsert_api_key_status(
    provider: str,
    status: str,
    last_error_msg: str = "",
    last_status_code: Optional[int] = None,
    blocked_until: str = "",
) -> None:
    if not provider:
        return
    c = _conn()
    now = datetime.now().isoformat()
    existing = c.execute(
        "SELECT failures_count FROM api_key_status WHERE provider=?", (provider,)
    ).fetchone()
    failures = (existing["failures_count"] if existing else 0) + (0 if status == "ok" else 1)
    c.execute(
        """INSERT INTO api_key_status (
            provider, status, last_error_msg, last_status_code,
            last_checked_at, blocked_until, failures_count
        ) VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(provider) DO UPDATE SET
            status=excluded.status,
            last_error_msg=excluded.last_error_msg,
            last_status_code=excluded.last_status_code,
            last_checked_at=excluded.last_checked_at,
            blocked_until=excluded.blocked_until,
            failures_count=excluded.failures_count""",
        (provider, status, last_error_msg, last_status_code, now, blocked_until, failures),
    )
    c.commit()


def reset_api_key_status(provider: str) -> None:
    upsert_api_key_status(provider, "ok", "", None, "")


def get_api_key_statuses() -> dict:
    rows = _conn().execute("SELECT * FROM api_key_status").fetchall()
    return {
        r["provider"]: {
            "provider": r["provider"],
            "status": r["status"],
            "last_error_msg": r["last_error_msg"],
            "last_status_code": r["last_status_code"],
            "last_checked_at": r["last_checked_at"],
            "blocked_until": r["blocked_until"],
            "failures_count": r["failures_count"],
        }
        for r in rows
    }


def get_api_events(search_id: str) -> list:
    rows = _conn().execute(
        "SELECT * FROM api_events WHERE search_id=? ORDER BY id ASC", (search_id,)
    ).fetchall()
    return [_api_event_row(r) for r in rows]


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
        location_rows = _conn().execute(
            "SELECT * FROM search_locations WHERE search_id=?", (r["id"],)
        ).fetchall()
        api_event_rows = _conn().execute(
            "SELECT * FROM api_events WHERE search_id=? ORDER BY id ASC", (r["id"],)
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
            "location_summary": r["location_summary"],
            "estimated_queries": r["estimated_queries"],
            "estimated_api_calls": r["estimated_api_calls"],
            "cost_warning_level": r["cost_warning_level"],
            "api_limit_warnings_count": r["api_limit_warnings_count"],
            "locations": [_search_location_row(l) for l in location_rows],
            "api_events": [_api_event_row(e) for e in api_event_rows],
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
    location_rows = _conn().execute(
        "SELECT * FROM search_locations WHERE search_id=?", (search_id,)
    ).fetchall()
    api_event_rows = _conn().execute(
        "SELECT * FROM api_events WHERE search_id=? ORDER BY id ASC", (search_id,)
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
        "location_summary": r["location_summary"],
        "estimated_queries": r["estimated_queries"],
        "estimated_api_calls": r["estimated_api_calls"],
        "cost_warning_level": r["cost_warning_level"],
        "api_limit_warnings_count": r["api_limit_warnings_count"],
        "locations": [_search_location_row(l) for l in location_rows],
        "api_events": [_api_event_row(e) for e in api_event_rows],
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
    c.execute("DELETE FROM leads WHERE search_id=?", (search_id,))
    c.execute("DELETE FROM stats WHERE search_id=?", (search_id,))
    c.execute("DELETE FROM search_locations WHERE search_id=?", (search_id,))
    c.execute("DELETE FROM api_events WHERE search_id=?", (search_id,))
    cur = c.execute("DELETE FROM searches WHERE id=?", (search_id,))
    c.commit()
    return cur.rowcount > 0


def _search_location_row(r) -> dict:
    return {
        "input_type": r["input_type"],
        "input_value": r["input_value"],
        "input_label": r["input_label"],
        "coverage_mode": r["coverage_mode"],
        "expanded_terms": json.loads(r["expanded_terms_json"] or "[]"),
        "expanded_count": r["expanded_count"],
    }


def _api_event_row(r) -> dict:
    return {
        "provider": r["provider"],
        "event_type": r["event_type"],
        "status_code": r["status_code"],
        "error_code": r["error_code"],
        "message": r["message"],
        "detected_at": r["detected_at"],
        "action_taken": r["action_taken"],
    }


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
