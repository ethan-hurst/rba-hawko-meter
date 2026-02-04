# Phase 1: Foundation & Data Pipeline - Research

**Researched:** 2026-02-04
**Domain:** Python ETL pipelines, Australian economic data sources, GitHub Actions automation
**Confidence:** MEDIUM (verified patterns, some library uncertainty)

## Summary

Phase 1 establishes an automated Python ETL pipeline that ingests Australian economic data from multiple sources (ABS, RBA, CoreLogic, NAB, ASX) via GitHub Actions and commits it to git as versioned CSV files. The research identified critical gaps in the assumed technology stack and validated alternative approaches.

**Critical Finding:** The user's CONTEXT.md specifies using the `readabs` library for ABS/RBA data. A Python package named `readabs` exists on PyPI (v0.1.8, Dec 2025), but documentation is sparse and the mature `readabs` library is actually an R package. Research recommends using direct ABS Data API (SDMX 2.1) and RBA CSV downloads via Python `requests` and `pandas` as the reliable approach.

**Primary recommendation:** Build scrapers using Python `requests` + `pandas` for all sources (ABS API, RBA CSV tables, CoreLogic/NAB web scraping, ASX futures). Use GitHub Actions with `stefanzweifel/git-auto-commit-action@v7` for automated commits. Implement tiered failure handling with graceful degradation for optional sources.

## Standard Stack

The established libraries/tools for Python ETL pipelines with GitHub Actions:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pandas | 2.x | DataFrame operations, CSV I/O | Industry standard for tabular data, excellent CSV handling with PyArrow backend |
| requests | 2.x | HTTP requests for APIs/scraping | De facto standard for Python HTTP, simple and reliable |
| beautifulsoup4 | 4.x | HTML parsing for web scraping | Most popular Python HTML parser, beginner-friendly, mature |
| lxml | 4.x | XML/HTML parser (BS4 backend) | Fastest parser for BeautifulSoup, handles malformed HTML |
| GitHub Actions | N/A | CI/CD scheduling & automation | Native GitHub integration, built-in GITHUB_TOKEN, no external services |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dateutil | 2.x | Date parsing & manipulation | Handling Australian date formats from scraped sources |
| pyarrow | 14.x+ | Fast CSV I/O, columnar operations | Faster CSV reading (30-50% memory reduction), use as pandas backend |
| Great Expectations | 0.18.x | Data validation framework | Production pipelines needing comprehensive validation (consider for future phases) |
| pydantic | 2.x | Data validation via Python types | Lightweight validation for API responses and CSV schemas |

### GitHub Actions
| Action | Version | Purpose | Why Standard |
|--------|---------|---------|--------------|
| actions/checkout | v6 | Clone repository | Required for all workflows, v6 is latest |
| actions/setup-python | v6 | Install Python, cache deps | Built-in pip caching, supports Python 3.11+ |
| stefanzweifel/git-auto-commit-action | v7 | Commit & push data files | Most popular auto-commit action (6k+ stars), handles edge cases |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| requests + BS4 | Scrapy | Scrapy adds complexity (async, crawling framework) but offers better rate limiting and retry logic. Not needed for 4-5 simple sources. |
| Direct API/CSV | readabs Python | readabs Python (PyPI) exists but is poorly documented. R version is mature but requires R runtime. Direct API access is more transparent. |
| git-auto-commit-action | ad-m/github-push-action | ad-m requires manual git config, less ergonomic. git-auto-commit-action handles edge cases better. |

**Installation:**
```bash
pip install pandas requests beautifulsoup4 lxml python-dateutil pyarrow
```

## Architecture Patterns

### Recommended Project Structure
```
rba-hawko-meter/
├── .github/
│   └── workflows/
│       ├── weekly-pipeline.yml      # Weekly Monday run for most sources
│       └── daily-asx-futures.yml    # Daily ASX futures scraper
├── pipeline/
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── abs_data.py              # ABS Data API client
│   │   ├── rba_data.py              # RBA table downloader
│   │   ├── corelogic_scraper.py    # CoreLogic web scraper
│   │   ├── nab_scraper.py          # NAB survey scraper
│   │   └── asx_futures_scraper.py  # ASX RBA Rate Tracker scraper
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── csv_handler.py          # CSV append/merge logic
│   │   └── validation.py           # Data quality checks
│   ├── config.py                    # Source configs, timeouts, URLs
│   └── main.py                      # Orchestration script
├── data/
│   ├── rba_cash_rate.csv           # Per-source CSV files
│   ├── abs_cpi.csv
│   ├── abs_employment.csv
│   ├── abs_wage_price_index.csv
│   ├── abs_building_approvals.csv
│   ├── corelogic_housing.csv
│   ├── nab_capacity.csv
│   └── asx_futures.csv
├── scripts/
│   └── backfill_historical.py      # One-time historical data download
└── requirements.txt
```

