import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
import io
import json
import threading
import uuid
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import db
from config import Config
from models import Lead
from processing.deduplicate import deduplicate
from ui_categories import SWISS_CITIES, INDUSTRIES
from ui_locations import (
    expand_location_selection,
    locations_payload,
    normalize_location_selections,
    search_location_options,
)
from search_estimator import estimate_search

app = FastAPI(title="Swiss B2B Lead Search")
_BASE = os.path.dirname(__file__)
app.mount("/static", StaticFiles(directory=os.path.join(_BASE, "static")), name="static")


@app.on_event("startup")
async def _startup():
    db.init()
    db.mark_interrupted()


# ── Job store ─────────────────────────────────────────────────────────────────
# job_id → {msgs, events, done, status, results, error, pause_event, resume_event, params}
_jobs: dict = {}

# ── Env helpers ───────────────────────────────────────────────────────────────
_ENV_PATH = os.path.join(_BASE, ".env")
_KEY_NAMES = ["GOOGLE_API_KEY", "SERP_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY"]


def _read_env_keys() -> dict:
    values = {k: "" for k in _KEY_NAMES}
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    if k in values:
                        values[k] = v.strip()
    return values


def _write_env_keys(updates: dict) -> None:
    lines = []
    if os.path.exists(_ENV_PATH):
        with open(_ENV_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()
    written = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k in updates:
                new_lines.append(f"{k}={updates[k]}\n")
                written.add(k)
                continue
        new_lines.append(line)
    for k, v in updates.items():
        if k not in written:
            new_lines.append(f"{k}={v}\n")
    with open(_ENV_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


# ── Pydantic models ───────────────────────────────────────────────────────────
class LocationSelection(BaseModel):
    type: str = "custom"
    value: str
    label: str = ""
    coverage_mode: str = "top_cities"


class SearchParams(BaseModel):
    cities: List[str] = Field(default_factory=list)
    locations: List[LocationSelection] = Field(default_factory=list)
    expanded_locations: List[str] = Field(default_factory=list)
    categories: List[str]
    target_count: int = 25
    require_email: bool = False
    require_phone: bool = False
    require_website: bool = False
    max_rounds: int = 3
    enrich_workers: int = 5
    enable_search_ch: bool = True
    enable_google_places: bool = True
    enable_google_search: bool = True
    enable_website_parser: bool = True
    enable_firecrawl: bool = False
    cost_confirmation: bool = False
    cost_override: bool = False


class ApiKeys(BaseModel):
    GOOGLE_API_KEY: str = ""
    SERP_API_KEY: str = ""
    TAVILY_API_KEY: str = ""
    FIRECRAWL_API_KEY: str = ""


class MergeRequest(BaseModel):
    ids: List[str]


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
async def index():
    return FileResponse(os.path.join(_BASE, "static", "index.html"))


@app.get("/history")
async def history_page():
    return FileResponse(os.path.join(_BASE, "static", "history.html"))


@app.get("/api/config")
async def get_config():
    return _config_payload()


@app.get("/api/categories")
async def get_categories():
    return {"cities": SWISS_CITIES, "industries": INDUSTRIES, "locations": locations_payload()}


@app.get("/api/locations")
async def get_locations():
    return locations_payload()


@app.get("/api/locations/search")
async def search_locations(q: str = Query("", min_length=0)):
    return {"items": search_location_options(q)}


@app.post("/api/search/estimate")
async def search_estimate(params: SearchParams):
    return _estimate_for_params(params)


@app.get("/api/api-status")
async def api_status():
    return _api_status_payload()


@app.get("/api/keys")
async def get_keys():
    return _read_env_keys()


@app.post("/api/keys")
async def save_keys(keys: ApiKeys):
    updates = {
        "GOOGLE_API_KEY": keys.GOOGLE_API_KEY,
        "SERP_API_KEY": keys.SERP_API_KEY,
        "TAVILY_API_KEY": keys.TAVILY_API_KEY,
        "FIRECRAWL_API_KEY": keys.FIRECRAWL_API_KEY,
    }
    _write_env_keys(updates)
    Config.GOOGLE_API_KEY = keys.GOOGLE_API_KEY
    Config.SERP_API_KEY = keys.SERP_API_KEY
    Config.TAVILY_API_KEY = keys.TAVILY_API_KEY
    Config.FIRECRAWL_API_KEY = keys.FIRECRAWL_API_KEY
    for provider in ["google_places", "serpapi", "tavily", "google_search", "firecrawl"]:
        db.reset_api_key_status(provider)
    return _config_payload()


def _provider_status(provider: str, available: bool, statuses: dict) -> dict:
    status = statuses.get(provider, {})
    if not available:
        return {"available": False, "status": "missing", "last_error_msg": ""}
    return {
        "available": True,
        "status": status.get("status", "ok"),
        "last_error_msg": status.get("last_error_msg", ""),
        "last_checked_at": status.get("last_checked_at", ""),
    }


def _aggregate_google_search_status(statuses: dict) -> dict:
    if not (Config.SERP_API_KEY or Config.TAVILY_API_KEY):
        return {"available": False, "status": "missing", "last_error_msg": ""}
    for provider in ["serpapi", "tavily", "google_search"]:
        status = statuses.get(provider, {})
        if status.get("status") in {"quota_exceeded", "rate_limited", "invalid_key"}:
            return {
                "available": True,
                "status": status.get("status"),
                "last_error_msg": status.get("last_error_msg", ""),
                "last_checked_at": status.get("last_checked_at", ""),
            }
    return {"available": True, "status": "ok", "last_error_msg": ""}


def _api_status_payload() -> dict:
    statuses = db.get_api_key_statuses()
    return {
        "search_ch": {"available": True, "status": "ok", "last_error_msg": ""},
        "google_places": _provider_status("google_places", bool(Config.GOOGLE_API_KEY), statuses),
        "google_search": _aggregate_google_search_status(statuses),
        "serpapi": _provider_status("serpapi", bool(Config.SERP_API_KEY), statuses),
        "tavily": _provider_status("tavily", bool(Config.TAVILY_API_KEY), statuses),
        "firecrawl": _provider_status("firecrawl", bool(Config.FIRECRAWL_API_KEY), statuses),
    }


def _config_payload() -> dict:
    return _api_status_payload()


def _estimate_for_params(params: SearchParams) -> dict:
    data = params.model_dump()
    estimate = estimate_search(data)
    data["locations"] = estimate["locations"]
    data["expanded_locations"] = estimate["expanded_locations"]
    return estimate


def _normalize_params(params: SearchParams) -> tuple[SearchParams, dict]:
    estimate = _estimate_for_params(params)
    data = params.model_dump()
    data["locations"] = estimate["locations"]
    data["expanded_locations"] = estimate["expanded_locations"]
    data["cities"] = estimate["expanded_locations"]
    normalized = SearchParams(**data)
    return normalized, estimate


def _enforce_cost_guardrails(params: SearchParams, estimate: dict) -> None:
    if not params.categories:
        raise HTTPException(status_code=400, detail={"error": "missing_categories", "message": "Select at least one industry."})
    if not estimate.get("expanded_locations"):
        raise HTTPException(status_code=400, detail={"error": "missing_locations", "message": "Select at least one location."})
    if estimate["warning_level"] == "blocked" and not params.cost_override:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "cost_blocked",
                "message": "Search is too large. Reduce locations/categories or enable explicit override.",
                "estimate": estimate,
            },
        )
    if estimate["warning_level"] in {"high", "blocked"} and not params.cost_confirmation:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "cost_confirmation_required",
                "message": "This search may use many API credits. Confirm before running.",
                "estimate": estimate,
            },
        )


