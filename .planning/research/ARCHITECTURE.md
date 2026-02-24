# Architecture Research

**Domain:** Automated Economic Dashboard — v1.1 Scraper Integration
**Researched:** 2026-02-24
**Confidence:** HIGH (all findings verified against actual codebase)

## Context: Milestone Scope

This document describes how the 3 new data source integrations — CoreLogic
housing prices, NAB capacity utilisation, and ASX IB futures endpoint fix —
fit into the existing v1.0 pipeline architecture.

The existing pipeline is fully operational. The work is **filling stub scrapers
that already have the correct integration contract**. No new architectural
layers, no new patterns. The constraint is scraping techniques and data
extraction, not architecture.

---

## Existing Architecture (Verified from Codebase)

### System Overview

```
┌───────────────────────────────────────────────────────────────────┐
│                  GitHub Actions (Compute / Scheduler)              │
│                                                                     │
│   weekly-pipeline.yml            daily-asx-futures.yml             │
│   Mon 2:07 AM UTC                Weekdays 6:23 AM UTC              │
│   python -m pipeline.main        python -m pipeline.ingest.        │
│                                            asx_futures_scraper     │
│                                  python -m pipeline.normalize.      │
│                                            engine                  │
└──────────────────┬────────────────────────────┬────────────────────┘
                   │                            │
                   ▼                            ▼
┌───────────────────────────────────────────────────────────────────┐
│              pipeline/main.py  (Tiered Orchestrator)               │
│                                                                     │
│  CRITICAL (fail-fast)   IMPORTANT (warn+continue)   OPTIONAL       │
│  ┌────────────────┐     ┌────────────────┐     ┌────────────────┐  │
│  │ rba_data       │     │ abs_data (HSI) │     │ abs_data (BA)  │  │
│  │ abs_data (CPI) │     │ abs_data (WPI) │     │ corelogic_     │  │
│  │ abs_data (EMP) │     └────────────────┘     │   scraper      │  │
│  └────────────────┘                            │ nab_scraper    │  │
│                                                └────────────────┘  │
│                               ▼                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              pipeline/normalize/engine.py                      │  │
│  │   INDICATOR_CONFIG + OPTIONAL_INDICATOR_CONFIG → status.json  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└──────────────────┬────────────────────────────────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────────────────────────────────┐
│                   data/ (Git-persisted CSVs)                        │
│                                                                     │
│  rba_cash_rate.csv          abs_cpi.csv                            │
│  abs_employment.csv         abs_household_spending.csv             │
│  abs_wage_price_index.csv   abs_building_approvals.csv             │
│  asx_futures.csv            [corelogic_housing.csv -- MISSING]     │
│                             [nab_capacity.csv -- MISSING]          │
└──────────────────┬────────────────────────────────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────────────────────────────────┐
│              public/data/status.json  (Frontend contract)           │
│   gauges: {inflation, wages, employment, spending,                 │
│            building_approvals, [housing], [business_confidence]}   │
│   asx_futures: {implied_rate, probabilities, next_meeting}        │
│   metadata: {indicators_available: N, indicators_missing: [...]}  │
└──────────────────┬────────────────────────────────────────────────┘
                   │
                   ▼
┌───────────────────────────────────────────────────────────────────┐
│              Netlify CDN → Browser (Plotly.js gauges)              │
└───────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities (Verified)

| Component | File | Responsibility | Contract |
|-----------|------|----------------|----------|
| Orchestrator | `pipeline/main.py` | Runs all scrapers in 3 tiers; calls `normalize/engine.py` in Phase 4 | Returns `{'status': 'success'/'partial'/'failed'}` |
| RBA Ingest | `pipeline/ingest/rba_data.py` | Downloads RBA cash rate CSV via readabs | Writes `data/rba_cash_rate.csv` |
| ABS Ingest | `pipeline/ingest/abs_data.py` | Queries ABS SDMX API for 5 indicators | Writes `data/abs_*.csv` |
| CoreLogic Ingest | `pipeline/ingest/corelogic_scraper.py` | **STUB** — scrapes free public housing data | Writes `data/corelogic_housing.csv`; returns status dict |
| NAB Ingest | `pipeline/ingest/nab_scraper.py` | **STUB** — fetches NAB survey PDF, extracts capacity utilisation | Writes `data/nab_capacity.csv`; returns status dict |
| ASX Ingest | `pipeline/ingest/asx_futures_scraper.py` | **PARTIALLY WORKING** — hits MarkitDigital API; endpoint may need update | Writes `data/asx_futures.csv`; returns status dict |
| Normalize | `pipeline/normalize/ratios.py` | Loads CSVs, computes YoY % change or direct, resamples to quarterly | Returns `pd.DataFrame` of `[date, value]` |
| Z-Score | `pipeline/normalize/zscore.py` | 10-year rolling robust Z-score (median/MAD) | Adds `z_score`, `window_size` columns |
| Gauge | `pipeline/normalize/gauge.py` | Maps Z-score to 0-100 scale, classifies zones, computes hawk score | Returns gauge dicts |
| Engine | `pipeline/normalize/engine.py` | Orchestrates normalize → zscore → gauge; builds and writes status.json | Writes `public/data/status.json` |
| CSV Handler | `pipeline/utils/csv_handler.py` | Append-with-dedup for per-source CSVs (keyed on `date` column) | Returns total row count |
| HTTP Client | `pipeline/utils/http_client.py` | Requests session with retry/backoff; browser UA for scraping | Returns `requests.Session` |
| Config | `pipeline/config.py` | All URLs, API keys, file paths, indicator configs | Imported by all modules |

---

## New Component Boundaries (v1.1)

### CoreLogic Scraper (`pipeline/ingest/corelogic_scraper.py`)

**What it must do:**
- Find a publicly accessible source of Australian dwelling price data
- Extract a single numeric value per reporting period (a price index or median, not nominal $)
- Write to `data/corelogic_housing.csv` with schema `[date, value]`

**Existing contract already satisfied:**
- `fetch_and_save()` function exists, returns `{'status': 'success'/'failed', ...}`
- `NEVER raises` — all exceptions caught, returns failed status dict
- Already registered as OPTIONAL in `pipeline/main.py` OPTIONAL_SOURCES list
- Already registered in `OPTIONAL_INDICATOR_CONFIG` with `normalize: 'yoy_pct_change'`
- Target CSV path: `data/corelogic_housing.csv`

**What is missing:** the actual data extraction logic inside `scrape_corelogic()`.

**Data source options (in priority order):**
1. CoreLogic media releases — monthly "Home Value Index" figure published in press releases on `corelogic.com.au/news-research`. HTML-parseable.
2. CoreLogic quarterly report PDFs — require pdfplumber. Higher maintenance.
3. ABS Residential Property Price Index (cat. 6416.0) via ABS SDMX API — structured API, most reliable, but is a lagged quarterly series not a CoreLogic-branded figure. Use as fallback or substitute.

**Normalization path:**
```
corelogic_housing.csv
    [date, value]  ← price index or median dwelling price
        ↓
