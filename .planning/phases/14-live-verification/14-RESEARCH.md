# Phase 14: Live Verification - Research

**Researched:** 2026-02-25
**Domain:** pytest live test tier, Python warnings, ASCII table reporting, npm script orchestration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Test depth per endpoint:**
- Full depth for ALL sources (APIs and scrapers alike): connectivity, response structure, and data quality checks
- One test function per source (7 separate tests) — easy to see which specific source failed
- Structural failures (missing columns, changed API shape) = hard test failure
- Data quality issues (stale data, empty values) = pytest warning, not failure
- All live tests marked with `@pytest.mark.live` (existing tier system from Phase 11)

**Warning and output format:**
- Use `pytest.warns` with details: URL, HTTP status code, and reason for the warning
- Summary table after `npm run verify`: ASCII table in terminal showing each indicator, status (PASS/WARN/FAIL), and latest data date
- Table includes hawk_score and overall result line (e.g., "PASS (1 warning)")

**Pipeline verification isolation:**
- Individual live pytest tests use temp directories (same isolation as unit tests)
- `npm run verify` writes to real `data/` and `public/data/` directories (production paths)
- `npm run verify` runs a single `python pipeline/main.py` invocation — tests the real orchestrator path
- After pipeline completes, verify reads `status.json` and prints the ASCII summary table

**Verification reporting:**
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

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| LIVE-01 | Developer can verify ABS, RBA, ASX API ingestion works with real endpoints | Seven `@pytest.mark.live` test functions, one per source; existing ingestors callable directly |
| LIVE-02 | Developer can verify Cotality and NAB scrapers work against live pages | Same test file, Cotality + NAB test functions; scraper pattern already handles failures gracefully |
| LIVE-03 | Full pipeline run produces valid status.json with all indicators | `npm run verify` invokes `python pipeline/main.py` then reads `public/data/status.json`; Python summary script checks for 7 gauge keys |
| LIVE-04 | Live test failures are non-blocking warnings (graceful degradation preserved) | `warnings.warn()` inside test body exits 0; `pytest.warns()` is for asserting a warning was raised (not the pattern needed here) |
</phase_requirements>

---

## Summary

Phase 14 adds two distinct verification mechanisms. The first is a pytest live test file (`tests/python/test_live_sources.py`) that contains one test function per data source — ABS CPI, ABS Employment, ABS WPI, ABS Household Spending, ABS Building Approvals, RBA Cash Rate, and ASX Futures for LIVE-01, plus Cotality and NAB for LIVE-02. All functions carry `@pytest.mark.live`, which the existing `block_network` fixture in `conftest.py` already handles correctly. The second mechanism is `npm run verify`, a new npm script that runs `python pipeline/main.py` against real data directories, then calls a Python summary script that reads `public/data/status.json` and renders an ASCII box-drawing table.

The existing codebase provides nearly all the pieces needed. The `@pytest.mark.live` marker and its fixture exemption already exist in Phase 11 infrastructure. All seven ingestors (`abs_data`, `rba_data`, `asx_futures_scraper`, `corelogic_scraper`, `nab_scraper`) expose `fetch_and_save()` callables. The `pipeline/main.py` orchestrator already produces `public/data/status.json` via `generate_status()`. The only net-new code is the live test file, a verify summary script, and two npm script entries.

The key design question for LIVE-04 (non-blocking failures) is the difference between `warnings.warn()` and `pytest.warns()`. The CONTEXT.md says "use `pytest.warns` with details", which implies asserting a warning is emitted — but the requirement is that the suite *exits 0 even when an external service is down*. The correct pattern is: try the request, catch any exception, call `warnings.warn()` with URL/status/reason details, and let the test pass. `pytest.warns()` is a context manager for *asserting* warnings were raised — not the right tool for graceful degradation. The implementation should use `warnings.warn(UserWarning, ...)` inside try-except and let the test function return normally.