### Pattern 1: Tiered Source Priority
**What:** Critical sources (RBA/ABS) must succeed or pipeline fails. Optional sources (CoreLogic/NAB) degrade gracefully with stale data + warnings.

**When to use:** Multiple data sources with different reliability/importance levels.

**Example:**
```python
# pipeline/main.py
import sys
from ingest import abs_data, rba_data, corelogic_scraper, nab_scraper

CRITICAL_SOURCES = [abs_data, rba_data]
OPTIONAL_SOURCES = [corelogic_scraper, nab_scraper]

def run_pipeline():
    failures = []

    # Critical sources - fail fast
    for source in CRITICAL_SOURCES:
        try:
            source.fetch_and_save()
        except Exception as e:
            print(f"CRITICAL: {source.__name__} failed: {e}")
            sys.exit(1)

    # Optional sources - log and continue
    for source in OPTIONAL_SOURCES:
        try:
            source.fetch_and_save()
        except Exception as e:
            print(f"WARNING: {source.__name__} failed: {e}")
            failures.append(source.__name__)

    if failures:
        print(f"Pipeline completed with {len(failures)} optional source failures")

    return 0 if not failures else 2  # Exit code 2 = partial success
```

### Pattern 2: Incremental CSV Append
**What:** Load existing CSV, append new rows based on timestamp, deduplicate on source release date.

**When to use:** Time-series data updated incrementally (not full refresh).

**Example:**
```python
# pipeline/utils/csv_handler.py
import pandas as pd
from pathlib import Path

def append_to_csv(file_path: str, new_data: pd.DataFrame, date_column: str = 'date'):
    """Append new data to existing CSV, deduplicating on date_column."""
    file_path = Path(file_path)

    if file_path.exists():
        existing = pd.read_csv(file_path, parse_dates=[date_column])
        combined = pd.concat([existing, new_data], ignore_index=True)
        # Keep most recent value for duplicate dates
        combined = combined.sort_values(date_column).drop_duplicates(
            subset=[date_column], keep='last'
        )
    else:
        combined = new_data

    combined = combined.sort_values(date_column)
    combined.to_csv(file_path, index=False, date_format='%Y-%m-%d')
    print(f"Written {len(combined)} rows to {file_path}")
```

### Pattern 3: ABS Data API Integration
**What:** ABS provides SDMX 2.1 compliant Data API returning CSV/JSON/XML. Use direct HTTP requests rather than undocumented readabs Python package.

**When to use:** All ABS data (CPI, employment, wage price index, building approvals).

**Example:**
```python
# pipeline/ingest/abs_data.py
import requests
import pandas as pd
from io import StringIO

ABS_API_BASE = "https://data.api.abs.gov.au/data"

def fetch_abs_series(dataflow_id: str, series_filters: dict) -> pd.DataFrame:
    """
    Fetch ABS data via SDMX Data API.

    Args:
        dataflow_id: ABS dataflow identifier (e.g., 'CPI')
        series_filters: SDMX dimension filters

    Returns:
        DataFrame with date and value columns
    """
    # Build SDMX query URL
    filter_str = '.'.join(series_filters.values())
    url = f"{ABS_API_BASE}/{dataflow_id}/{filter_str}"

    headers = {
        'Accept': 'application/vnd.sdmx.data+csv;labels=both',
        'User-Agent': 'RBA-Hawko-Meter/1.0 (Data Pipeline)'
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))
    # Transform to standard format: date, value, metadata
    df = df.rename(columns={'TIME_PERIOD': 'date', 'OBS_VALUE': 'value'})
    df['date'] = pd.to_datetime(df['date'])

    return df[['date', 'value']]

# Example usage for CPI
def fetch_cpi():
    return fetch_abs_series(
        dataflow_id='CPI',
        series_filters={'MEASURE': 'INDEX', 'INDEX': '10001', 'TSEST': '10'}
    )
```

### Pattern 4: GitHub Actions Scheduled Workflow
**What:** Use cron schedule for weekly runs, workflow_dispatch for manual triggers, built-in caching for Python dependencies.

