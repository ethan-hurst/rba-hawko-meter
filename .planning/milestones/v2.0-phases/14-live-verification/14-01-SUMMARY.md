---
phase: 14-live-verification
plan: 01
subsystem: testing
tags: [pytest, live-tests, verification, ascii-table, npm-scripts]

requires:
  - phase: 11-test-foundation
    provides: conftest.py autouse fixtures (isolate_data_dir, block_network, @pytest.mark.live exemption)
provides:
  - 9 @pytest.mark.live test functions covering all data sources
  - scripts/verify_summary.py ASCII summary table for pipeline output
  - npm run test:python:live and npm run verify scripts
affects: [15-pre-push-hook]

tech-stack:
  added: []
  patterns:
    - "Live test pattern: try fetch_and_save() -> structural assert on success -> warnings.warn() on failure/stale"
    - "Verify summary: read status.json -> ASCII box-drawing table with exit code signalling"

key-files:
  created:
    - tests/python/test_live_sources.py
    - scripts/verify_summary.py
  modified:
    - package.json

key-decisions:
  - "warnings.warn(UserWarning) for endpoint unavailability — not pytest.warns() — so tests pass whether endpoint is up or down"
  - "Shared _run_abs_test() helper for 5 ABS tests to avoid code duplication while keeping each test function distinct"
  - "Staleness threshold 90 days — warns but does not fail (data quality concern, not structural break)"
  - "verify script checks only 7 gauge keys + hawk_score range — full JSON schema validation owned by test_schema.py"

patterns-established:
  - "Live test pattern: structural assertions = hard fail, data quality/availability = UserWarning"

requirements-completed: [LIVE-01, LIVE-02, LIVE-03, LIVE-04]

duration: 2 min
completed: 2026-02-25
---

# Phase 14 Plan 01: Live Verification Infrastructure Summary

**9 @pytest.mark.live test functions (5 ABS + RBA + ASX + Cotality + NAB) with graceful degradation, plus ASCII verify summary script and npm scripts**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-25T03:53:26Z
- **Completed:** 2026-02-25T03:56:19Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- 9 live test functions covering all data sources with structural validation on success and UserWarning on unavailability
- verify_summary.py reads status.json and prints ASCII table with PASS/WARN/FAIL per indicator and hawk_score
- npm scripts `test:python:live` and `verify` wired in package.json
- Unit test suite completely unaffected (118 pass, 10 deselected including 9 live + 1 smoke)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create live test file with 9 @pytest.mark.live test functions** - `32bcf60` (feat)
2. **Task 2: Create verify summary script and add npm scripts** - `f12e82c` (feat)

## Files Created/Modified
- `tests/python/test_live_sources.py` - 9 live test functions, one per data source
- `scripts/verify_summary.py` - ASCII summary table reader for status.json
- `package.json` - Added test:python:live and verify npm scripts

## Decisions Made
- Used `warnings.warn(UserWarning)` instead of `pytest.warns()` so tests pass regardless of endpoint status
- Shared `_run_abs_test()` helper for 5 ABS tests keeps code DRY while preserving individual test identity
- Staleness threshold set at 90 days (warn, not fail) — data quality concern, not structural break
- Verify script only checks 7 gauge keys + hawk_score range — full schema validation owned by test_schema.py

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 14 complete, live verification infrastructure ready
- Phase 15 (Pre-Push Hook) can now reference `npm run test:python:live` and `npm run verify` for the full quality gate

---
*Phase: 14-live-verification*
*Completed: 2026-02-25*