def _locations_for_db(params: SearchParams) -> list:
    locations = [loc.model_dump() for loc in params.locations]
    out = []
    for loc in normalize_location_selections(locations, params.cities):
        loc = dict(loc)
        loc["expanded_terms"] = expand_location_selection(loc)
        out.append(loc)
    return out


def _start_job(job_id: str, params: SearchParams, prior_visited_domains=None) -> None:
    pause_event = threading.Event()
    resume_event = threading.Event()
    _jobs[job_id] = {
        "msgs": [],
        "events": [],
        "done": False,
        "status": "running",
        "results": None,
        "error": None,
        "params": params.model_dump(),
        "pause_event": pause_event,
        "resume_event": resume_event,
    }

    def _run():
        from runner import run_search
        from db import LeadWriter
        writer = LeadWriter(job_id)
        api_events = []

        def progress(msg: str) -> None:
            _jobs[job_id]["msgs"].append(msg)

        def api_event(event: dict) -> None:
            api_events.append(event)
            db.record_api_event(job_id, event)
            _jobs[job_id]["events"].append(event)
            provider = event.get("provider", "api")
            event_type = event.get("event_type", "event")
            message = event.get("message", "")
            _jobs[job_id]["msgs"].append(f"⚠️ [{provider}] {event_type}: {message}")

        try:
            results = run_search(
                cities=params.expanded_locations or params.cities,
                categories=params.categories,
                target_count=params.target_count,
                require_email=params.require_email,
                require_phone=params.require_phone,
                require_website=params.require_website,
                max_rounds=params.max_rounds,
                enrich_workers=params.enrich_workers,
                enable_search_ch=params.enable_search_ch,
                enable_google_places=params.enable_google_places,
                enable_google_search=params.enable_google_search,
                enable_website_parser=params.enable_website_parser,
                enable_firecrawl=params.enable_firecrawl,
                pause_event=pause_event,
                resume_event=resume_event,
                progress_callback=progress,
                status_callback=lambda s: _jobs[job_id].update({"status": s}),
                api_event_callback=api_event,
                lead_writer=writer,
                prior_visited_domains=prior_visited_domains,
            )
            results["api_events"] = api_events
            writer.close()
            _jobs[job_id]["results"] = results
            _jobs[job_id]["status"] = "done"
            db.update_search(
                job_id,
                status="done",
                raw_count=results["raw_count"],
                qualifying_count=results.get("qualifying_count", len(results["final"])),
                lead_count=len(results["final"]),
            )
            db.upsert_stats(job_id, results["stats"])
        except Exception as exc:
            writer.close()
            _jobs[job_id]["error"] = str(exc)
            _jobs[job_id]["status"] = "error"
            db.update_search(job_id, status="error", error_msg=str(exc))
        finally:
            _jobs[job_id]["done"] = True

    threading.Thread(target=_run, daemon=True).start()