**When to use:** All automated data pipelines.

**Example:**
```yaml
# .github/workflows/weekly-pipeline.yml
name: Weekly Data Pipeline

on:
  schedule:
    - cron: '0 2 * * 1'  # 2 AM UTC Monday (avoid hourly peaks)
  workflow_dispatch:      # Manual trigger support

permissions:
  contents: write         # Required for git-auto-commit-action

jobs:
  ingest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: actions/setup-python@v6
        with:
          python-version: '3.11'
          cache: 'pip'  # Cache pip dependencies

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run pipeline
        run: python pipeline/main.py

      - uses: stefanzweifel/git-auto-commit-action@v7
        with:
          commit_message: 'data: weekly update ${{ github.run_number }}'
          file_pattern: 'data/*.csv'
          commit_user_name: 'github-actions[bot]'
          commit_user_email: 'github-actions[bot]@users.noreply.github.com'
```

### Anti-Patterns to Avoid

- **Using git-lfs for small CSVs:** CSVs in this project are small (<1MB even after years). git-lfs adds complexity for no benefit. Only consider if files exceed 10MB.
- **Hand-rolling retry logic:** Use `requests` with `urllib3.util.Retry` adapter instead of custom retry loops.
- **Storing secrets in code:** Use GitHub Actions secrets for any future API keys. Never commit credentials.
- **Global error handlers that mask failures:** Let critical sources fail loudly. Only catch exceptions for optional sources.
- **Committing on every run with no changes:** git-auto-commit-action handles this automatically (checks dirty state).

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date parsing from strings | Custom regex/strptime | `python-dateutil.parser` | Handles dozens of formats, timezones, ambiguous dates |
| CSV append with deduplication | Manual row comparison | `pandas.drop_duplicates()` after concat | Optimized C implementation, handles edge cases (NaN, mixed types) |
| HTTP retries with backoff | Custom retry loops | `requests.adapters.HTTPAdapter` + `urllib3.util.Retry` | Handles transient failures, connection pooling, exponential backoff |
| User-Agent rotation | Manual header management | `requests.Session` with persistent headers | Maintains session state, cookie handling |
| Data validation schemas | Custom if/else checks | `pydantic` models or `Great Expectations` | Type checking, clear error messages, reusable schemas |
| Git commit automation in Actions | Manual git commands | `stefanzweifel/git-auto-commit-action@v7` | Handles detached HEAD, empty commits, branch conflicts |
| SDMX XML parsing | BeautifulSoup on SDMX XML | Request CSV format directly (`Accept: application/vnd.sdmx.data+csv`) | ABS API returns CSV, no XML parsing needed |

**Key insight:** Python's data engineering ecosystem is mature. The "standard library + pandas + requests + BeautifulSoup" stack handles 90% of ETL use cases. Resist adding orchestration frameworks (Airflow, Prefect) or validation frameworks (Great Expectations) until complexity justifies them.

## Common Pitfalls

### Pitfall 1: GitHub Actions Scheduled Workflows Don't Run
**What goes wrong:** Cron schedules are silently ignored or delayed by hours.

