# Phase 14: Live Verification - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

On-demand end-to-end verification that the full data pipeline works against real external endpoints (ABS, RBA, ASX, Cotality, NAB). Developer can run live tests and a full pipeline verification without touching the unit test suite. External service unavailability is handled gracefully with warnings, not failures.

</domain>

<decisions>
## Implementation Decisions

### Test depth per endpoint
- Full depth for ALL sources (APIs and scrapers alike): connectivity, response structure, and data quality checks
- One test function per source (7 separate tests) — easy to see which specific source failed
- Structural failures (missing columns, changed API shape) = hard test failure
- Data quality issues (stale data, empty values) = pytest warning, not failure
- All live tests marked with `@pytest.mark.live` (existing tier system from Phase 11)

### Warning & output format
- Use `pytest.warns` with details: URL, HTTP status code, and reason for the warning
- Summary table after `npm run verify`: ASCII table in terminal showing each indicator, status (PASS/WARN/FAIL), and latest data date
- Table includes hawk_score and overall result line (e.g., "PASS (1 warning)")

### Pipeline verification isolation
- Individual live pytest tests use temp directories (same isolation as unit tests)
- `npm run verify` writes to real `data/` and `public/data/` directories (production paths)
- `npm run verify` runs a single `python pipeline/main.py` invocation — tests the real orchestrator path
- After pipeline completes, verify reads `status.json` and prints the ASCII summary table

### Verification reporting
- ASCII table format with box-drawing characters, showing:
  - Header: "RBA Hawk-O-Meter — Live Verification"
  - Columns: Indicator, Status, Latest
  - Footer: Hawk Score and Result line
- Don't re-validate status.json schema (unit tests cover that) — just check file exists with 7 indicator keys
- Pass/fail + data freshness per indicator in the summary

### Claude's Discretion
- Whether live tests call pipeline functions directly or make independent HTTP requests (pick per source based on what's practical)
- Per-test timeout strategy for slow endpoints
- Success output verbosity for individual live tests
- Whether `npm run verify` auto-commits updated data or leaves unstaged
- Exit code semantics for `npm run verify` (0 on warnings vs only on full pass)
- Implementation approach for the summary table generator (Python script vs npm orchestration)
- Whether to also log verify output to a file

</decisions>

<specifics>
## Specific Ideas

- ASCII summary table style modeled on the preview shown during discussion:
  ```
  ────────────────────────────────────────────────
    RBA Hawk-O-Meter — Live Verification
  ────────────────────────────────────────────────
   Indicator        Status  Latest
  ────────────────────────────────────────────────
   ABS CPI          PASS    Jan 2026
   ...
  ────────────────────────────────────────────────
   Hawk Score: 62 / 100
   Result: PASS (1 warning)
  ────────────────────────────────────────────────
  ```
- `npm run test:python:live` for per-source live tests (pytest with `-m live`)
- `npm run verify` for full pipeline run + summary table

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 14-live-verification*
*Context gathered: 2026-02-25*