@app.post("/api/search")
async def start_search(params: SearchParams):
    params, estimate = _normalize_params(params)
    _enforce_cost_guardrails(params, estimate)
    job_id = str(uuid.uuid4())
    db.create_search(
        job_id,
        datetime.now().isoformat(),
        params.model_dump(),
        params.target_count,
        estimate=estimate,
    )
    db.save_search_locations(job_id, _locations_for_db(params), params.expanded_locations)
    _start_job(job_id, params)
    return {"job_id": job_id, "estimate": estimate}


@app.post("/api/jobs/{job_id}/pause")
async def pause_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["done"]:
        raise HTTPException(409, "Job already finished")
    job["resume_event"].clear()
    job["pause_event"].set()
    job["status"] = "paused"
    db.update_search(job_id, status="paused")
    return {"status": "pause_requested"}


@app.post("/api/jobs/{job_id}/resume")
async def resume_job(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job["done"]:
        raise HTTPException(409, "Job already finished")
    job["pause_event"].clear()
    job["resume_event"].set()
    job["status"] = "running"
    db.update_search(job_id, status="running")
    return {"status": "resumed"}


@app.get("/api/progress/{job_id}")
async def progress_stream(job_id: str):
    async def _generate():
        last = 0
        last_event = 0
        last_status = None
        while True:
            job = _jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'job not found'})}\n\n"
                return

            for msg in job["msgs"][last:]:
                yield f"data: {json.dumps({'msg': msg})}\n\n"
            last = len(job["msgs"])

            for event in job.get("events", [])[last_event:]:
                payload = {
                    "api_limit": event.get("event_type") in {"quota_exceeded", "rate_limited", "invalid_key"},
                    "source_disabled": event.get("action_taken") == "source_disabled",
                    "provider": event.get("provider"),
                    "message": event.get("message"),
                    "severity": event.get("severity", "warning"),
                    "event_type": event.get("event_type"),
                }
                yield f"data: {json.dumps(payload)}\n\n"
            last_event = len(job.get("events", []))

            status = job["status"]
            if status != last_status:
                if status == "paused":
                    yield f"data: {json.dumps({'paused': True})}\n\n"
                elif status == "running" and last_status == "paused":
                    yield f"data: {json.dumps({'resumed': True})}\n\n"
                last_status = status

            if job["done"]:
                count = len(job["results"]["final"]) if job["results"] else 0
                yield f"data: {json.dumps({'done': True, 'count': count, 'error': job['error']})}\n\n"
                return

            await asyncio.sleep(0.3)

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/results/{job_id}")
async def get_results(job_id: str):
    job = _jobs.get(job_id)
    if not job or not job["done"] or not job["results"]:
        return Response(content=json.dumps({"error": "not ready"}), status_code=202)
    r = job["results"]
    return {
        "raw_count": r["raw_count"],
        "stats": r["stats"],
        "leads": [lead.to_dict() for lead in r["final"]],
        "shown_count": len(r["final"]),
        "unique_count": r.get("unique_count", len(r["final"])),
        "target_count": r.get("target_count", 0),
        "qualifying_count": r.get("qualifying_count", len(r["final"])),
        "api_events": r.get("api_events", []),
    }


