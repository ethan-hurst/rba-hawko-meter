---
phase: 11-test-foundation
plan: 02
subsystem: testing
tags: [pytest, conftest, fixtures, socket-mocking, monkeypatch, smoke-tests, pandas]

# Dependency graph
requires: [11-01]
provides:
  - tests/python/conftest.py with autouse DATA_DIR isolation and network blocking
  - 7 fixture CSVs with real production data snapshots
  - tests/python/test_smoke.py proving all infrastructure guarantees
affects: [12-unit-tests, 13-smoke-tests, 14-git-hooks]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - autouse monkeypatch fixture for DATA_DIR isolation (import module, not attribute)
    - socket.socket monkeypatching for network blocking at OS level
    - live marker escape hatch via request.node.get_closest_marker("live")
    - FIXTURES_DIR = Path(__file__).parent for CWD-safe fixture resolution
    - fixture CSVs as real production data snapshots (not synthetic)

key-files:
  created:
    - tests/python/conftest.py
    - tests/python/fixtures/abs_cpi.csv
    - tests/python/fixtures/abs_employment.csv
    - tests/python/fixtures/abs_wage_price_index.csv
    - tests/python/fixtures/abs_household_spending.csv
    - tests/python/fixtures/abs_building_approvals.csv
    - tests/python/fixtures/corelogic_housing.csv
    - tests/python/fixtures/nab_capacity.csv
    - tests/python/test_smoke.py
  modified: []

key-decisions:
  - "Import pipeline.config as a module (not 'from pipeline.config import DATA_DIR') so monkeypatch targets the module attribute and patches are visible to all callers"
  - "block_network blocks localhost too — no exceptions for non-live tests (per user decision)"
  - "FIXTURES_DIR uses Path(__file__).parent to avoid CWD sensitivity"
  - "fixture CSVs are real production snapshots (~40-48 rows), not synthetic data (per user decision)"
  - "nab_capacity.csv copied in full (all 7 rows) since fewer than 40 exist in production"

patterns-established:
  - "Pattern: autouse isolate_data_dir — all tests get DATA_DIR patched to tmp_path automatically"
  - "Pattern: autouse block_network — all tests have network blocked; live marker exempts via get_closest_marker"
  - "Pattern: named CSV fixtures return DataFrames — tests request them explicitly, not autouse"

requirements-completed: [FOUND-02, FOUND-03]

# Metrics
duration: ~2min
completed: 2026-02-25
---

# Phase 11 Plan 02: Test Infrastructure (conftest + fixtures + smoke) Summary

**conftest.py with autouse DATA_DIR isolation (monkeypatch to tmp_path) and socket-level network blocker (live marker escape), 7 real-data fixture CSVs, and 5 smoke tests proving all three infrastructure guarantees**

## Performance

- **Duration:** ~2 min
- **Started:** 2026-02-24T22:01:42Z
- **Completed:** 2026-02-24T22:03:09Z
- **Tasks:** 2
- **Files created:** 9

## Accomplishments

- Created `tests/python/conftest.py` with:
  - `FIXTURES_DIR = Path(__file__).parent / "fixtures"` (CWD-safe)
  - `isolate_data_dir` autouse fixture: `monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)` — every test runs with an isolated data directory
  - `block_network` autouse fixture: replaces `socket.socket` with `blocked_socket()` that raises `RuntimeError("Network access blocked in tests...")`; live-marked tests are exempted via `request.node.get_closest_marker("live")`
  - 7 named CSV loader fixtures returning pandas DataFrames (not autouse)
- Created 7 fixture CSVs in `tests/python/fixtures/` from real production data:
  - 6 files with headers `date,value,source,series_id` (~40-48 rows each)
  - `nab_capacity.csv` with headers `date,value,source` (all 7 production rows copied)
