# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-04)

**Core value:** "Data, not opinion." Empowers laypeople to understand interest rate drivers without relying on media sensationalism or biased advice.
**Current focus:** Phase 3 - Data Normalization & Z-Scores

## Current Position

Phase: 3 of 5 (Data Normalization & Z-Scores)
Plan: 2 of 2 complete
Status: Phase complete
Last activity: 2026-02-06 — Completed 03-02-PLAN.md (Status.json Generation & Pipeline Integration)

Progress: [██████████████░░░░░░] 70% (7/10 plans complete, excluding Phase 1 gap closure)

## Performance Metrics

**Velocity:**
- Total plans completed: 6
- Average duration: 3.9 minutes
- Total execution time: 0.39 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 4/5 | 18.4 min | 4.6 min |
| 03 | 2/2 | 6 min | 3.0 min |

**Recent Trend:**
- Last 5 plans: 01-03 (3 min), 01-04 (3.9 min), 03-01 (3 min), 03-02 (3 min)
- Trend: Consistent velocity (3 min per plan)

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
- **BA_GCCSA for Building Approvals** (01-04): Use BA_GCCSA dataflow (Greater Capital Cities) instead of missing "BA"
- **Building Approvals as Non-Critical** (01-04): Mark critical=False since it's a secondary indicator
- **Graceful Degradation for Optional Sources** (01-02): CoreLogic/NAB scrapers never crash, return status dicts
- **Scraper Diagnostics Pattern** (01-02): JS-rendering detection, validation checks for brittleness
- **BROWSER_USER_AGENT** (01-02): Realistic Chrome UA in config for web scraping
- **Tiered Failure Handling with Exit Codes** (01-03): 0=success, 1=critical failure, 2=partial success for nuanced monitoring
- **Off-Peak Cron Scheduling** (01-03): Use :07 and :23 minutes to avoid GitHub Actions load spikes
- **Manual Seed Files for CoreLogic/NAB Historical** (01-03): PDF-based data requires manual backfill from archived reports
- **numpy-only MAD calculation** (03-01): No scipy dependency for single function; np.median(|x - median|) * 1.4826
- **[-3,+3] clamp range** (03-01): Widened from original [-2,+2] per research (reduces clipping 4.6% -> 0.3%)
- **ASX futures excluded from hawk score** (03-01): Displayed as benchmark, excluded via exclude_benchmark parameter
- **Guarded normalization import** (03-02): NORMALIZATION_AVAILABLE flag prevents pipeline crash if module broken
- **Non-fatal normalization** (03-02): Normalization failure does not change pipeline exit code

### Pending Todos

None yet.

### Blockers/Concerns

- **Building Approvals data source** (RESOLVED 01-04): ABS Data API "BA" dataflow not found — resolved by using BA_GCCSA dataflow. Building approvals now implemented with 144 rows of historical data.
- **Web scraper maintenance burden** (01-02): CoreLogic, NAB, ASX scrapers have TODOs for actual implementation. May need PDF parsing, Selenium/Playwright for JS-rendered pages, or alternative data sources. Optional sources pattern means pipeline continues even if these fail.
- **Mixed ABS series data** (03-02): Employment and retail trade CSVs contain multiple ABS series mixed together (wildcard queries). Produces invalid YoY% values. Need ABS filter refinement in Phase 1 gap closure.

## Session Continuity

Last session: 2026-02-06 05:46 UTC
Stopped at: Completed 03-02-PLAN.md — Status.json Generation & Pipeline Integration
Resume file: None
Next: Phase 3 complete. Phase 4 (Hawk-O-Meter Gauges) requires Phase 2 completion first.