def _leads_to_excel(leads: list, stats: list) -> bytes:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(leads).to_excel(writer, sheet_name="leads", index=False)
        if stats:
            pd.DataFrame(stats).to_excel(writer, sheet_name="source_summary", index=False)
    return buf.getvalue()


def _export_leads_for_scope(results: dict, scope: str) -> tuple[list, str]:
    if scope == "all_qualified":
        leads = results.get("all_qualified") or results.get("final") or []
        return [l.to_dict() for l in leads], "leads_all_qualified.xlsx"
    leads = results.get("final") or []
    return [l.to_dict() for l in leads], "leads_target.xlsx"


@app.get("/api/export/{job_id}/excel")
async def export_excel(job_id: str, scope: str = Query("target")):
    job = _jobs.get(job_id)
    if not job or not job["results"]:
        return Response("Not found", status_code=404)
    r = job["results"]
    leads, filename = _export_leads_for_scope(r, scope)
    content = _leads_to_excel(leads, r["stats"])
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/export/{job_id}/csv")
async def export_csv(job_id: str):
    job = _jobs.get(job_id)
    if not job or not job["results"]:
        return Response("Not found", status_code=404)
    r = job["results"]
    csv_bytes = (
        pd.DataFrame([l.to_dict() for l in r["final"]])
        .to_csv(index=False)
        .encode("utf-8-sig")
    )
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_clean.csv"},
    )


# ── History endpoints ─────────────────────────────────────────────────────────
@app.get("/api/history")
async def get_history():
    return db.list_searches()


@app.get("/api/history/{history_id}")
async def get_history_entry(history_id: str):
    entry = db.get_search(history_id)
    if not entry:
        raise HTTPException(404, "History entry not found")
    return entry


@app.delete("/api/history/{history_id}")
async def delete_history_entry(history_id: str):
    ok = db.delete_search(history_id)
    if not ok:
        raise HTTPException(404, "History entry not found")
    return {"deleted": history_id}


@app.post("/api/history/merge-export")
async def merge_export(req: MergeRequest):
    """Merge leads from selected history entries, deduplicate, return Excel."""
    if not req.ids:
        raise HTTPException(400, "No history IDs provided")

    lead_dicts = db.get_leads_for_searches(req.ids)
    all_leads = [Lead(**{k: d.get(k, "") for k in Lead.__dataclass_fields__}) for d in lead_dicts]
    for i, l in enumerate(all_leads):
        l.quality_score = lead_dicts[i].get("quality_score", 0)

    merged = deduplicate(all_leads)

    all_stats = []
    for hid in req.ids:
        entry = db.get_search(hid)
        if entry:
            all_stats.extend(entry.get("stats", []))

    content = _leads_to_excel([l.to_dict() for l in merged], all_stats)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=merged_{len(merged)}_leads.xlsx"},
    )


@app.post("/api/history/{history_id}/resume")
async def resume_interrupted(history_id: str):
    """Resume or reconnect to a search. Handles all states:
    - already running in memory → just return job_id (reconnect SSE)
    - interrupted/error/paused/running-but-lost → restart from saved point
    """
    # Job is already alive in memory — just let the caller reconnect to SSE
    job = _jobs.get(history_id)
    if job and not job["done"]:
        return {"job_id": history_id}

    entry = db.get_search(history_id)
    if not entry:
        raise HTTPException(404, "History entry not found")

    params_dict = entry["params"]
    params, estimate = _normalize_params(SearchParams(**params_dict))

    prior_domains = db.get_visited_domains(history_id)
    db.update_search(
        history_id,
        status="running",
        location_summary=estimate.get("location_summary", ""),
        estimated_queries=estimate.get("estimated_queries", 0),
        estimated_api_calls=estimate.get("estimated_api_calls", 0),
        cost_warning_level=estimate.get("warning_level", "low"),
    )
    db.save_search_locations(history_id, _locations_for_db(params), params.expanded_locations)

    _start_job(history_id, params, prior_visited_domains=prior_domains)
    return {"job_id": history_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_server:app", host="0.0.0.0", port=8000, reload=True)