- Created `tests/python/test_smoke.py` with 5 smoke tests:
  1. `test_pytest_discovers_and_exits_zero` — baseline discovery proof
  2. `test_data_dir_isolated_from_production` — confirms DATA_DIR != live `data/`
  3. `test_network_blocker_raises_runtime_error` — confirms socket raises RuntimeError
  4. `test_live_marker_exempts_network_block` — confirms live-marked tests can open sockets
  5. `test_fixture_csvs_loadable` — confirms fixture CSV loads as DataFrame with correct columns

## Task Commits

Each task was committed atomically:

1. **Task 1: Create conftest.py with autouse fixtures and CSV loaders** — `28c7c7a` (feat)
2. **Task 2: Create fixture CSVs and smoke tests** — `970a469` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `tests/python/conftest.py` — Test infrastructure: FIXTURES_DIR, isolate_data_dir autouse, block_network autouse, 7 CSV loader fixtures
- `tests/python/fixtures/abs_cpi.csv` — 40 rows, `date,value,source,series_id` (quarterly from 2014)
- `tests/python/fixtures/abs_employment.csv` — 48 rows, `date,value,source,series_id` (monthly from 2014)
- `tests/python/fixtures/abs_wage_price_index.csv` — 40 rows, `date,value,source,series_id` (quarterly from 2014)
- `tests/python/fixtures/abs_household_spending.csv` — 48 rows, `date,value,source,series_id` (monthly from 2014)
- `tests/python/fixtures/abs_building_approvals.csv` — 48 rows, `date,value,source,series_id` (monthly from 2014)
- `tests/python/fixtures/corelogic_housing.csv` — 40 rows, `date,value,source,series_id` (quarterly from 2003)
- `tests/python/fixtures/nab_capacity.csv` — 7 rows, `date,value,source` (all production rows)
- `tests/python/test_smoke.py` — 5 smoke tests proving DATA_DIR isolation, network blocking, live marker tier separation, fixture loading

## Decisions Made

- Imported `pipeline.config` as a module (not `from pipeline.config import DATA_DIR`) — ensures monkeypatch targets the module attribute so all code reading `pipeline.config.DATA_DIR` at call time sees the patched value
- `block_network` blocks localhost too — no carve-outs for non-live tests, per user decision
- `FIXTURES_DIR = Path(__file__).parent / "fixtures"` — avoids CWD sensitivity (research pitfall #4)
- Fixture CSVs are real production snapshots, not synthetic data — per user decision
- `nab_capacity.csv` copied in full (only 7 rows exist in production)

## Deviations from Plan

None — plan executed exactly as written.

## Verification Results

All checks passed:

1. `pytest tests/python/ -m "not live" -v` — 4 passed, 1 deselected, exit 0
2. `pytest tests/python/ -m live -v` — 1 passed, 4 deselected, exit 0
3. `pytest tests/python/ -v` — 5 passed, exit 0
4. `python -c "import pipeline.config; print(pipeline.config.DATA_DIR)"` — prints `data` (production untouched)
5. `ls tests/python/fixtures/*.csv | wc -l` — returns 7
6. `head -1 tests/python/fixtures/abs_cpi.csv` — `date,value,source,series_id`
7. `head -1 tests/python/fixtures/nab_capacity.csv` — `date,value,source` (no series_id)

## Self-Check: PASSED

Files verified:
- FOUND: tests/python/conftest.py
- FOUND: tests/python/test_smoke.py
- FOUND: tests/python/fixtures/abs_cpi.csv
- FOUND: tests/python/fixtures/abs_employment.csv
- FOUND: tests/python/fixtures/abs_wage_price_index.csv
- FOUND: tests/python/fixtures/abs_household_spending.csv
- FOUND: tests/python/fixtures/abs_building_approvals.csv
- FOUND: tests/python/fixtures/corelogic_housing.csv
- FOUND: tests/python/fixtures/nab_capacity.csv

Commits verified:
- FOUND: 28c7c7a (conftest.py)
- FOUND: 970a469 (fixture CSVs + smoke tests)

---
*Phase: 11-test-foundation*
*Completed: 2026-02-25*