**Primary recommendation:** Implement a single `tests/python/test_live_sources.py` with 7 `@pytest.mark.live` test functions (one per source), plus a `scripts/verify_summary.py` Python script called by `npm run verify` after the pipeline run.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | 9.0.2 (installed) | Test runner, live marker, warning capture | Already in requirements-dev.txt |
| warnings (stdlib) | Python 3.13 | Issue UserWarning from test body | No extra deps, integrates with pytest -W output |
| requests | >=2.28 (installed) | HTTP client for live endpoint checks | Already used by all ingestors |
| json (stdlib) | Python 3.13 | Read status.json for verify step | No extra deps |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| subprocess | stdlib | `npm run verify` invokes `python pipeline/main.py` | npm script → Python orchestration |
| pathlib | stdlib | Path resolution in verify script | Already project-wide convention |
| pandas | >=2.0 (installed) | Read CSV columns for data freshness check | Already project dependency |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `warnings.warn()` inside test body | `pytest.warns()` as context manager | `pytest.warns()` ASSERTS a warning was raised — it fails if none is emitted. For graceful degradation you need plain `warnings.warn()` so the test passes whether or not the endpoint is up |
| Python `scripts/verify_summary.py` | Shell script or Node.js | Python already has json/pathlib, consistent with pipeline; no new language |
| Direct function calls in live tests | Independent HTTP requests | Direct calls test the actual ingestor path (data quality checks included); independent requests add maintenance burden |

**Installation:** No new packages required. All dependencies already in `requirements.txt` and `requirements-dev.txt`.

---

## Architecture Patterns

### Recommended Project Structure

```
tests/python/
└── test_live_sources.py     # NEW: 7 @pytest.mark.live test functions

scripts/
├── backfill_historical.py   # existing
├── generate_frontend_data.py # existing
└── verify_summary.py        # NEW: reads status.json, prints ASCII table

package.json                 # add test:python:live and verify scripts
```

### Pattern 1: Live Test Function (graceful degradation)

**What:** Each test calls the ingestor's `fetch_and_save()` function directly. On structural success (right columns returned), the test passes. On data quality issues (stale, empty), it calls `warnings.warn()` and still passes. On hard failures (wrong columns, HTTP error that indicates a permanent API change), it hard-fails.

**When to use:** All 7 source tests.

```python
# tests/python/test_live_sources.py
import warnings
import pytest
import pandas as pd
from pipeline.ingest import abs_data

@pytest.mark.live
def test_live_abs_cpi(tmp_path, monkeypatch):
    """ABS CPI: connectivity + response structure + data quality."""
    import pipeline.config
    monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)

    result = abs_data.fetch_and_save("cpi")

    # Structural check: result dict must exist
    assert isinstance(result, dict), "fetch_and_save must return a dict"
    assert "cpi" in result, "Expected 'cpi' key in result"

    # Read the CSV to verify structure
    csv_path = tmp_path / "abs_cpi.csv"
    assert csv_path.exists(), "abs_cpi.csv must be created"
    df = pd.read_csv(csv_path)

    # Structural failure: hard fail — API shape has changed
    required_cols = {"date", "value", "source"}
    missing = required_cols - set(df.columns)
    assert not missing, f"Missing required columns: {missing}"

    # Data quality: warn, don't fail
    if len(df) == 0:
        warnings.warn(
            "ABS CPI returned 0 rows — endpoint may be returning empty data",
            UserWarning,
            stacklevel=2,
        )
        return

    # Staleness check: warn if data is older than 45 days
    df["date"] = pd.to_datetime(df["date"])
    latest = df["date"].max()
    staleness = (pd.Timestamp.now() - latest).days
    if staleness > 45:
        warnings.warn(
            f"ABS CPI latest data is {staleness} days old "
            f"(latest: {latest.date()}) — may be stale",
            UserWarning,
            stacklevel=2,
        )
```

### Pattern 2: Scraper Test (HTTP 404 / missing data = warning)

**What:** Scrapers (Cotality, NAB) return empty DataFrames or status dicts on failure. Test treats an empty return as a warning, not a failure, because the external page structure may legitimately lag.

```python
@pytest.mark.live
def test_live_cotality_scraper(tmp_path, monkeypatch):
    """Cotality HVI: scraper connectivity + PDF parse + data quality."""
    import pipeline.config
    monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)
    from pipeline.ingest import corelogic_scraper

    result = corelogic_scraper.fetch_and_save()

    assert isinstance(result, dict), "fetch_and_save must return a dict"
    assert "status" in result, "Result must have a 'status' key"

    if result["status"] != "success":
        warnings.warn(
            f"Cotality scraper did not succeed: {result.get('error', 'unknown')} "
            "— PDF may not be available yet this month",
            UserWarning,
            stacklevel=2,
        )
```

