# Architecture Research

**Domain:** Local CI & Test Infrastructure — RBA Hawk-O-Meter v2.0
**Researched:** 2026-02-24
**Confidence:** HIGH (all findings verified against live codebase)

## Context: What This Research Covers

This replaces the v1.1 ARCHITECTURE.md (scraper integration) with v2.0 focus:
integration of pytest, ruff, ESLint, a pre-push git hook, and npm orchestration
scripts into the existing Python/vanilla-JS pipeline. No new product features.
The question is purely: where do test files live, how do tools discover them,
and how do they wire together?

---

## System Overview

### Before v2.0: Test Landscape

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Existing Test Surface                           │
│                                                                      │
│  tests/                        pipeline/                            │
│  ├── dashboard.spec.js         ├── main.py                          │
│  ├── calculator.spec.js        ├── config.py                        │
│  └── phase6-ux.spec.js         ├── ingest/*.py       NO UNIT TESTS  │
│                                ├── normalize/*.py    NO UNIT TESTS  │
│  Playwright E2E only           └── utils/*.py        NO UNIT TESTS  │
│  Requires: python3 -m http.server 8080                              │
│  Command: npx playwright test                                        │
└─────────────────────────────────────────────────────────────────────┘
```

### After v2.0: Test Infrastructure

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Pre-push Gate (fast)                            │
│   .git/hooks/pre-push                                               │
│   └── npm run test:fast                                             │
│        ├── ruff check pipeline/      (Python lint)                  │
│        ├── ruff format --check pipeline/  (Python format)           │
│        ├── eslint public/js/         (JS lint)                      │
│        └── pytest tests/python/ -m "not live"  (unit tests only)   │
└──────────────────┬──────────────────────────────────────────────────┘
                   │ passes
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         On-Demand: Full Verify                       │
│   npm run verify                                                     │
│   ├── npm run test:fast  (runs all fast checks above)               │
│   ├── pytest tests/python/ -m "live"  (real API calls)             │
│   └── npx playwright test             (Playwright E2E)              │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Recommended Project Structure

```
rba-hawko-meter/
├── pyproject.toml           NEW — pytest + ruff config; single source of truth
│
├── .git/hooks/
│   └── pre-push             NEW — executable shell script; calls npm run test:fast
│
├── eslint.config.js         NEW — ESLint 9 flat config for public/js/
│
├── pipeline/                EXISTING — no structural changes
│   ├── __init__.py
│   ├── config.py
│   ├── main.py
│   ├── ingest/
│   │   ├── abs_data.py
│   │   ├── rba_data.py
│   │   ├── asx_futures_scraper.py
│   │   ├── corelogic_scraper.py
│   │   └── nab_scraper.py
│   ├── normalize/
│   │   ├── engine.py
│   │   ├── ratios.py
│   │   ├── zscore.py
│   │   └── gauge.py
│   └── utils/
│       ├── csv_handler.py
│       └── http_client.py
│
├── tests/                   EXISTING Playwright tests stay at root
│   ├── CLAUDE.md
│   ├── dashboard.spec.js
│   ├── calculator.spec.js
│   └── phase6-ux.spec.js
│
├── tests/python/            NEW — all pytest tests live here
│   ├── conftest.py          NEW — shared fixtures, CSV helpers, status.json loader
│   ├── fixtures/            NEW — static fixture data (not tmp_path; version-controlled)
│   │   ├── abs_cpi_sample.csv
│   │   ├── abs_employment_sample.csv
│   │   ├── rba_cash_rate_sample.csv
│   │   └── status_sample.json
│   ├── test_zscore.py       NEW — unit tests for zscore.py
│   ├── test_ratios.py       NEW — unit tests for ratios.py
│   ├── test_gauge.py        NEW — unit tests for gauge.py
│   ├── test_csv_handler.py  NEW — unit tests for csv_handler.py
│   ├── test_status_schema.py  NEW — validates status.json contract
│   └── test_live_apis.py    NEW — marked @pytest.mark.live; real HTTP calls
│
├── data/                    EXISTING — source CSVs (not touched by tests)
├── public/                  EXISTING
│   ├── index.html
│   ├── js/
│   └── data/
│       └── status.json
├── requirements.txt         MODIFIED — add pytest, ruff, jsonschema
├── package.json             MODIFIED — add ESLint deps; expand scripts
└── .gitignore               MODIFIED — add .pytest_cache/, .ruff_cache/
```

### Structure Rationale

- **`tests/python/` as a sibling to `tests/`:** Playwright already owns `tests/*.spec.js`.
  Adding `tests/python/` keeps all tests under one tree without colliding with
  Playwright's discovery (which only collects `*.spec.js` files).

- **`pyproject.toml` at root:** Ruff and pytest both discover config from the
  project root upward. A single `pyproject.toml` replaces the need for
  `pytest.ini`, `setup.cfg`, and `.ruff.toml`. The project has no existing
  `pyproject.toml`, so this is a net-new file.

- **`tests/python/conftest.py` (not root `conftest.py`):** Root `conftest.py`
  would be visible to Playwright if Playwright ever collects Python files.
  Scoping fixtures to `tests/python/conftest.py` keeps them isolated and
  follows pytest best practice of placing fixtures closest to where they're used.

- **`tests/python/fixtures/` (static, version-controlled):** CSV fixtures
  representing minimal valid data are more readable in version control than
  `tmp_path`-generated data. `tmp_path` is used for write tests (csv_handler)
  where the test itself generates output.

- **`eslint.config.js` at root:** ESLint 9 flat config uses `eslint.config.js`
  (or `.mjs`) in the project root. This is the new required location — no
  `.eslintrc` files.

---

## Architectural Patterns

### Pattern 1: `conftest.py` as Fixture Hub

**What:** A single `tests/python/conftest.py` provides all shared fixtures.
Tests receive fixtures via dependency injection (function arguments).

**When to use:** Any fixture used by more than one test file. CSV loading,
status.json loading, tmp_path wrappers for write tests.

**Trade-offs:** Centralised but can grow large. Keep only genuinely shared
fixtures here; test-local fixtures stay in the test file itself.

**Example:**

```python
# tests/python/conftest.py
import pytest
import pandas as pd
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_cpi_df():
    """Minimal valid CPI CSV as DataFrame (2 years of monthly data)."""
    return pd.read_csv(FIXTURES_DIR / "abs_cpi_sample.csv",
                       parse_dates=["date"])


@pytest.fixture
def tmp_csv(tmp_path):
    """Factory fixture: returns a callable that writes a DataFrame to a tmp CSV.
    Use for testing csv_handler.append_to_csv() write behaviour."""
    def _write(df, filename="test.csv"):
        path = tmp_path / filename
        df.to_csv(path, index=False)
        return path
    return _write


@pytest.fixture
def status_json():
    """Load the live public/data/status.json for schema validation tests."""
    import json
    path = Path(__file__).parent.parent.parent / "public" / "data" / "status.json"
    return json.loads(path.read_text())
```

### Pattern 2: Marker-Based Test Tiers

**What:** pytest markers separate fast unit tests from slow live-API tests.
The pre-push hook runs only fast tests; `npm run verify` runs all.

**When to use:** Any test that makes a real HTTP call gets `@pytest.mark.live`.
Tests using only fixtures and no I/O get no marker (default fast tier).

**Trade-offs:** Requires `--strict-markers` in `pyproject.toml` to catch typos.
Developers must remember to apply the marker. Low discipline cost — live tests
are obvious by nature.

**Example:**

```python
# tests/python/test_live_apis.py
import pytest
import requests

@pytest.mark.live
def test_abs_api_reachable():
    """ABS SDMX API responds to a real HTTP request."""
    r = requests.get(
        "https://data.api.abs.gov.au/data/ABS,CPI/all",
        params={"startPeriod": "2024", "detail": "dataonly"},
        headers={"Accept": "application/vnd.sdmx.data+csv;labels=both"},
        timeout=30,
    )
    assert r.status_code == 200
    assert len(r.text) > 100

@pytest.mark.live
def test_rba_csv_reachable():
    """RBA statistics endpoint returns a valid CSV response."""
    r = requests.get(
        "https://www.rba.gov.au/statistics/tables/csv/a2-data.csv",
        timeout=30,
    )
    assert r.status_code == 200
    assert "Cash Rate Target" in r.text or "date" in r.text.lower()
```

### Pattern 3: Pure-Function Unit Tests for Normalization Logic

**What:** `zscore.py`, `ratios.py`, and `gauge.py` are pure functions operating
on DataFrames. They take data in, return data out, with no I/O. Test them
directly with synthetic data constructed in-memory or from fixture CSVs.

**When to use:** All normalization module functions — no mocking needed because
there are no external dependencies to isolate.

**Trade-offs:** Tests are fast and deterministic. The synthetic data must be
realistic enough to exercise edge cases (e.g., MAD=0 when all values are equal,
NaN when window is too small).

**Example:**

```python
# tests/python/test_zscore.py
import numpy as np
import pandas as pd
import pytest
from pipeline.normalize.zscore import compute_rolling_zscores, determine_confidence


def make_df(values, freq="Q"):
    """Build a minimal date/value DataFrame for zscore tests."""
    periods = len(values)
    dates = pd.date_range("2014-01-01", periods=periods, freq=freq)
    return pd.DataFrame({"date": dates, "value": values})


def test_rolling_zscore_requires_minimum_window():
    """Rows before min_quarters get NaN z_score."""
    df = make_df([1.0] * 25)  # 25 quarters
    result = compute_rolling_zscores(df, min_quarters=20)
    # First 20 rows should be NaN
    assert result["z_score"].iloc[:20].isna().all()
    # Row 21+ should have a value
    assert not result["z_score"].iloc[20:].isna().all()


def test_zero_mad_returns_zero_zscore():
    """When all window values are identical, MAD=0, zscore should be 0.0."""
    df = make_df([5.0] * 25)
    result = compute_rolling_zscores(df, min_quarters=20)
    valid = result.dropna(subset=["z_score"])
    assert (valid["z_score"] == 0.0).all()


def test_confidence_thresholds():
    assert determine_confidence(32) == "HIGH"
    assert determine_confidence(20) == "MEDIUM"
    assert determine_confidence(19) == "LOW"
    assert determine_confidence(0) == "LOW"
```

### Pattern 4: status.json Schema Validation

**What:** A dedicated test file loads `public/data/status.json` and validates
its structure against an explicit schema using `jsonschema`. This catches
contract regressions — if a pipeline change removes a field the frontend
depends on, the test fails.

**When to use:** Always run as part of `test:fast` (no HTTP calls; reads a
local file). The file is committed to git, so it always exists locally.

**Trade-offs:** The schema must be kept in sync with the frontend contract
(gauges.js, data.js). This is a one-time cost. The payoff is catching silent
contract breaks before they reach Netlify.

**Example:**

```python
# tests/python/test_status_schema.py
import json
import jsonschema
from pathlib import Path

STATUS_PATH = Path(__file__).parent.parent.parent / "public" / "data" / "status.json"

GAUGE_SCHEMA = {
    "type": "object",
    "required": ["value", "zone", "zone_label", "z_score", "raw_value",
                 "weight", "data_date", "staleness_days", "confidence",
                 "interpretation", "history"],
    "properties": {
        "value": {"type": "number", "minimum": 0, "maximum": 100},
        "zone": {"type": "string",
                 "enum": ["cold", "cool", "neutral", "warm", "hot"]},
        "z_score": {"type": "number"},
        "staleness_days": {"type": "integer", "minimum": 0},
        "confidence": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        "history": {"type": "array", "items": {"type": "number"}},
    },
}

STATUS_SCHEMA = {
    "type": "object",
    "required": ["generated_at", "pipeline_version", "overall",
                 "gauges", "weights", "metadata"],
    "properties": {
        "overall": {
            "type": "object",
            "required": ["hawk_score", "zone", "zone_label",
                         "verdict", "confidence"],
            "properties": {
                "hawk_score": {"type": "number", "minimum": 0, "maximum": 100},
            },
        },
        "gauges": {
            "type": "object",
            "minProperties": 1,
            "additionalProperties": GAUGE_SCHEMA,
        },
        "metadata": {
            "type": "object",
            "required": ["indicators_available", "indicators_missing"],
        },
    },
}


def test_status_json_exists():
    assert STATUS_PATH.exists(), "public/data/status.json must exist"


def test_status_json_valid_schema():
    data = json.loads(STATUS_PATH.read_text())
    jsonschema.validate(instance=data, schema=STATUS_SCHEMA)


def test_hawk_score_in_range():
    data = json.loads(STATUS_PATH.read_text())
    score = data["overall"]["hawk_score"]
    assert 0 <= score <= 100, f"hawk_score {score} out of range"


def test_all_gauge_values_in_range():
    data = json.loads(STATUS_PATH.read_text())
    for name, gauge in data["gauges"].items():
        assert 0 <= gauge["value"] <= 100, \
            f"gauge {name}.value={gauge['value']} out of range"
        assert gauge["staleness_days"] >= 0, \
            f"gauge {name}.staleness_days is negative"
```

---

## Data Flow: Test Execution

### Fast Tier (pre-push hook + `npm run test:fast`)

```
npm run test:fast
    │
    ├── ruff check pipeline/
    │       Reads: pipeline/**/*.py
    │       No I/O, no fixtures
    │       Exits 0 (pass) or 1 (lint errors)
    │
    ├── ruff format --check pipeline/
    │       Reads: pipeline/**/*.py
    │       No I/O
    │       Exits 0 (pass) or 1 (format violations)
    │
    ├── eslint public/js/
    │       Reads: public/js/**/*.js
    │       Uses: eslint.config.js (root)
    │       No I/O
    │       Exits 0 (pass) or 1 (lint errors)
    │
    └── pytest tests/python/ -m "not live"
            Reads: tests/python/conftest.py
                   tests/python/fixtures/*.csv
                   public/data/status.json (for schema tests)
            No HTTP calls
            Exits 0 (all pass) or 1 (any failure)
```

### Full Tier (`npm run verify`)

```
npm run verify
    │
    ├── [all fast tier steps above]
    │
    ├── pytest tests/python/ -m "live"
    │       Makes real HTTP calls to:
    │       - ABS SDMX API
    │       - RBA statistics
    │       - ASX MarkitDigital API
    │       - NAB website
    │       - CoreLogic/Cotality pages
    │       Exits 0 (all APIs reachable) or 1 (any failure)
    │
    └── npx playwright test
            Requires: python3 -m http.server 8080 (via Playwright config)
            Reads: public/data/status.json (already tested)
            Exercises: full browser rendering
```

---

## Integration Points

### New vs Existing Files

| File | Status | Purpose |
|------|--------|---------|
| `pyproject.toml` | NEW | pytest config + ruff config — single config hub |
| `.git/hooks/pre-push` | NEW | Shell script; calls `npm run test:fast`; `chmod +x` required |
| `eslint.config.js` | NEW | ESLint 9 flat config for `public/js/` |
| `tests/python/conftest.py` | NEW | Shared pytest fixtures for all Python tests |
| `tests/python/fixtures/*.csv` | NEW | Static minimal CSVs for unit test data |
| `tests/python/test_zscore.py` | NEW | Unit tests for `pipeline/normalize/zscore.py` |
| `tests/python/test_ratios.py` | NEW | Unit tests for `pipeline/normalize/ratios.py` |
| `tests/python/test_gauge.py` | NEW | Unit tests for `pipeline/normalize/gauge.py` |
| `tests/python/test_csv_handler.py` | NEW | Unit tests for `pipeline/utils/csv_handler.py` |
| `tests/python/test_status_schema.py` | NEW | Validates `public/data/status.json` contract |
| `tests/python/test_live_apis.py` | NEW | Real HTTP calls; `@pytest.mark.live` |
| `requirements.txt` | MODIFIED | Add: `pytest>=8.0`, `ruff>=0.9`, `jsonschema>=4.23` |
| `package.json` | MODIFIED | Add ESLint deps; expand `scripts` section |
| `.gitignore` | MODIFIED | Add `.pytest_cache/`, `.ruff_cache/` |
| `tests/` (existing) | UNCHANGED | Playwright `*.spec.js` tests stay as-is |
| `pipeline/` (existing) | UNCHANGED | No structural changes to production code |

### `pyproject.toml` — Configuration Hub

```toml
[tool.pytest.ini_options]
testpaths = ["tests/python"]
pythonpath = ["."]
addopts = ["--strict-markers", "-ra"]
markers = [
    "live: marks tests that make real HTTP/network calls (deselect with -m 'not live')",
]

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]
ignore = ["E501"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["S101"]
```

**Key decisions:**
- `pythonpath = ["."]` makes `pipeline.*` importable from the project root
  without editable install or `sys.path` hacks. Verified: the project root
  already contains `pipeline/__init__.py`, so `import pipeline.normalize.zscore`
  works when pytest is run from the root.
- `testpaths = ["tests/python"]` prevents pytest from accidentally collecting
  Playwright `*.spec.js` files or `.planning/` markdown.
- `--strict-markers` makes unknown marker names an error — catches typos in
  `@pytest.mark.live`.

### `package.json` — Orchestration Scripts

```json
{
  "scripts": {
    "test": "npx playwright test",
    "test:headed": "npx playwright test --headed",
    "test:fast": "ruff check pipeline/ && ruff format --check pipeline/ && eslint public/js/ && pytest tests/python/ -m 'not live'",
    "test:python": "pytest tests/python/ -m 'not live'",
    "test:python:live": "pytest tests/python/ -m live",
    "lint:py": "ruff check pipeline/",
    "lint:js": "eslint public/js/",
    "verify": "npm run test:fast && pytest tests/python/ -m live && npx playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.50.0",
    "@eslint/js": "^9.0.0",
    "eslint": "^9.0.0",
    "globals": "^16.0.0"
  }
}
```

**Key decisions:**
- `test:fast` chains with `&&` — first failure stops the chain. This is
  intentional: if lint fails, there's no point running tests.
- `ruff` and `pytest` are called directly (not `npx`) because they come from
  the Python virtualenv, not `node_modules`. This assumes the dev has activated
  their virtualenv before running npm scripts — a documented prerequisite.
- `verify` is the full gate: fast + live + Playwright. Run before releasing,
  not before every commit.

### `eslint.config.js` — Vanilla JS Flat Config

```javascript
// eslint.config.js
import js from '@eslint/js';
import globals from 'globals';

export default [
  js.configs.recommended,
  {
    files: ['public/js/**/*.js'],
    languageOptions: {
      globals: {
        ...globals.browser,
        // Project-level globals (IIFE exports used across modules)
        Plotly: 'readonly',
        Decimal: 'readonly',
      },
      ecmaVersion: 2020,
      sourceType: 'script',   // IIFE modules, not ES modules
    },
    rules: {
      'no-unused-vars': 'warn',
      'no-console': 'off',    // console.warn used for data debugging
      'no-undef': 'error',
    },
  },
  {
    ignores: ['node_modules/', 'playwright-report/', 'test-results/'],
  },
];
```

**Key decisions:**
- `sourceType: 'script'` because `public/js/*.js` are IIFE modules, not ES
  modules. Using `'module'` would cause ESLint to reject `var` declarations
  that are intentionally global-scoped for cross-file sharing.
- `Plotly` and `Decimal` declared as globals to prevent false-positive `no-undef`
  errors for CDN-loaded libraries.
- No `@typescript-eslint` or framework plugins needed — this is pure browser JS.

### `.git/hooks/pre-push` — Gate Script

```bash
#!/bin/sh
# Pre-push hook: runs fast test suite before allowing push.
# Exit code 0 = allow push. Non-zero = abort push.
# Skip with: git push --no-verify

set -e

echo "Running pre-push checks..."
npm run test:fast

echo "Pre-push checks passed."
```

**Key decisions:**
- `set -e` exits immediately on first failure — no partial pass state.
- Delegates entirely to `npm run test:fast`. Single source of truth for what
  "fast" means; changing the npm script automatically updates the hook behavior.
- The hook lives at `.git/hooks/pre-push`. It is NOT committed to the repo
  (git does not track `.git/`). Developers install it manually or via a
  setup script.
- Must be executable: `chmod +x .git/hooks/pre-push`.

### Hook Installation

Since `.git/hooks/` is not tracked, a one-line setup command is needed. Add to
`package.json` or document in README:

```bash
cp scripts/pre-push.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
```

Alternatively, store the hook source at `scripts/hooks/pre-push` (committed)
and document manual installation. This is simpler than Husky for a project with
one developer and no framework dependency.

---

## pytest Discovery: How It Works With This Structure

```
pytest tests/python/ -m "not live"
│
├── Reads pyproject.toml at project root
│   - testpaths = ["tests/python"]  (overridden by explicit path on CLI)
│   - pythonpath = ["."]  → adds /Users/annon/projects/rba-hawko-meter to sys.path
│   - markers = ["live: ..."]
│   - addopts = ["--strict-markers", "-ra"]
│
├── Discovers conftest.py at tests/python/conftest.py
│   - Registers fixtures: sample_cpi_df, tmp_csv, status_json
│   - No import of pipeline modules (fixtures are lazy)
│
├── Collects test files matching test_*.py in tests/python/
│   test_zscore.py, test_ratios.py, test_gauge.py,
│   test_csv_handler.py, test_status_schema.py
│   (test_live_apis.py collected but DESELECTED by -m "not live")
│
├── For each test function:
│   - Fixtures injected by name-matching (dependency injection)
│   - pipeline.* imports resolve via pythonpath = ["."]
│     e.g. "from pipeline.normalize.zscore import compute_rolling_zscores"
│        → /Users/annon/projects/rba-hawko-meter/pipeline/normalize/zscore.py
│
└── No __init__.py needed in tests/python/
    (prepend import mode handles flat test layout without __init__.py;
     test filenames must be globally unique — they will be)
```

---

## Anti-Patterns

### Anti-Pattern 1: Root-Level `conftest.py`

**What people do:** Place `conftest.py` at the project root to make fixtures
available everywhere.

**Why it's wrong:** A root `conftest.py` is loaded for all test collection,
including Playwright's if ever configured to collect from root. It also puts
fixtures far from the tests that use them, violating pytest's recommendation
to scope fixtures to the closest relevant directory.

**Do this instead:** `tests/python/conftest.py` scoped exactly to the pytest
test directory.

### Anti-Pattern 2: Mocking Pipeline Internals

**What people do:** Mock `pipeline.normalize.zscore.compute_rolling_zscores`
to return fake data, then test the engine.

**Why it's wrong:** The normalization functions are pure functions with no I/O.
Mocking them adds test complexity while reducing confidence — you're testing
the mock, not the code. The real functions are fast and deterministic.

**Do this instead:** Test zscore.py, ratios.py, and gauge.py directly with
synthetic DataFrames. Test engine.py via integration: construct a real CSV
in `tmp_path`, run `generate_status()`, and assert on the output JSON.

### Anti-Pattern 3: Live API Tests in the Pre-Push Hook

**What people do:** Put all tests in the pre-push hook including network calls.

**Why it's wrong:** A single slow API (ABS takes 5-10 seconds, NAB PDF
download is unpredictable) makes every push painful. Pre-push hooks that take
over 10 seconds get disabled by frustrated developers.

**Do this instead:** Marker-based separation. Pre-push runs `pytest -m "not live"`.
Live tests only run with `npm run verify` or `npm run test:python:live`.

### Anti-Pattern 4: Importing `pipeline.config` to Get File Paths in Tests

**What people do:** `from pipeline.config import DATA_DIR` in test fixtures
to load real `data/*.csv` files.

**Why it's wrong:** `DATA_DIR = Path("data")` in config.py is relative to
wherever the script runs. Tests run from the project root (correct) or from
`tests/python/` (wrong path). Also, real data CSVs are mutable — the pipeline
updates them weekly. Tests should not depend on real data state.

**Do this instead:** Use `Path(__file__).parent / "fixtures" / "abs_cpi_sample.csv"`
in conftest.py to load static fixture CSVs with known, stable content.

### Anti-Pattern 5: ESLint with `sourceType: 'module'` on IIFE Files

**What people do:** Use the default ESLint config which assumes ES modules.

**Why it's wrong:** `public/js/*.js` are IIFE modules (the project's explicit
decision: "IIFE modules: Encapsulate private state without a build system").
With `sourceType: 'module'`, ESLint would flag IIFE top-level `var` declarations
and not understand cross-file global sharing.

**Do this instead:** `sourceType: 'script'` in `eslint.config.js` with
explicit `globals` for Plotly, Decimal, and any cross-file IIFE exports.

---

## Build Order Considerations

Dependencies between new components determine sequencing:

```
Phase 1 (no external deps):
  pyproject.toml              -- needed before pytest can run
  requirements.txt update     -- needed before pytest/ruff install

Phase 2 (depends on Phase 1):
  tests/python/conftest.py    -- needed before any pytest test runs
  tests/python/fixtures/      -- needed by conftest.py fixtures

Phase 3 (depends on Phase 2):
  test_zscore.py              -- depends on conftest fixtures + zscore.py
  test_ratios.py              -- depends on conftest fixtures + ratios.py
  test_gauge.py               -- depends on conftest fixtures + gauge.py
  test_csv_handler.py         -- depends on tmp_csv fixture + csv_handler.py
  test_status_schema.py       -- depends on status_json fixture + public/data/status.json
                                 (no HTTP; status.json is committed)

Phase 4 (depends on Phase 2):
  test_live_apis.py           -- depends on conftest; marked @pytest.mark.live

Phase 5 (independent of pytest):
  eslint.config.js            -- only needs ESLint npm packages
  package.json scripts update -- can go any time after deps are known

Phase 6 (depends on all above):
  .git/hooks/pre-push         -- only useful after npm run test:fast works end-to-end
```

**Critical path:** `pyproject.toml` → `conftest.py` → unit test files → hook.

Linting (ruff + ESLint) is fully independent of the pytest chain and can be
set up in parallel with Phase 2.

---

## Sources

All findings verified against the live codebase and official documentation:

- Codebase: `/Users/annon/projects/rba-hawko-meter/` (all files read directly)
- pytest configuration: [pytest pyproject.toml configuration](https://docs.pytest.org/en/stable/reference/customize.html)
- pytest fixtures: [How to use fixtures](https://docs.pytest.org/en/stable/how-to/fixtures.html)
- pytest tmp_path: [Temporary directories and files](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- pytest discovery: [Good Integration Practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- Ruff configuration: [Configuring Ruff](https://docs.astral.sh/ruff/configuration/)
- ESLint 9 flat config: [ESLint v9 migration](https://eslint.org/docs/latest/use/migrate-to-9.0.0)
- jsonschema: [Schema Validation](https://python-jsonschema.readthedocs.io/en/stable/validate/)
- Git hooks: [Git Hooks](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks)

---

*Architecture research for: RBA Hawk-O-Meter v2.0 Local CI & Test Infrastructure*
*Researched: 2026-02-24*
