---
phase: 17-fix-datadir-verify-chain
plan: 01
status: complete
started: 2026-02-25
completed: 2026-02-25
---

# Plan 17-01: Fix DATA_DIR Late-Binding — Summary

## What Was Built

Replaced import-time `DATA_DIR` binding with late-bound `pipeline.config.DATA_DIR` access across all 7 affected Python modules. Added environment variable override support to `pipeline/config.py`.

## Key Changes

### Task 1: Fix DATA_DIR binding + env var override

**Files modified:**
- `pipeline/config.py` — Added `os.environ.get("DATA_DIR", "data")` for env var override
- `pipeline/ingest/abs_data.py` — Removed `DATA_DIR` from imports, added `import pipeline.config`, replaced all `DATA_DIR` with `pipeline.config.DATA_DIR`, added logger + startup log
- `pipeline/ingest/rba_data.py` — Same pattern, added logger
- `pipeline/ingest/asx_futures_scraper.py` — Same pattern (logger already existed)
- `pipeline/ingest/corelogic_scraper.py` — Same pattern (logger already existed)
- `pipeline/ingest/nab_scraper.py` — Same pattern (logger already existed)
- `pipeline/normalize/ratios.py` — Removed `from pipeline.config import DATA_DIR`, added `import pipeline.config`
- `pipeline/normalize/engine.py` — Same pattern, also fixed internal late-import at line 188

### Task 2: Verify unit tests pass

- `tests/python/test_ratios.py` — Fixed `test_normalize_indicator_hybrid_cotality_abs_path` to provide enough data rows (was silently reading real `data/` directory due to the import-time binding bug)
- All 118 non-live tests pass
- Ruff reports 0 violations on all modified files
- `DATA_DIR` environment variable override verified working

## Decisions Made

- Used `import pipeline.config` + `pipeline.config.DATA_DIR` pattern (direct module attribute access) rather than a config accessor function — simpler, idiomatic Python
- Added startup `logger.info("DATA_DIR: %s", pipeline.config.DATA_DIR)` to each ingestor's `fetch_and_save()` for debugging visibility per user decision
- Left `SOURCE_METADATA` paths in config.py as import-time computed — documented known limitation, no current test failures from this

## Verification

- Zero remaining `from pipeline.config import.*DATA_DIR` in `pipeline/ingest/` and `pipeline/normalize/`
- 118/118 non-live tests pass (0 failures, 10 deselected live tests)
- Ruff: 0 violations
- ENV override: `DATA_DIR=/tmp/test python -c "import pipeline.config; print(pipeline.config.DATA_DIR)"` outputs `/tmp/test`