### Pattern 3: ASX Test (special — reads rba_cash_rate.csv dependency)

**What:** ASX scraper reads `DATA_DIR / "rba_cash_rate.csv"` for current cash rate (falls back to 4.35 if missing). Live test can pre-seed a minimal CSV in tmp_path, or let it use the fallback. Both are valid since the test is checking the API connectivity and JSON shape, not the rate calculation.

```python
@pytest.mark.live
def test_live_asx_futures(tmp_path, monkeypatch):
    """ASX Futures: MarkitDigital API connectivity + response structure."""
    import pipeline.config
    monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)
    from pipeline.ingest import asx_futures_scraper

    result = asx_futures_scraper.fetch_and_save()

    assert isinstance(result, dict)
    assert "status" in result

    if result["status"] != "success":
        warnings.warn(
            f"ASX futures scraper returned non-success: {result.get('error', 'unknown')}",
            UserWarning,
            stacklevel=2,
        )
        return

    csv_path = tmp_path / "asx_futures.csv"
    assert csv_path.exists(), "asx_futures.csv must be created on success"
    df = pd.read_csv(csv_path)
    required_cols = {"date", "meeting_date", "implied_rate", "probability_cut",
                     "probability_hold", "probability_hike"}
    missing = required_cols - set(df.columns)
    assert not missing, f"ASX futures CSV missing columns: {missing}"
```

### Pattern 4: `npm run verify` — Pipeline + Summary Table

**What:** npm script calls `python pipeline/main.py`, then calls `python scripts/verify_summary.py`. The summary script reads `public/data/status.json` and prints the ASCII table.

```json
// package.json additions
{
  "scripts": {
    "test:python:live": "python -m pytest tests/python/ -m live -v",
    "verify": "python pipeline/main.py && python scripts/verify_summary.py"
  }
}
```

```python
# scripts/verify_summary.py
import json
import sys
from pathlib import Path
from datetime import datetime

STATUS_FILE = Path("public/data/status.json")
INDICATOR_LABELS = {
    "inflation":          "ABS CPI",
    "employment":         "ABS Employment",
    "wages":              "ABS WPI",
    "spending":           "ABS Household Spending",
    "building_approvals": "ABS Building Approvals",
    "housing":            "Cotality HVI",
    "business_confidence":"NAB Capacity",
}

def main():
    if not STATUS_FILE.exists():
        print("ERROR: public/data/status.json not found — pipeline may have failed")
        sys.exit(1)

    with open(STATUS_FILE) as f:
        status = json.load(f)

    gauges = status.get("gauges", {})
    hawk_score = status["overall"]["hawk_score"]

    # Check 7 indicator keys present
    missing = [k for k in INDICATOR_LABELS if k not in gauges]

    W = 48
    sep = "─" * W
    rows = []
    warnings_count = 0

    for key, label in INDICATOR_LABELS.items():
        if key not in gauges:
            rows.append((label, "FAIL", "missing"))
        else:
            g = gauges[key]
            staleness = g.get("staleness_days", 999)
            data_date = g.get("data_date", "unknown")
            # Format date as Mon YYYY
            try:
                dt = datetime.strptime(data_date, "%Y-%m-%d")
                date_label = dt.strftime("%b %Y")
            except ValueError:
                date_label = data_date

            if staleness > 90:
                status_str = "WARN"
                warnings_count += 1
            else:
                status_str = "PASS"
            rows.append((label, status_str, date_label))

    print(sep)
    print(f"  RBA Hawk-O-Meter — Live Verification")
    print(sep)
    print(f" {'Indicator':<22} {'Status':<8} {'Latest'}")
    print(sep)
    for label, st, date in rows:
        print(f" {label:<22} {st:<8} {date}")
    print(sep)
    print(f" Hawk Score: {hawk_score} / 100")
    if missing:
        result_str = f"FAIL ({len(missing)} indicator(s) missing)"
        exit_code = 1
    elif warnings_count:
        result_str = f"PASS ({warnings_count} warning{'s' if warnings_count != 1 else ''})"
        exit_code = 0
    else:
        result_str = "PASS"
        exit_code = 0
    print(f" Result: {result_str}")
    print(sep)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
```

### Anti-Patterns to Avoid

