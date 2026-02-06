# Phase 7 Research: ASX Futures Integration

## Problem Statement

The existing `pipeline/ingest/asx_futures_scraper.py` uses BeautifulSoup to parse the ASX Rate Tracker page, but that page is a JavaScript SPA. Static HTML scraping always fails — the scraper raises ValueError because no futures table exists in the raw HTML.

## Discovered API Endpoints

Research identified 4 public endpoints that return JSON data (disguised as `.csv` URLs):

### 1. ASX DAM Dynamic Text (Current Rate Context)
- **URL**: `https://www.asx.com.au/data/ASX_RateTracker_DynamicText.csv`
- **Format**: JSON object with fields like `currentCashRate`, `lastUpdated`, `nextMeetingDate`
- **Use**: Get current RBA cash rate and meeting schedule

### 2. ASX DAM Yield Curve
- **URL**: `https://www.asx.com.au/data/ASX_RateTracker_YieldCurve.csv`
- **Format**: JSON array of yield curve points
- **Use**: Background context (optional)

### 3. ASX DAM Market Expectations
- **URL**: `https://www.asx.com.au/data/ASX_RateTracker_MarketExpectation.csv`
- **Format**: JSON array of meeting-by-meeting rate expectations
- **Use**: **Primary data source** — implied rate and probability for each upcoming RBA meeting

### 4. Markit Digital Futures API
- **URL**: `https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures`
- **Format**: JSON with settlement prices per contract month
- **Use**: Alternative/supplementary — raw settlement prices (implied rate = 100 - price)

## Data Contracts

### Output CSV: `data/asx_futures.csv`
Schema (7 columns):
```
date,meeting_date,implied_rate,change_bp,probability_cut,probability_hold,probability_hike
```

### Status.json: Top-level `asx_futures` key
```json
{
  "asx_futures": {
    "current_rate": 4.35,
    "next_meeting": "2026-02-18",
    "implied_rate": 4.10,
    "probabilities": { "cut": 85, "hold": 15, "hike": 0 },
    "direction": "cut",
    "data_date": "2026-02-07",
    "staleness_days": 0
  }
}
```

## Probability Derivation Logic
- `change_bp = (implied_rate - current_rate) * 100`
- If change < -5bp: direction = "cut", probability_cut = min(100, abs(change_bp) / 25 * 100)
- If change > +5bp: direction = "hike", probability_hike = min(100, change_bp / 25 * 100)
- Otherwise: direction = "hold", probability_hold = 100
- Probabilities always sum to ~100

## Architecture Notes
- ASX futures is excluded from hawk score calculation (`exclude_benchmark=True` in gauge.py)
- `INDICATOR_CONFIG["asx_futures"]` already exists as a stub in config.py with `csv_file: None`, `normalize: "direct"`, `frequency: "monthly"`
- Frontend already has "What Markets Expect" section that shows placeholder when data unavailable
- `fetch_and_save()` interface must be preserved — CI workflow depends on it
- Existing scraper returns `{'status': 'failed', 'error': ...}` on failure — new version should return `{'status': 'success', 'rows_saved': N}`

## Key Files
- `pipeline/ingest/asx_futures_scraper.py` — Complete rewrite target
- `pipeline/config.py` — Add ASX_FUTURES_URLS, activate INDICATOR_CONFIG stub
- `pipeline/normalize/engine.py` — Add build_asx_futures_entry()
- `pipeline/normalize/ratios.py` — Add load_asx_futures_csv() loader
- `.github/workflows/daily-asx-futures.yml` — Update to regenerate status.json
- `.github/workflows/weekly-pipeline.yml` — Commit public/data/status.json
- `data/weights.json` — asx_futures weight already set to 0.10
