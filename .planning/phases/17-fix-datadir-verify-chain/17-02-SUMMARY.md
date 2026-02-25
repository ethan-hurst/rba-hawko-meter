---
phase: 17-fix-datadir-verify-chain
plan: 02
status: complete
started: 2026-02-25
completed: 2026-02-25
---

# Plan 17-02: Wire verify_summary.py into npm verify Chain — Summary

## What Was Built

Updated `package.json` to include `verify_summary.py` as the final step in `npm run verify` and added individual tier scripts for dev convenience.

## Key Changes

### Task 1: Update package.json scripts

**File modified:** `package.json`

New/updated scripts:
- `verify:fast` — `npm run lint && python -m pytest tests/python/ -m "not live"` (first tier)
- `verify:live` — `python -m pytest tests/python/ -m live -v` (second tier)
- `verify:playwright` — `npx playwright test` (third tier)
- `verify` — `npm run verify:fast && npm run verify:live && npm run verify:playwright && python scripts/verify_summary.py` (full chain)
- `test:fast` — Updated to use `python -m pytest` for consistent binary resolution

### Task 2: Validate verify chain wiring

- `npm run verify:fast` exits 0 (118 tests pass, linting clean)
- `npm run test:fast` exits 0 (backward compatible with lefthook pre-push hook)
- All 4 verify scripts correctly defined in package.json
- `verify_summary.py` accessible at `scripts/verify_summary.py`

## Decisions Made

- `test:fast` and `verify:fast` are intentionally identical — `test:fast` is the pre-push hook entry point, `verify:fast` is the first tier of the verify chain
- Used `&&` chaining for fail-fast behavior (stops at first failing tier)
- `verify_summary.py` runs as the final step after all three tiers pass, not between tiers

## Verification

- `npm run verify:fast` passes
- `npm run test:fast` passes (backward compatibility)
- `verify` script includes `verify_summary.py` as final step
- Individual tier scripts all defined and resolvable