- **Using `pytest.warns()` as the graceful degradation mechanism:** `pytest.warns()` ASSERTS that a warning is emitted — the test fails if no warning is raised. For LIVE-04, the test should call `warnings.warn()` and pass regardless. Only use `pytest.warns()` in the unit test suite to assert specific warning scenarios.
- **Calling ingestors without patching DATA_DIR:** The `isolate_data_dir` autouse fixture patches `DATA_DIR` to `tmp_path` for all tests. Live tests still get this isolation — they hit real networks but write to tmp_path. This is correct behavior.
- **Re-validating the full schema in verify_summary.py:** Unit tests in `test_schema.py` own schema validation. The summary script only needs to check the 7 indicator keys exist and hawk_score is in [0, 100].
- **Constructing test URLs independently:** Tests should call the existing `fetch_and_save()` functions, not reconstruct the URL logic. The goal is verifying the ingestor path works end-to-end, not a parallel HTTP check.
- **Making ASX test fail when rba_cash_rate.csv is absent:** `_get_current_cash_rate()` in `asx_futures_scraper.py` already falls back to 4.35 if the CSV is missing. Live tests don't need to seed this file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Warning emission in tests | Custom warning class | `warnings.warn(msg, UserWarning)` | stdlib, pytest captures automatically with `-W` flag |
| ASCII box-drawing table | Rich/tabulate library | Plain string formatting with `─` and f-strings | No new dependency; the output is simple enough |
| Per-test timeout | Custom signal handling | pytest `timeout` plugin or `requests` timeout param | Ingestors already set `DEFAULT_TIMEOUT = 30` on all requests |
| CSV column validation | Schema library | Simple set arithmetic on `df.columns` | Already the pattern in the unit tests |

**Key insight:** All ingestors already handle their own failures gracefully (try-except, return status dicts, logger.warning). The live tests are thin wrappers that call `fetch_and_save()` and translate the result into a pytest pass/warning.

---

## Common Pitfalls

### Pitfall 1: `isolate_data_dir` patches DATA_DIR but not SOURCE_METADATA

**What goes wrong:** `pipeline/config.py` computes `SOURCE_METADATA` paths at import time from the *original* `DATA_DIR = Path("data")`. After `monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)`, the `SOURCE_METADATA` paths still point to the real `data/` directory.

**Why it happens:** Module-level expressions are evaluated once at import. The autouse conftest note already documents this.

**How to avoid:** Live tests should not use `SOURCE_METADATA` paths directly. They call `fetch_and_save()` which uses `DATA_DIR` at *call time* (not import time), so it picks up the patched value. The only scrapers that might read `SOURCE_METADATA` are in the normalization engine — live tests don't call `generate_status()` (that's `npm run verify`'s job, not pytest's).

**Warning signs:** Test writes to `data/*.csv` instead of `tmp_path/*.csv`.

### Pitfall 2: ASX scraper reads `meetings.json` from a relative path

**What goes wrong:** `_get_rba_meeting_dates()` opens `Path("public/data/meetings.json")` as a relative path. From pytest's working directory (project root), this works fine. From a different CWD, it returns an empty list and the scraper produces rows without meeting dates.

**Why it happens:** Path is not anchored to the project root.

**How to avoid:** Live tests should be run from the project root (standard pytest invocation). The existing pytest setup (`testpaths = ["tests/python"]`) already implies project root as CWD. Document this as a prerequisite in the npm script comment.

**Warning signs:** Live ASX test passes but all `meeting_date` values equal the contract expiry date rather than an RBA meeting date.

### Pitfall 3: Cotality idempotency check fires during test

**What goes wrong:** `_current_month_already_scraped()` in `corelogic_scraper.py` checks if the current month is already in `DATA_DIR / "corelogic_housing.csv"`. In a `tmp_path` (always fresh), this check always returns False — correct. But if DATA_DIR is not patched (e.g., fixture not triggered), it reads the real CSV and may return True, making the scraper return an empty DataFrame and the test emit a spurious warning.

**Why it happens:** `isolate_data_dir` is autouse, so it IS applied to live tests. This pitfall only bites if someone removes the autouse fixture or tests without it.

**How to avoid:** Confirm `isolate_data_dir` remains autouse. Live tests still get a fresh `tmp_path` even though they have real network access.

### Pitfall 4: `npm run verify` exit code semantics

