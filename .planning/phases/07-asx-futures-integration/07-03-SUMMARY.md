---
phase: 07
plan: 03
status: complete
type: workflow
subsystem: ci-cd
tags: [github-actions, playwright, testing, workflow-automation]
requires: [07-01, 07-02]
provides:
  - Daily ASX futures workflow commits status.json after regeneration
  - Weekly pipeline workflow commits status.json alongside CSVs
  - Concurrency guards prevent race conditions between daily/weekly workflows
  - Playwright tests verify ASX futures section renders correctly
  - Bug fix for probability percentage formatting
affects: []
tech-stack:
  added: []
  patterns: [playwright-route-interception, github-actions-concurrency]
key-files:
  created: []
  modified:
    - .github/workflows/daily-asx-futures.yml
    - .github/workflows/weekly-pipeline.yml
    - requirements.txt
    - tests/dashboard.spec.js
    - public/js/interpretations.js
decisions:
  - id: concurrency-group
    decision: Use shared 'data-pipeline' concurrency group with cancel-in-progress: false
    rationale: Prevents daily scraper and weekly pipeline from committing simultaneously while allowing running jobs to complete
    alternatives: [separate groups, cancel-in-progress: true, no concurrency control]
  - id: status-regeneration
    decision: Daily workflow regenerates status.json after scraping
    rationale: Ensures dashboard reflects latest ASX futures data immediately after scraper completes
    alternatives: [rely only on weekly pipeline, separate workflow for status.json]
  - id: test-mocking
    decision: Use page.route() to inject mock asx_futures data into status.json
    rationale: Tests work regardless of whether real ASX data exists; isolates frontend rendering logic
    alternatives: [require real data, mock entire status.json, skip testing]
completed: 2026-02-06
duration: 3 minutes
---

# Phase 7 Plan 03: CI/CD Workflow Updates & Frontend Testing Summary

**One-liner:** Added status.json commits to workflows, concurrency guards to prevent race conditions, Playwright tests for ASX futures section, and fixed probability percentage formatting bug.

## What Changed

### Task 1: Update CI/CD workflows and clean up requirements.txt

**Daily ASX futures workflow (.github/workflows/daily-asx-futures.yml):**
- Added concurrency group `data-pipeline` with `cancel-in-progress: false`
- Added step to regenerate status.json after scraping: `python -m pipeline.normalize.engine`
- Updated file_pattern to commit both `data/asx_futures.csv` and `public/data/status.json`

**Weekly pipeline workflow (.github/workflows/weekly-pipeline.yml):**
- Added concurrency group `data-pipeline` with `cancel-in-progress: false`
- Updated file_pattern to commit `data/*.csv public/data/status.json`

**Dependencies (requirements.txt):**
- Removed unused `pyarrow>=14.0` dependency (no parquet file handling in codebase)

### Task 2: Add Playwright tests for ASX futures section

**New tests (tests/dashboard.spec.js):**
- Test 6: Verifies ASX futures section renders probability table when data available
  - Uses `page.route()` to inject mock asx_futures data
  - Verifies "What Markets Expect" heading appears
  - Verifies probability values render correctly (85.0%, 15.0%)
- Test 7: Verifies ASX futures section hidden when data unavailable
  - Uses `page.route()` to set `asx_futures: null`
  - Verifies container has `display: none`

**Bug fix (public/js/interpretations.js):**
- Fixed probability percentage formatting bug in `renderASXTable` function
- Changed `percentFormatter.format(outcome.prob)` to `percentFormatter.format(outcome.prob / 100)`
- Root cause: `Intl.NumberFormat` with `style: 'percent'` expects 0-1 values, but status.json provides 0-100
- Result: Displays "85.0%" instead of "8,500.0%"

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ASX futures probability percentage formatting**

- **Found during:** Task 2 test execution
- **Issue:** Probability percentages displaying as "8,500.0%" instead of "85%"
- **Root cause:** `percentFormatter` (Intl.NumberFormat with style: 'percent') expects values 0-1 but received 0-100 from status.json
- **Fix:** Divide by 100 before passing to formatter: `percentFormatter.format(outcome.prob / 100)`
- **Files modified:** `public/js/interpretations.js` (line 160)
- **Commit:** 4f4fd5b
- **Rationale:** This is a genuine bug (broken behavior) — the frontend code was written assuming a different data format than what the backend actually provides. Auto-fixed under deviation Rule 1.

## Task Commits

| Task | Description | Commit | Files Modified |
|------|-------------|--------|----------------|
| 1 | Update workflows to commit status.json and add concurrency guards | b4d9164 | .github/workflows/daily-asx-futures.yml, .github/workflows/weekly-pipeline.yml, requirements.txt |
| 2 | Add Playwright tests for ASX futures section | 4f4fd5b | tests/dashboard.spec.js, public/js/interpretations.js |

## Verification Results

All plan verification checks passed:

1. ✓ Daily workflow regenerates status.json after scraping
2. ✓ Daily workflow commits both `data/asx_futures.csv` and `public/data/status.json`
3. ✓ Weekly workflow commits `public/data/status.json` alongside `data/*.csv`
4. ✓ Both workflows share concurrency group `data-pipeline`
5. ✓ pyarrow removed from requirements.txt
6. ✓ All 7 Playwright tests pass (5 existing + 2 new)

## Success Criteria Met

- [x] Daily workflow regenerates status.json after scraping and commits both data/asx_futures.csv and public/data/status.json
- [x] Weekly workflow commits public/data/status.json alongside data/*.csv
- [x] Both workflows use concurrency group `data-pipeline` to prevent race conditions
- [x] pyarrow removed from requirements.txt
- [x] Playwright tests verify ASX futures section renders probability table with data and hides gracefully without data
- [x] All 7 Playwright tests pass

## Next Phase Readiness

**Blockers:** None

**Concerns:** None

**Notes:**
- Daily workflow will now update the dashboard immediately after scraping ASX futures data
- Weekly pipeline continues to commit status.json as part of the full data refresh
- Concurrency guards ensure these workflows never run simultaneously (avoiding git conflicts)
- Frontend ASX futures rendering is now fully tested with both success and null-data scenarios

## Self-Check: PASSED

All created files and commits verified:

**Modified files verified:**
- .github/workflows/daily-asx-futures.yml exists and contains concurrency group + regenerate step
- .github/workflows/weekly-pipeline.yml exists and contains concurrency group + status.json in file_pattern
- requirements.txt exists and pyarrow removed
- tests/dashboard.spec.js exists and contains 7 tests
- public/js/interpretations.js exists with bug fix applied

**Commits verified:**
- b4d9164: chore(07-03): update workflows to commit status.json and add concurrency guards
- 4f4fd5b: test(07-03): add Playwright tests for ASX futures section