**Why it happens:**
- Workflow file not on default branch
- Repository inactive (60+ days in public repos disables schedules)
- High load at start of hour delays execution
- Invalid cron syntax (GitHub doesn't validate, just ignores)

**How to avoid:**
- Always merge workflow to default branch (main)
- Schedule at off-peak times (avoid :00, prefer :07 or :23)
- Use workflow_dispatch for manual testing
- Test cron syntax at crontab.guru before committing

**Warning signs:**
- Workflow shows in Actions tab but never runs
- Runs sporadically (high load issue)
- Works manually but not on schedule (branch/syntax issue)

### Pitfall 2: readabs Python Package is Not Well-Supported
**What goes wrong:** Documentation is sparse, no code examples, unclear API vs. R version.

**Why it happens:** The mature `readabs` library is an R package (MattCowgill/readabs on GitHub). A Python package exists on PyPI (v0.1.8) but appears to be a separate, less mature implementation.

**How to avoid:** Use direct API/CSV access instead:
- ABS: Use ABS Data API (SDMX 2.1) with `requests` - documented, official, returns CSV/JSON
- RBA: Download CSV tables directly from https://www.rba.gov.au/statistics/tables/

**Warning signs:**
- Import errors or missing functions from documentation
- Need to reference R documentation to understand Python package
- Package hasn't been updated in 6+ months

### Pitfall 3: Web Scraping Without User-Agent Gets Blocked
**What goes wrong:** Requests return 403 Forbidden or empty responses.

**Why it happens:** Default `requests` User-Agent is `python-requests/2.x`, which many sites block as a bot.

**How to avoid:**
- Always set realistic User-Agent header
- Use recent Chrome/Firefox UA strings (not old/rare browsers)
- Maintain session with `requests.Session()` for cookies

**Example:**
```python
headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
}
response = requests.get(url, headers=headers, timeout=30)
```

**Warning signs:**
- Works in browser but fails in script
- 403/418 HTTP status codes
- Empty HTML responses

### Pitfall 4: CSV Date Formats are Ambiguous
**What goes wrong:** 01/02/2025 is parsed as Feb 1 (US) instead of Jan 2 (Australian format).

**Why it happens:** pandas defaults to US date parsing (MM/DD/YYYY). Australian data sources use DD/MM/YYYY.

**How to avoid:**
- Store dates in ISO 8601 format (YYYY-MM-DD) in CSV files
- Use `pd.to_datetime(format='%d/%m/%Y', dayfirst=True)` when parsing Australian dates
- Always use `date_format='%Y-%m-%d'` in `df.to_csv()`

**Warning signs:**
- Dates in early months (01-12) look correct, later months (13+) throw errors
- Data from January appears in February column after processing

### Pitfall 5: GitHub Actions Auto-Commit Creates Infinite Loops
**What goes wrong:** Workflow triggers itself, creating endless commits.

**Why it happens:** By default, commits from `GITHUB_TOKEN` don't trigger workflows (safety feature). But if using PAT or on forks, can create loops.

**How to avoid:**
- Use built-in `GITHUB_TOKEN`, not Personal Access Token
- Add `[skip ci]` to commit message if needed
- Set `skip_checks: true` in git-auto-commit-action for forks

**Warning signs:**
- Workflow runs immediately after completing
- Commit history shows repeated "data update" commits seconds apart
- GitHub Actions usage quota depletes rapidly

### Pitfall 6: ABS Data Release Lag Not Accounted For
**What goes wrong:** Weekly pipeline runs Monday but ABS releases data on Tuesday, using previous week's stale data.

**Why it happens:** ABS releases are monthly/quarterly, not weekly. If data not yet released, pipeline gets previous value.

**How to avoid:**
- Add `days_since_update` metadata field to track staleness
- Implement "carry forward" logic: if new data not available, keep previous value
- Log staleness warnings when data is 30+ days old

**Example:**
```python
def add_staleness_metadata(df: pd.DataFrame, date_column: str = 'date') -> pd.DataFrame:
    latest_date = df[date_column].max()
    days_since = (pd.Timestamp.now() - latest_date).days
    df['days_since_update'] = days_since

    if days_since > 30:
        print(f"WARNING: Data is {days_since} days old")

    return df
```

**Warning signs:**
- Same value repeating across multiple weekly runs
- No new rows added despite pipeline "success"

### Pitfall 7: Optional Source Failures Silent After 4 Weeks
**What goes wrong:** CoreLogic/NAB scrapers fail, but no alerts until 4-week grace period expires.

**Why it happens:** Design decision - optional sources allowed to be stale. Need monitoring to track grace period.

**How to avoid:**
- Track `last_successful_fetch` timestamp per source
- Alert if approaching 4-week limit (e.g., day 25 warning)
- Include staleness in README status badge or dashboard metadata

**Warning signs:**
- Data hasn't updated in 3+ weeks
- No failed workflow notifications despite missing data

## Code Examples

Verified patterns from official sources and best practices:

### RBA Table Download (Direct CSV)
```python
# pipeline/ingest/rba_data.py
import requests
import pandas as pd
from io import StringIO

RBA_TABLES_BASE = "https://www.rba.gov.au/statistics/tables/csv"

def fetch_rba_table(table_id: str) -> pd.DataFrame:
    """
    Download RBA statistical table as CSV.

    Args:
        table_id: RBA table identifier (e.g., 'a2' for cash rate)

    Returns:
        DataFrame with standardized columns
    """
    url = f"{RBA_TABLES_BASE}/{table_id}.csv"

    headers = {
        'User-Agent': 'RBA-Hawko-Meter/1.0 (Data Pipeline)'
    }

    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    # RBA CSVs have metadata in first rows, skip them
    df = pd.read_csv(StringIO(response.text), skiprows=10)

    # Clean and standardize
    df = df.dropna(how='all')  # Remove empty rows
    df.columns = df.columns.str.lower().str.strip()

    return df

def fetch_cash_rate():
    """Fetch RBA cash rate target from Table A2."""
    df = fetch_rba_table('a2')
    df = df.rename(columns={'date': 'date', 'cash rate target': 'value'})
    df['date'] = pd.to_datetime(df['date'], format='%d-%b-%Y')
    return df[['date', 'value']]
```

### Web Scraping with Error Handling
```python
# pipeline/ingest/asx_futures_scraper.py
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

ASX_RATE_TRACKER_URL = "https://www.asx.com.au/markets/trade-our-derivatives-market/futures-market/rba-rate-tracker"

def scrape_asx_futures() -> pd.DataFrame:
    """
    Scrape ASX RBA Rate Tracker for futures-implied rate expectations.

    Returns:
        DataFrame with date, meeting_date, implied_rate columns
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    response = requests.get(ASX_RATE_TRACKER_URL, headers=headers, timeout=30)
    response.raise_for_status()

    soup = BeautifulSoup(response.content, 'lxml')

    # Example: Find table with rate expectations
    table = soup.find('table', {'class': 'rate-tracker'})

    if not table:
        raise ValueError("Could not find rate tracker table on page")

    rows = []
    for tr in table.find_all('tr')[1:]:  # Skip header
        cols = [td.text.strip() for td in tr.find_all('td')]
        if len(cols) >= 2:
            rows.append({
                'meeting_date': cols[0],
                'implied_rate': float(cols[1].rstrip('%'))
            })

    df = pd.DataFrame(rows)
    df['scrape_date'] = datetime.now().date()
    df['meeting_date'] = pd.to_datetime(df['meeting_date'], format='%d %b %Y')

    return df
```

### HTTP Retry Adapter
```python
# pipeline/utils/http_client.py
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def create_retry_session(
    retries=3,
    backoff_factor=0.5,
    status_forcelist=(500, 502, 503, 504)
) -> requests.Session:
    """
    Create requests session with automatic retry logic.

    Args:
        retries: Number of retry attempts
        backoff_factor: Backoff multiplier (0.5 = 0.5s, 1s, 2s delays)
        status_forcelist: HTTP codes to retry

    Returns:
        Configured requests.Session
    """
    session = requests.Session()

    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST"]
    )

    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session

# Usage
session = create_retry_session()
response = session.get("https://api.example.com/data", timeout=30)
```

### Validation with Pydantic
```python
# pipeline/utils/validation.py
from pydantic import BaseModel, Field, field_validator
from datetime import date
from typing import Optional

class EconomicDataPoint(BaseModel):
    """Schema for economic indicator data point."""
    date: date
    value: float = Field(gt=0)  # Must be positive
    days_since_update: Optional[int] = Field(default=None, ge=0)
    source: str

    @field_validator('days_since_update')
    @classmethod
    def warn_stale_data(cls, v: Optional[int]) -> Optional[int]:
        if v and v > 30:
            print(f"WARNING: Data is {v} days old")
        return v

# Usage
data_point = EconomicDataPoint(
    date=date(2026, 2, 4),
    value=4.35,
    days_since_update=5,
    source="RBA"
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Git-based data with custom commit scripts | GitHub Actions with git-auto-commit-action@v7 | 2023-2024 | Handles edge cases (detached HEAD, empty commits, branch sync) automatically |
| Separate file for each date | Single CSV per source, incremental append | 2020s standard | Simpler structure, easier querying, smaller repo size |
| pandas with NumPy backend | pandas with PyArrow backend | pandas 2.0 (2023) | 30-50% memory reduction, faster I/O, better type handling |
| Monolithic ETL script | Modular per-source ingest modules | Modern pattern | Easier testing, independent source failures, clearer code |
| XML/JSON responses from ABS | Direct CSV via SDMX API | ABS API evolution | Simpler parsing, no XML libraries needed |
| Manual workflow triggers | Scheduled cron + workflow_dispatch | GitHub Actions maturity | Automation with manual override for debugging |

**Deprecated/outdated:**
- **pandas.DataFrame.append()**: Deprecated in pandas 1.4+, use `pd.concat()` instead
- **GitHub Actions v2/v3**: Use v6 of actions/checkout and actions/setup-python for latest features
- **setup-python without cache**: v4+ supports built-in pip caching, no need for actions/cache

## Open Questions

Things that couldn't be fully resolved:

1. **readabs Python Package Reliability**
   - What we know: Package exists on PyPI (v0.1.8, Dec 2025), minimal documentation
   - What's unclear: API compatibility with R version, maintenance status, reliability
   - Recommendation: Start with direct ABS Data API and RBA CSV downloads. Evaluate readabs Python in future phase if it gains maturity/documentation.

2. **CoreLogic and NAB Data Access**
   - What we know: No public APIs, data published in monthly reports (PDFs/web pages)
   - What's unclear: Exact URLs for latest data, page structure stability, scraping legal terms
   - Recommendation: Implement scrapers targeting known report URLs. Build brittle-detection (schema validation) to catch page structure changes. Review ToS for scraping restrictions.

3. **Historical Data Availability**
   - What we know: ABS/RBA have 10+ years via API/tables. CoreLogic/NAB require manual compilation.
   - What's unclear: How far back CoreLogic/NAB data can be compiled from archives
   - Recommendation: Implement ABS/RBA 10-year backfill first. For CoreLogic/NAB, manually compile whatever historical data is accessible (even if incomplete), commit as seed CSVs.

4. **ASX Futures Page Structure**
   - What we know: Page exists at asx.com.au, shows rate tracker data
   - What's unclear: Exact table structure, JavaScript rendering requirements, update frequency
   - Recommendation: Inspect page during implementation. May require selenium if JavaScript-rendered. Consider fallback to third-party sources (e.g., investing.com) if ASX page is unstable.

5. **GitHub Actions Reliability for Daily Runs**
   - What we know: Scheduled workflows can have delays (especially on the hour), 60-day inactivity disables them
   - What's unclear: How reliable daily ASX futures scraper will be in practice
   - Recommendation: Schedule ASX workflow at off-peak time (:07 or :23 past hour). Monitor for missed runs. Consider workflow_dispatch fallback if unreliable.

## Sources

### Primary (HIGH confidence)
- [GitHub Actions Workflow Syntax](https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions) - Official documentation for scheduled workflows and workflow_dispatch
- [ABS Data API User Guide](https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis/data-api-user-guide) - Official ABS API documentation (SDMX 2.1, CSV format)
- [stefanzweifel/git-auto-commit-action](https://github.com/stefanzweifel/git-auto-commit-action) - v7 documentation and configuration
- [actions/setup-python](https://github.com/actions/setup-python) - Built-in dependency caching for pip

### Secondary (MEDIUM confidence)
- [readabs PyPI](https://pypi.org/project/readabs/) - Python package (v0.1.8, Dec 2025), sparse documentation
- [RBA Statistical Tables](https://www.rba.gov.au/statistics/tables/) - Direct CSV download source
- [BeautifulSoup Web Scraping Patterns (2026)](https://realpython.com/beautiful-soup-web-scraper-python/) - Current best practices
- [Pandas CSV Append Best Practices (2026)](https://copyprogramming.com/howto/incremental-data-load-using-pandas) - Incremental loading patterns
- [GitHub Actions Scheduled Workflow Best Practices](https://jasonet.co/posts/scheduled-actions/) - Timing, pitfalls, gotchas
- [Python ETL Best Practices (2026)](https://www.integrate.io/blog/data-validation-etl/) - Data validation and error handling

### Tertiary (LOW confidence)
- [Matt Cowgill's cash-rate-scraper](https://github.com/MattCowgill/cash-rate-scraper) - R-based ASX scraper (reference for approach, not Python code)
- [NAB Monthly Business Survey](https://business.nab.com.au/nab-monthly-business-survey-april-2025) - Example survey report (structure may change)
- [ASX RBA Rate Tracker](https://www.asx.com.au/markets/trade-our-derivatives-market/futures-market/rba-rate-tracker) - Page exists but structure unverified

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pandas, requests, BeautifulSoup are industry standards with extensive documentation
- Architecture: MEDIUM - Patterns verified via official docs, but readabs Python package is uncertain
- Pitfalls: HIGH - GitHub Actions issues well-documented in community discussions, scraping pitfalls are universal

**Research date:** 2026-02-04
**Valid until:** 2026-04-04 (60 days - data engineering stack is stable, but verify GitHub Actions updates and ABS API changes)

**Key risks:**
1. readabs Python package may not work as expected - fallback to direct API/CSV access is required
2. Web scraping targets (CoreLogic, NAB, ASX) may change structure - need brittleness detection
3. GitHub Actions scheduled workflows can be unreliable - need monitoring and manual trigger fallback