**What goes wrong:** If `pipeline/main.py` exits 1 (critical source failure), the `&&` in `python pipeline/main.py && python scripts/verify_summary.py` prevents the summary script from running. The developer sees a pipeline error but no summary table.

**Why it happens:** Shell `&&` short-circuits on non-zero exit.

**How to avoid:** Use `; python scripts/verify_summary.py` OR have `verify_summary.py` handle the missing `status.json` case gracefully (it already does in the pattern above). Better: keep `&&` for correctness — if pipeline fails critically, there's no status.json to summarize anyway. Document that `npm run verify` exits non-zero on critical source failure.

### Pitfall 5: `pytest.warns()` semantics mismatch

**What goes wrong:** CONTEXT.md says "use `pytest.warns` with details". If the planner interprets this as wrapping the `fetch_and_save()` call in `with pytest.warns(UserWarning):`, the test will FAIL whenever the endpoint is up and working correctly (because no warning is emitted).

**Why it happens:** `pytest.warns()` requires at least one matching warning or it raises `Failed: DID NOT WARN`. The intent in CONTEXT.md is about the *format* of warnings (include URL, status, reason), not the assertion mechanism.

**How to avoid:** The correct pattern for LIVE-04 is:
```python
# CORRECT: test passes whether endpoint is up or down
try:
    result = fetch_and_save(...)
    # check structure...
except Exception as e:
    warnings.warn(f"URL: ... Status: ... Reason: {e}", UserWarning, stacklevel=2)

# WRONG: test fails when endpoint is working (no warning emitted)
with pytest.warns(UserWarning):
    result = fetch_and_save(...)
```

---

## Code Examples

### Verified patterns from project codebase

### Existing live marker infrastructure (conftest.py)

```python
# Source: /tests/python/conftest.py (Phase 11, already implemented)
@pytest.fixture(autouse=True)
def block_network(monkeypatch, request):
    if request.node.get_closest_marker("live"):
        yield  # live tests: network allowed
        return
    # non-live tests: network blocked
    monkeypatch.setattr(socket, "socket", blocked_socket)
    yield
```

The live marker system is complete. No changes to conftest.py needed for Phase 14.

### Existing ingestor entry points for live tests

```python
# All ingestors expose fetch_and_save() — call these in live tests

# API-based (return dict of {series: row_count})
abs_data.fetch_and_save("cpi")           # -> {"cpi": N}
abs_data.fetch_and_save("employment")    # -> {"employment": N}
abs_data.fetch_and_save("wage_price_index")   # -> {"wage_price_index": N}
abs_data.fetch_and_save("household_spending") # -> {"household_spending": N}
abs_data.fetch_and_save("building_approvals") # -> {"building_approvals": N}
rba_data.fetch_and_save()                # -> int (row count)

# Scraper-based (return status dict)
asx_futures_scraper.fetch_and_save()     # -> {"status": "success"/"failed", ...}
corelogic_scraper.fetch_and_save()       # -> {"status": "success"/"failed", ...}
nab_scraper.fetch_and_save()             # -> {"status": "success"/"failed", ...}
```

### Indicator key mapping for verify_summary.py

```python
# From pipeline/config.py INDICATOR_CONFIG + OPTIONAL_INDICATOR_CONFIG
# 7 gauge keys in status.json["gauges"]:
# "inflation", "wages", "employment", "spending",
# "building_approvals", "housing", "business_confidence"
# (asx_futures is top-level, not in gauges)
```

### ASCII table style (from CONTEXT.md specifics)