normalize_indicator('housing', config)
    yoy_pct_change (12 monthly periods or 4 quarterly)
        ↓
compute_rolling_zscores()
        ↓
build_gauge_entry() → status.json gauges['housing']
```

**Key constraint:** The config sets `normalize: 'yoy_pct_change'`. The scraper must write raw index values (or raw median prices — YoY % change removes the nominal currency problem at the normalization layer). Raw values are fine.

---

### NAB Scraper (`pipeline/ingest/nab_scraper.py`)

**What it must do:**
- Locate the latest NAB Monthly Business Survey PDF from `business.nab.com.au`
- Extract the capacity utilisation figure (a percentage, typically 80-85%)
- Write to `data/nab_capacity.csv` with schema `[date, value]`

**Existing contract already satisfied:**
- `fetch_and_save()` function exists, returns status dict, never raises
- Already registered as OPTIONAL in `pipeline/main.py`
- Already registered in `OPTIONAL_INDICATOR_CONFIG` with `normalize: 'direct'` (capacity utilisation is already a ratio — no YoY needed)
- Target CSV path: `data/nab_capacity.csv`

**What is missing:** PDF download + text extraction inside `scrape_nab_survey()`.

**Implementation approach:**
```
GET business.nab.com.au/nab-monthly-business-survey page
    ↓
