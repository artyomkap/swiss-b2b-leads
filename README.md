# Swiss B2B Lead Generation

FastAPI + SQLite tool for collecting Swiss B2B leads from multiple sources, enriching company websites, deduplicating records, and exporting results to Excel or CSV.

## Features

- Web UI with live progress via Server-Sent Events
- Sources: search.ch, Google Places, Google Search via SerpAPI or Tavily
- Optional website and Firecrawl enrichment
- SQLite history with progressive lead saving
- Pause, resume, and restart interrupted searches
- Excel and CSV exports

## Setup

```powershell
cd swiss_b2b_leads
.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Fill `.env` with any available API keys:

```env
GOOGLE_API_KEY=
SERP_API_KEY=
TAVILY_API_KEY=
FIRECRAWL_API_KEY=
SEARCH_CH_API_KEY=
OUTPUT_DIR=output
MAX_RESULTS_PER_QUERY=50
```

`search.ch` works without an API key.

## Run Web App

```powershell
cd swiss_b2b_leads
.venv\Scripts\python.exe app_server.py
```

Open `http://localhost:8000`.

## Run Tests

```powershell
cd swiss_b2b_leads
.venv\Scripts\python.exe -m pytest tests/ -v
```

## Notes

Runtime data is stored under `swiss_b2b_leads/output/` and is intentionally not committed. Local API keys are stored in `.env`, which is also ignored.