```
────────────────────────────────────────────────
  RBA Hawk-O-Meter — Live Verification
────────────────────────────────────────────────
 Indicator              Status   Latest
────────────────────────────────────────────────
 ABS CPI                PASS     Jan 2026
 ABS Employment         PASS     Jan 2026
 ABS WPI                PASS     Oct 2025
 ABS Household Spending PASS     Jan 2026
 ABS Building Approvals PASS     Jan 2026
 Cotality HVI           WARN     Feb 2026
 NAB Capacity           PASS     Feb 2026
────────────────────────────────────────────────
 Hawk Score: 62 / 100
 Result: PASS (1 warning)
────────────────────────────────────────────────
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No live test tier | `@pytest.mark.live` with `block_network` fixture exemption | Phase 11 (2026-02-24) | Live tests already plumbed — Phase 14 just adds the test functions |
| Manual pipeline runs | `npm run verify` with automated summary | Phase 14 (this phase) | Single command replaces manual `python pipeline/main.py` + visual inspection of status.json |
| `pytest.warns()` for asserting warnings | `warnings.warn()` for graceful degradation | N/A — clarification | The two patterns serve different purposes; don't conflate them |

---

## Open Questions

1. **`hawk_score` is `float` in current status.json**
   - What we know: `public/data/status.json` has `"hawk_score": 52.0` (float). The schema unit test enforces integer type via `StrictValidator`. The normalization engine does `round(hawk_score, 1)` which returns a float.
   - What's unclear: Will `npm run verify` fail the `hawk_score in [0, 100]` check if the value is 52.0? The summary script just reads the JSON — Python's `json.load()` parses `52.0` as float, and `0 <= 52.0 <= 100` is True. No issue for the summary check.
   - Recommendation: The verify_summary.py check `0 <= hawk_score <= 100` works for both int and float. Don't add a type assertion there (unit tests own that).

2. **Seven sources vs `test:python:live` description in CONTEXT.md**
   - What we know: CONTEXT.md specifies "7 separate tests" and `npm run test:python:live` for per-source live tests. The 7 gauge sources are: ABS CPI, ABS Employment, ABS WPI, ABS Household Spending, ABS Building Approvals, Cotality HVI, NAB Capacity. ASX Futures is NOT in the gauges (it's top-level in status.json) but LIVE-01 says "ABS, RBA, ASX" endpoints.
   - What's unclear: Whether "7 separate tests" means 7 gauge sources (excluding RBA+ASX which are separate) or the 9 total sources across requirements.
   - Recommendation: Write one test per distinct `fetch_and_save()` call: ABS CPI, ABS Employment, ABS WPI, ABS Household Spending, ABS Building Approvals, RBA Cash Rate, ASX Futures, Cotality, NAB = 9 tests total. This covers LIVE-01 (ABS+RBA+ASX) and LIVE-02 (Cotality+NAB) completely. The "7 separate" in CONTEXT.md likely referred to indicators, not sources.

3. **Per-test timeout for slow scrapers**
   - What we know: `DEFAULT_TIMEOUT = 30` in config. NAB scraper can take longer due to tag archive discovery + article fetch + optional PDF download (up to 3 × 30s = 90s). Cotality PDF download can be 30-60s.
   - What's unclear: Whether pytest-timeout is already installed.
   - Recommendation: Check `pip list | grep timeout`. If not installed, add a `pytest.ini` timeout marker or use `@pytest.mark.timeout(120)` per test if pytest-timeout is available. As a fallback, the `requests` sessions already have `DEFAULT_TIMEOUT = 30` per request. Worst case: slow tests are just slow (not a blocker).

---

## Validation Architecture

> `workflow.nyquist_validation` is not present in `.planning/config.json` — this key is absent, which means nyquist validation is not explicitly enabled. Skipping this section.

---

## Sources

### Primary (HIGH confidence)

- Codebase — `/tests/python/conftest.py` — live marker and block_network fixture (verified working, Phase 11)
- Codebase — `/pipeline/ingest/*.py` — all fetch_and_save() signatures and return types
- Codebase — `/pipeline/normalize/engine.py` — generate_status() and 7 gauge key names
- Codebase — `/pipeline/config.py` — DATA_DIR, SOURCE_METADATA, ASX_FUTURES_URLS, timeout values
- Codebase — `/public/data/status.json` — production structure, 7 gauge keys confirmed
- Codebase — `/pyproject.toml` — pytest 9.0.2, markers config, testpaths
- Python 3.13 stdlib — `warnings.warn()` semantics verified via REPL
- pytest 9.0.2 — `pytest.warns()` semantics verified via `help(pytest.warns)`

### Secondary (MEDIUM confidence)

- `.planning/phases/14-live-verification/14-CONTEXT.md` — locked decisions from user discussion

### Tertiary (LOW confidence)

- None — all findings verified against codebase or stdlib

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified against installed packages, no new deps needed
- Architecture: HIGH — verified against existing ingestor APIs and conftest.py patterns
- Pitfalls: HIGH — SOURCE_METADATA import-time issue documented in existing conftest.py; warnings semantics verified via REPL
- Open questions: MEDIUM — question 2 (test count) is ambiguous from CONTEXT.md wording

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (30 days; external URLs may change but test patterns are stable)