BeautifulSoup: find latest PDF link (href contains .pdf)
    ↓
GET the PDF URL → bytes
    ↓
pdfplumber.open(BytesIO(pdf_bytes))
    ↓
Search pages for "Capacity utilisation" row in tables or text
    Extract float value (e.g., 83.2)
    ↓
Build DataFrame: [date (survey month), value (capacity %)]
    ↓
append_to_csv(DATA_DIR / "nab_capacity.csv", df)
```

**New library dependency:** `pdfplumber` (or `pypdf2`). Recommend `pdfplumber` — it handles table extraction from PDFs better than `pypdf2`.

**Normalization path:**
```
nab_capacity.csv
    [date, value]  ← capacity utilisation % (e.g., 83.2)
        ↓
normalize_indicator('business_confidence', config)
    direct (no YoY — it's already an index/ratio)
        ↓
compute_rolling_zscores()
        ↓
build_gauge_entry() → status.json gauges['business_confidence']
```

**Key constraint:** `normalize: 'direct'` means the raw % value flows straight to Z-score. The CSV must contain the utilisation rate as a percentage float.

---

### ASX Futures Scraper (`pipeline/ingest/asx_futures_scraper.py`)

**What it must do:**
- Hit the MarkitDigital API (or a working replacement) to get IB futures settlement prices
- Derive implied cash rates and probabilities for upcoming RBA meetings
- Write to `data/asx_futures.csv` with schema `[date, meeting_date, implied_rate, change_bp, probability_cut, probability_hold, probability_hike]`

**Current status:**
- Implementation is complete and correct
- The MarkitDigital API URL in `config.py` (`ASX_FUTURES_URLS["ib_futures"]`) may be returning errors or stale data
- `data/asx_futures.csv` **already exists** with 40+ rows — so the API has worked at some point

**What the fix involves:**
- Verify the current endpoint responds correctly: `https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures?days=365&height=1&width=1`
- If endpoint has changed, find the replacement via the ASX website's network requests
- Update `ASX_FUTURES_URLS["ib_futures"]` in `config.py`

**Unique architectural consideration — ASX is a benchmark, not a gauge:**
The existing engine handles ASX specially. It does NOT go through `process_indicator()` → Z-score. Instead:

```python
# engine.py: build_asx_futures_entry() reads CSV directly
asx_entry = build_asx_futures_entry()
if asx_entry is not None:
    status['asx_futures'] = asx_entry  # top-level key, not in gauges{}
```

This means:
- ASX futures data bypasses the Z-score pipeline entirely
- It appears in `status.json` as `status['asx_futures']`, not `status['gauges']`
- It does NOT count toward the hawk score (excluded via `exclude_benchmark=True`)
- It does NOT count toward the "Based on N of 8 indicators" count

**Daily workflow** (`daily-asx-futures.yml`) runs the scraper then `engine.py` independently of the weekly pipeline. The fix must preserve this separate scheduling.

---

## Data Flow: Complete Picture

### Weekly Pipeline (Monday)

```
pipeline/main.py
    │
    ├── CRITICAL: rba_data.fetch_and_save()
    │       GET rba.gov.au CSV → data/rba_cash_rate.csv
    │
    ├── CRITICAL: abs_data.fetch_and_save('cpi')
    │       GET ABS SDMX API → data/abs_cpi.csv
    │
    ├── CRITICAL: abs_data.fetch_and_save('employment')
    │       GET ABS SDMX API → data/abs_employment.csv
    │
    ├── IMPORTANT: abs_data.fetch_and_save('household_spending')
    │       GET ABS SDMX API → data/abs_household_spending.csv
    │
    ├── IMPORTANT: abs_data.fetch_and_save('wage_price_index')
    │       GET ABS SDMX API → data/abs_wage_price_index.csv
    │
    ├── OPTIONAL: abs_data.fetch_and_save('building_approvals')
    │       GET ABS SDMX API → data/abs_building_approvals.csv
    │
    ├── OPTIONAL: corelogic_scraper.fetch_and_save()   ← FIX NEEDED
    │       Scrape CoreLogic public page → data/corelogic_housing.csv
    │
    ├── OPTIONAL: nab_scraper.fetch_and_save()          ← FIX NEEDED
    │       Scrape NAB → download PDF → pdfplumber → data/nab_capacity.csv
    │
    └── normalize/engine.generate_status()
            │
            ├── For each indicator in INDICATOR_CONFIG:
            │     normalize_indicator() → compute_rolling_zscores() → build_gauge_entry()
            │
            ├── For each indicator in OPTIONAL_INDICATOR_CONFIG:
            │     normalize_indicator() → [if CSV exists] → gauge entry
            │
            ├── build_asx_futures_entry()  ← reads asx_futures.csv directly
            │
            └── Write public/data/status.json
                    gauges: {inflation, wages, employment, spending,
                             building_approvals, housing?, business_confidence?}
                    asx_futures: {implied_rate, probabilities, ...}
                    metadata: {indicators_available: N}
```

### Daily ASX Pipeline (Weekdays)

```
pipeline/ingest/asx_futures_scraper.py
    GET MarkitDigital API → parse JSON → derive probabilities
    → data/asx_futures.csv (append + composite-key dedup)

pipeline/normalize/engine.generate_status()
    → reads asx_futures.csv (build_asx_futures_entry())
    → regenerates public/data/status.json with fresh ASX data
```

---

## Integration Points

### What Each New Scraper Plugs Into

| Integration Point | CoreLogic | NAB | ASX |
|-------------------|-----------|-----|-----|
| Orchestrator registration | Already in `OPTIONAL_SOURCES` | Already in `OPTIONAL_SOURCES` | Separate daily workflow |
| Config entry | `OPTIONAL_INDICATOR_CONFIG['housing']` (csv_file=None → fill in) | `OPTIONAL_INDICATOR_CONFIG['business_confidence']` (csv_file=None → fill in) | `OPTIONAL_INDICATOR_CONFIG['asx_futures']` (csv_file='asx_futures.csv' — done) |
| Output CSV | `data/corelogic_housing.csv` | `data/nab_capacity.csv` | `data/asx_futures.csv` (exists) |
| Normalization | `yoy_pct_change` (12 monthly) | `direct` | Special path: `build_asx_futures_entry()` |
| Status.json key | `gauges['housing']` | `gauges['business_confidence']` | `asx_futures` (top-level) |
| Hawk score contribution | Yes (weighted) | Yes (weighted) | No (benchmark excluded) |

**One activation step for CoreLogic and NAB:** When the scrapers produce data, update `OPTIONAL_INDICATOR_CONFIG` in `config.py` to set `csv_file` from `None` to the actual filename. The normalization engine already checks for `csv_file is None` and skips gracefully.

```python
# config.py — change after scraper works
OPTIONAL_INDICATOR_CONFIG = {
    "housing": {
        "csv_file": "corelogic_housing.csv",  # was None
        ...
    },
    "business_confidence": {
        "csv_file": "nab_capacity.csv",        # was None
        ...
    },
}
```

### External Service Integration Points

| Source | Integration Method | Auth | Rate Limit Risk |
|--------|-------------------|------|-----------------|
| CoreLogic media page | HTTP GET + BeautifulSoup | None (public) | LOW — weekly cadence |
| ABS RPPI (fallback) | ABS SDMX API | None (public) | LOW — established API |
| NAB website | HTTP GET (link discovery) | None (public) | LOW — weekly cadence |
| NAB PDF | HTTP GET (PDF download) | None (public) | LOW — direct file |
| ASX MarkitDigital API | HTTP GET + JSON parse | None (currently) | MEDIUM — may add CORS/referrer checks |

---

## Recommended Build Order

Dependencies determine ordering. CoreLogic and NAB are fully independent of
each other. ASX is already partially working. The suggested sequence:

### Step 1: ASX Endpoint Fix (Day 1)

**Why first:** Quickest win. The scraper logic is complete. Only the endpoint
URL may need updating. Can verify in 30 minutes via manual `curl` or running
`python -m pipeline.ingest.asx_futures_scraper`. Unblocks daily refresh
accuracy. No new dependencies.

**Verification:** `data/asx_futures.csv` gets new rows with today's date.
`status.json` contains `asx_futures` key with `staleness_days: 0`.

### Step 2: CoreLogic (Days 2-3)

**Why second:** Source discovery is the uncertain part (website structure,
available public data). BeautifulSoup approach is the same pattern already
used in the codebase. No new dependencies beyond what's installed.

**If CoreLogic public page is paywalled or unreliable:** Switch to ABS RPPI
via the ABS SDMX API using the same `abs_data.py` pattern. The ABS approach
is more reliable but returns quarterly data vs CoreLogic's monthly.

**Verification:** `data/corelogic_housing.csv` exists with rows. Engine run
shows `housing` in `gauges` key of `status.json`. `indicators_available`
increments from 5 to 6.

### Step 3: NAB PDF Parsing (Days 4-6)

**Why last:** Highest complexity. Requires `pdfplumber` (new dependency). PDF
structure may vary between survey months. Text extraction for a specific
figure requires careful regex or table parsing. Budget 2-3 days for extraction
logic and testing against multiple historical PDFs.

**New dependency:** `pdfplumber` must be added to `requirements.txt`.

**Verification:** `data/nab_capacity.csv` exists with rows. Value is in range
75-90 (capacity utilisation %). `indicators_available` increments to 7 or 8.

---

## Architectural Patterns to Follow

### Pattern 1: Status Dict Return (Existing — Must Follow)

All optional scrapers return a status dict, never raise. This is enforced by
the orchestrator's OPTIONAL_SOURCES tier handling.

```python
def fetch_and_save() -> Dict[str, Union[str, int]]:
    try:
        df = scrape_source()
        if df.empty:
            return {'status': 'failed', 'error': 'No data extracted'}
        row_count = append_to_csv(output_path, df, date_column='date')
        return {'status': 'success', 'rows': row_count}
    except Exception as e:
        logger.warning(f"Scraper failed (optional source): {e}")
        return {'status': 'failed', 'error': str(e)}
```

### Pattern 2: Standard CSV Schema (Existing — Must Follow)

All indicator CSVs (except `asx_futures.csv`) use the same two-column schema.
The normalization engine's `load_indicator_csv()` expects this exactly.

```
date,value
2024-01-31,142.3
2024-04-30,145.1
```

The `date` column is deduplicated by `csv_handler.append_to_csv()`. Dates
should be the last day of the reporting period (month-end or quarter-end).

### Pattern 3: ASX Multi-Column Schema (Existing — Different from others)

ASX futures uses a bespoke schema because it stores per-meeting probabilities.
The normalization engine has a dedicated `load_asx_futures_csv()` function.
Do not change this schema.

```
date,meeting_date,implied_rate,change_bp,probability_cut,probability_hold,probability_hike
2026-02-24,2026-04-01,3.82,-3.0,12,88,0
```

Deduplication uses composite key `[date, meeting_date]` (in `asx_futures_scraper.py`,
not via `csv_handler`).

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Raising from Optional Scrapers

**What:** Letting `scrape_corelogic()` or `scrape_nab_survey()` propagate
exceptions without catching in `fetch_and_save()`.

**Why bad:** The orchestrator's OPTIONAL tier catches exceptions, but an
uncaught exception in `fetch_and_save()` marks the source as failed with a
Python traceback rather than a clean status dict. The outer try-except in
`main.py` handles this, but it's cleaner to catch inside `fetch_and_save()`.

**Do this instead:** The existing stub already has the outer try-except in
`fetch_and_save()`. Keep it. Let `scrape_*()` raise freely; `fetch_and_save()`
catches and returns a status dict.

### Anti-Pattern 2: Nominal Currency Values in CSV

**What:** Storing raw median dwelling prices in dollars (e.g., `value: 850000`)
without flagging the unit.

**Why bad:** The config specifies `normalize: 'yoy_pct_change'` for housing,
which means YoY % change is computed in the normalization layer. Raw nominal
values are fine as long as the series is internally consistent. BUT: if the
source ever changes its methodology (e.g., switches from median to mean), the
historical YoY comparisons break silently.

**Do this instead:** Prefer a price index (where 2020=100) over nominal medians
when available. If using nominal, document the unit in the scraper and note
the source methodology.

### Anti-Pattern 3: Hardcoding PDF Page Numbers

**What:** `pdfplumber.pages[3]` to extract the capacity utilisation table from
the NAB PDF.

**Why bad:** NAB can and does vary the report layout between months. Page 3 in
January may be page 4 in June after a methodology update.

**Do this instead:** Search all pages for the section header "Capacity
utilisation" and extract from that section. Use regex on the full text, or
iterate pages until the pattern matches.

### Anti-Pattern 4: Changing the ASX CSV Schema

**What:** Adding columns or renaming fields in `asx_futures.csv`.

**Why bad:** `build_asx_futures_entry()` in the engine reads specific column
names by position. The daily workflow commits this CSV. Changing the schema
creates incompatibility with historical rows already in the CSV.

**Do this instead:** If additional ASX data is needed, add new columns and
handle them as optional with `.get()` calls in the engine. Never remove or
rename existing columns.

---

## Scalability Considerations

This architecture is not bandwidth or compute constrained at any realistic
traffic level — the bottleneck is GitHub Actions free tier minutes (2,000/month)
and external scraping reliability.

| Concern | Current State | v1.1 Change |
|---------|--------------|-------------|
| GitHub Actions minutes | ~4 min/week pipeline + 1 min/day ASX | +1-2 min/week for PDF download |
| CSV file sizes | <10KB each | Quarterly NAB data: tiny |
| Scraping brittleness | ABS/RBA: official APIs (stable) | CoreLogic: HTML scraping (fragile), NAB: PDF layout (fragile) |
| Maintenance burden | Near-zero for API sources | CoreLogic/NAB need monitoring for source changes |

The only meaningful scalability concern is **scraper maintenance**, not compute
or data volume.

---

## Sources

All findings verified directly against the codebase at
`/Users/annon/projects/rba-hawko-meter/`:

- `pipeline/main.py` — orchestrator tier structure, OPTIONAL_SOURCES list
- `pipeline/config.py` — OPTIONAL_INDICATOR_CONFIG stubs, ASX_FUTURES_URLS
- `pipeline/ingest/corelogic_scraper.py` — stub implementation, contracts
- `pipeline/ingest/nab_scraper.py` — stub implementation, PDF notes
- `pipeline/ingest/asx_futures_scraper.py` — working implementation, CSV schema
- `pipeline/normalize/engine.py` — ASX special path, gauges construction
- `pipeline/normalize/ratios.py` — normalize_indicator(), load_asx_futures_csv()
- `pipeline/utils/csv_handler.py` — append_to_csv(), dedup logic
- `.github/workflows/daily-asx-futures.yml` — separate ASX scheduling
- `.github/workflows/weekly-pipeline.yml` — main pipeline trigger

---

*Architecture research for: RBA Hawk-O-Meter v1.1 Scraper Integration*
*Researched: 2026-02-24*
