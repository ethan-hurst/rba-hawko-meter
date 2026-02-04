# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-04)

**Core value:** "Data, not opinion." Empowers laypeople to understand interest rate drivers without relying on media sensationalism or biased advice.
**Current focus:** Phase 1 - Foundation & Data Pipeline

## Current Position

Phase: 1 of 5 (Foundation & Data Pipeline)
Plan: 3 of 3 complete
Status: Phase complete ✓
Last activity: 2026-02-04 — Completed 01-03-PLAN.md (Pipeline Orchestration)

Progress: [███████░░░] 60% (3/5 plans complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: 4.8 minutes
- Total execution time: 0.24 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 3/3 | 14.5 min | 4.8 min |

**Recent Trend:**
- Last 5 plans: 01-01 (8.5 min), 01-02 (3 min), 01-03 (3 min)
- Trend: Consistent velocity (3 min for last 2 plans)

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Netlify Hosting**: User preference for existing workflow/infrastructure
- **Serverless/Static**: Minimizes cost and complexity (Netlify + JSON flat files)
- **Z-Score Algorithm**: Normalizes diverse metrics into single 0-100 scale
- **Scraping**: Official APIs don't cover all leading indicators (accepted maintenance burden)
- **No Framework**: React/Vue is overkill for single-page dashboard (Vanilla JS + Tailwind + Plotly)
- **ABS API Wildcard Approach** (01-01): Use "all" queries with filters for maintainability
- **CSV Storage** (01-01): Per-source CSV files in data/ directory for simplicity
- **Building Approvals Deferred** (01-01): Dataflow not in ABS API, needs investigation
- **Graceful Degradation for Optional Sources** (01-02): CoreLogic/NAB scrapers never crash, return status dicts
- **Scraper Diagnostics Pattern** (01-02): JS-rendering detection, validation checks for brittleness
- **BROWSER_USER_AGENT** (01-02): Realistic Chrome UA in config for web scraping
- **Tiered Failure Handling with Exit Codes** (01-03): 0=success, 1=critical failure, 2=partial success for nuanced monitoring
- **Off-Peak Cron Scheduling** (01-03): Use :07 and :23 minutes to avoid GitHub Actions load spikes
- **Manual Seed Files for CoreLogic/NAB Historical** (01-03): PDF-based data requires manual backfill from archived reports

### Pending Todos

None yet.

### Blockers/Concerns

- **Building Approvals data source**: ABS Data API "BA" dataflow not found. Need to investigate alternate dataflow name or use different source (e.g., web scraping from ABS website).
- **Web scraper maintenance burden** (01-02): CoreLogic, NAB, ASX scrapers have TODOs for actual implementation. May need PDF parsing, Selenium/Playwright for JS-rendered pages, or alternative data sources. Optional sources pattern means pipeline continues even if these fail.

## Session Continuity

Last session: 2026-02-04 08:39 UTC
Stopped at: Completed 01-03-PLAN.md — Pipeline Orchestration (Phase 1 complete)
Resume file: None
Next: Begin Phase 2 (Core Dashboard)
