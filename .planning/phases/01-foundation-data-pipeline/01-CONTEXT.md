# Phase 1: Foundation & Data Pipeline - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Automated Python ETL pipeline that ingests economic data from multiple sources via GitHub Actions and commits to git. Covers ingestion, storage, scheduling, and failure handling. Does NOT include normalization, Z-scores, or any frontend work.

</domain>

<decisions>
## Implementation Decisions

### Data Source Priority
- **Tiered system:** RBA/ABS sources are critical (pipeline fails if they fail). CoreLogic/NAB are optional (use stale data + log warning on failure)
- ABS data releases monthly/quarterly — carry forward most recent value, include `days_since_update` staleness field in metadata
- ASX Futures get a **separate daily GitHub Action** (most time-sensitive data). Scrape from ASX RBA Rate Tracker page
- All other sources run on the weekly Monday schedule

### CSV Schema Design
- **Per-source files** — separate CSV per data source (e.g., `data/rba_rates.csv`, `data/abs_cpi.csv`, `data/corelogic_housing.csv`)
- **Source release dates** as row timestamps (not pipeline run dates). Different sources have different row counts
- No concerns about git repo size — CSVs are small

### Failure Handling
- GitHub Action failure email (built-in) + status badge in README
- Optional sources have a **4-week grace period** before flagged as a problem
- Support **workflow_dispatch** for manual trigger outside weekly schedule

### Historical Backfill
- **Backfill at build time** — one-time script downloads 10 years of historical data from ABS/RBA via `readabs`
- CoreLogic/NAB: **manual seed files** — compile historical data from reports/archives and commit as seed CSVs
- Pipeline then appends new data incrementally going forward

### Claude's Discretion
- Exact CSV column naming conventions
- GitHub Action workflow structure and caching
- `readabs` API usage patterns
- Scraper implementation details (BeautifulSoup patterns)

</decisions>

<specifics>
## Specific Ideas

- Use `readabs` library for all ABS/RBA data — it's the verified reliable source
- "Git as Database" pattern — data versioned in the repo itself
- Daily ASX Futures scrape is separate from the weekly pipeline — two GitHub Action workflows

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation-data-pipeline*
*Context gathered: 2026-02-04*
