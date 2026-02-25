---
phase: 13-linting-baseline
plan: 01
subsystem: testing
tags: [ruff, python, linting, E501, B904]

# Dependency graph
requires:
  - phase: 11-test-foundation
    provides: pyproject.toml with ruff config (select E/F/W/B/I/UP, max-line-length 88)
provides:
  - Zero-violation Python codebase ready for pre-push hook gating
  - Baseline cleanup commit absorbing all pre-existing ruff violations
affects: [15-pre-push-hook]

# Tech tracking
tech-stack:
  added: []
  patterns: [max-line-length 88 across all Python files, no inline noqa suppressions]

key-files:
  created: []
  modified:
    - pipeline/config.py
    - pipeline/ingest/abs_data.py
    - pipeline/ingest/asx_futures_scraper.py
    - pipeline/ingest/corelogic_scraper.py
    - pipeline/ingest/nab_scraper.py
    - pipeline/ingest/rba_data.py
    - pipeline/main.py
    - pipeline/normalize/engine.py
    - pipeline/normalize/ratios.py
    - pipeline/normalize/zscore.py
    - pipeline/normalize/gauge.py
    - pipeline/utils/csv_handler.py
    - pipeline/utils/http_client.py
    - tests/python/conftest.py
    - tests/python/test_smoke.py
    - tests/python/test_zscore.py
    - tests/python/test_gauge.py
    - tests/python/test_ratios.py
    - tests/python/test_csv_handler.py
    - tests/python/test_schema.py

key-decisions:
  - "Auto-fix first (ruff --fix), then manual fixes for B904 and E501 that ruff cannot auto-fix"
  - "No noqa or type: ignore suppressions — all violations resolved by fixing the code"

patterns-established:
  - "Line wrapping: multi-line function signatures, string concatenation for long strings, extracted variables for complex expressions"
  - "B904 pattern: always use 'from e' in raise-from-except blocks"

requirements-completed: [LINT-01, LINT-02]

# Metrics
duration: 15min
completed: 2026-02-25
---

# Phase 13 Plan 01: Ruff Baseline Cleanup Summary

**145 Python violations fixed to zero across pipeline/ and tests/ — 46 auto-fixed, 1 B904, 87 E501 manual wraps, zero inline suppressions**

## Performance

- **Duration:** 15 min
- **Started:** 2026-02-25
- **Completed:** 2026-02-25
- **Tasks:** 3 (auto-fix, B904 manual fix, E501 manual wraps)
- **Files modified:** 20

## Accomplishments
- Auto-fixed 46 violations (unused imports, import sorting, UP007 type annotations)
- Fixed 1 B904 violation in abs_data.py (added `from e` clause to raise-in-except)
- Fixed 87 E501 line-too-long violations via multi-line wrapping across all Python files
- All 119 tests pass after cleanup
- Zero noqa/type:ignore suppressions

## Task Commits

1. **Ruff baseline cleanup** - `66c3c02` (style: auto-fix + manual B904 + E501)

## Files Created/Modified
- `pipeline/config.py` - Wrapped long strings and inline comments
- `pipeline/ingest/abs_data.py` - Multi-line signatures, from-e clause, wrapped FETCHERS
- `pipeline/ingest/asx_futures_scraper.py` - Multi-line signatures and logger calls
- `pipeline/ingest/corelogic_scraper.py` - Wrapped docstrings and logger calls
- `pipeline/ingest/nab_scraper.py` - Wrapped URL lambdas, comments, logger calls (14 fixes)
- `pipeline/ingest/rba_data.py` - Wrapped comment
- `pipeline/main.py` - Extracted variables, wrapped print/summary lines
- `pipeline/normalize/engine.py` - Wrapped comments and list concatenation
- `pipeline/normalize/ratios.py` - Wrapped method chains
- `pipeline/normalize/zscore.py` - Auto-fixed unused import and import sorting
- `pipeline/normalize/gauge.py` - Auto-fixed import sorting
- `pipeline/utils/csv_handler.py` - Auto-fixed UP007 type annotation
- `pipeline/utils/http_client.py` - Auto-fixed import sorting
- `tests/python/` (7 test files) - Wrapped docstrings, assertions, long lists

## Decisions Made
- Auto-fix first approach: run ruff --fix to handle the 46 auto-fixable violations, then manually fix the remaining B904 and E501
- No suppressions policy: every violation resolved by restructuring the code rather than adding noqa comments

## Deviations from Plan
None - plan executed exactly as written

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Python linting baseline is clean — `ruff check pipeline/ tests/` exits 0
- Ready for pre-push hook to gate on `npm run lint:py`

---
*Phase: 13-linting-baseline*
*Completed: 2026-02-25*
