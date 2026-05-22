# Swiss B2B Lead Source Validation Script

Validation script for collecting Swiss B2B company leads from multiple sources, normalizing, deduplicating, and exporting to CSV/Excel.

## Setup

```bash
pip install -r requirements.txt
copy .env.example .env
# Edit .env — fill in any available API keys
```

## Run

```bash
python main.py
```

## Output

```
output/
├── leads_raw.csv      # All collected records before deduplication
├── leads_clean.xlsx   # Cleaned leads (sheet 1) + source stats (sheet 2)
└── summary.md         # Source quality report
```

## Configuration

Edit `config.py` to change targets:

```python
CITIES = ["Zurich", "Geneva", "Basel"]
CATEGORIES = ["garages", "schools", "corporate gifts"]
MAX_RESULTS_PER_QUERY = 50
```

## Sources

| Source | API Key | Notes |
|--------|---------|-------|
| search.ch | None | Swiss phone directory — always enabled |
| Google Search | `SERP_API_KEY` or `TAVILY_API_KEY` | Company website discovery |
| Google Places | `GOOGLE_API_KEY` | Structured company data |
| Website Parser | None | Email/phone extraction — always enabled |
| Firecrawl | `FIRECRAWL_API_KEY` | Enhanced website text extraction |

Sources without API keys are automatically skipped.

## Data Pipeline

```
search.ch / Google Search / Google Places
    ↓
Normalize (phone → +41..., email → lowercase, website → https)
    ↓
Website Parser (visit company sites, extract email/phone from impressum)
    ↓
Deduplicate (by domain, email, phone, name+city — merge missing fields)
    ↓
Quality Score (0–100 based on field presence)
    ↓
Export → leads_raw.csv, leads_clean.xlsx, summary.md
```

## Output Fields

`company_name`, `industry`, `street`, `postal_code`, `city`, `canton`, `country`,
`phone`, `email`, `website`, `source`, `source_url`, `contact_page_url`,
`status`, `notes`, `linkedin_company_url`, `contact_person`, `contact_role`, `quality_score`

## Tests

```bash
python -m pytest tests/ -v
```
