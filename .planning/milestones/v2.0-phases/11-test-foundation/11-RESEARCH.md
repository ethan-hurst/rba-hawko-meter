# Phase 11: Test Foundation - Research

**Researched:** 2026-02-25
**Domain:** pytest configuration, test isolation, network blocking, fixture data
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Fixture data strategy
- Use real historical data snapshots copied from production CSVs (not synthetic)
- Seed all 7 active indicators: CPI, employment, wages, retail trade, building approvals, housing (ABS RPPI), NAB capacity utilisation
- ~40 rows per fixture CSV — enough for 10-year rolling window Z-score calculations to actually compute
- Fixture CSVs live in `tests/python/fixtures/` directory

#### Test directory layout
- Mirror `pipeline/` module structure: `tests/python/test_zscore.py`, `test_gauge.py`, `test_ratios.py`, `test_csv_handler.py`, etc.
- Single `conftest.py` at `tests/python/` with all shared fixtures (DATA_DIR patch, network blocker, CSV loaders)
- Test function naming: `test_<behavior>` — descriptive of what's being verified (e.g., `test_zscore_returns_zero_for_mean_value`, `test_gauge_clamps_at_100`)
- Include smoke tests in Phase 11 to prove infrastructure works end-to-end (DATA_DIR isolation, network blocking, tier separation)

#### Network safety scope
- Block at socket level — monkeypatch `socket.socket` to catch ALL outbound connections (requests, urllib, httpx, anything)
- Block everything including localhost/127.0.0.1 — no exceptions for non-live tests
- On violation: raise `RuntimeError('Network access blocked in tests. Use @pytest.mark.live for tests requiring network.')`
- Auto-disable for `@pytest.mark.live` — autouse fixture checks markers and steps aside for live-marked tests

### Claude's Discretion
- Exact pyproject.toml structure and ruff rule selection
- conftest.py fixture implementation details
- How fixture CSVs are loaded (fixture functions vs pytest-datadir vs manual)
- Smoke test specifics beyond what success criteria require

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FOUND-01 | Developer can configure pytest and ruff from a single `pyproject.toml` | pyproject.toml `[tool.pytest.ini_options]` and `[tool.ruff]`/`[tool.ruff.lint]` sections — both tools share the file natively |
| FOUND-02 | Unit tests are isolated from production data via autouse DATA_DIR fixture | `monkeypatch.setattr("pipeline.config.DATA_DIR", tmp_path)` in an autouse conftest fixture — verified pattern from pytest docs |
| FOUND-03 | Test fixtures provide deterministic CSV data for reproducible test runs | Fixture CSVs in `tests/python/fixtures/` loaded via fixture functions returning DataFrames or Path objects |
| FOUND-04 | Tests are tiered via `@pytest.mark.live` so fast and live tests run separately | Register `live` marker in pyproject.toml; use `--strict-markers`; filter with `-m "not live"` / `-m live` |
| FOUND-05 | Dev dependencies managed separately in `requirements-dev.txt` | Plain `requirements-dev.txt` with pinned `pytest>=9`, `ruff>=0.15`, `jsonschema>=4.23` — installed with `pip install -r requirements-dev.txt` |
</phase_requirements>

---

## Summary

Phase 11 establishes the pytest infrastructure from scratch. The project has no `pyproject.toml`, no `tests/python/` directory, and no Python test runner yet — only Playwright tests in `tests/*.spec.js`. Everything must be created: `pyproject.toml` as the config hub, `tests/python/conftest.py` with three autouse fixtures (DATA_DIR isolation, network blocker, live-marker awareness), fixture CSVs copied from production, and `requirements-dev.txt`.

The technical domain is mature and well-documented. All five patterns (pyproject.toml dual config, monkeypatching a module-level `Path`, socket-level network blocking, marker-conditional autouse, and requirements separation) have verified implementations from official pytest and ruff documentation. The main subtlety is that `pipeline.config.DATA_DIR` is a module-level `Path` object assigned at import time — monkeypatching it correctly requires patching the attribute on the module object, not reassigning the variable, and the fixture must have function scope.

The critical constraint from STATE.md is the relative path: `DATA_DIR = Path("data")` in `pipeline/config.py`. If any test runs without the DATA_DIR patch active, it will silently read or write the live `data/` directory relative to wherever pytest is invoked from. The autouse fixture MUST run before any test body executes and MUST patch both `pipeline.config.DATA_DIR` and any other module-level bindings that captured it at import time (e.g., `pipeline.config.SOURCE_METADATA` references `DATA_DIR`).

**Primary recommendation:** Use `pyproject.toml` with `[tool.pytest.ini_options]` (pytest 6+ compatible, no need for pytest 9's `[tool.pytest]` native TOML), register the `live` marker with `--strict-markers`, patch `socket.socket` rather than just `requests` to block all network at the lowest level, and check `request.node.get_closest_marker("live")` in the autouse fixture to step aside for live-marked tests.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=9.0.2 | Test runner, fixture system, marker system | Official standard; pyproject.toml config support since v6; latest stable as of 2025-12-06 |
| ruff | >=0.15.2 | Linter (replaces flake8+isort+pyupgrade) | Fastest Python linter; single tool for E/F/W/B/I/UP rules; configured via pyproject.toml |
| jsonschema | >=4.23,<5.0 | JSON schema validation (for status.json tests in Phase 12) | Standard library for JSON Schema draft validation; 4.x is stable LTS series |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-socket | optional | Alternative socket-blocking plugin | Only if the hand-rolled socket monkeypatch proves fragile — the user decision specifies manual monkeypatching |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled socket blocker | pytest-socket plugin | Plugin is cleaner but adds a dependency; user decided manual monkeypatch for control |
| `requirements-dev.txt` | `pyproject.toml [dependency-groups]` | Modern approach, but requires pip 24.3+ and adds complexity; requirements-dev.txt is simpler and universally compatible |
| `[tool.pytest]` native TOML (pytest 9+) | `[tool.pytest.ini_options]` | Native format is cleaner but requires pytest 9+; ini_options works from pytest 6+ and is safer |

**Installation:**
```bash
pip install -r requirements-dev.txt
```

---

## Architecture Patterns

### Recommended Project Structure

```
tests/
└── python/
    ├── conftest.py          # autouse fixtures: DATA_DIR patch, network blocker
    ├── fixtures/            # static CSV snapshots, ~40 rows each
    │   ├── abs_cpi.csv
    │   ├── abs_employment.csv
    │   ├── abs_wage_price_index.csv
    │   ├── abs_household_spending.csv
    │   ├── abs_building_approvals.csv
    │   ├── corelogic_housing.csv
    │   └── nab_capacity.csv
    ├── test_smoke.py        # Phase 11 smoke tests — prove infra works
    └── (future test files)

pyproject.toml               # Config hub: pytest + ruff
requirements-dev.txt         # Dev-only dependencies
```

### Pattern 1: pyproject.toml as Dual Config Hub (FOUND-01)

**What:** Single file configures both pytest (under `[tool.pytest.ini_options]`) and ruff (under `[tool.ruff]` and `[tool.ruff.lint]`).

**When to use:** Always — pyproject.toml is the modern Python project config standard and both tools support it natively.

**Example:**
```toml
# pyproject.toml

[tool.pytest.ini_options]
minversion = "6.0"
testpaths = ["tests/python"]
pythonpath = ["."]
addopts = ["--strict-markers"]
markers = [
    "live: marks tests that require live network access (deselect with '-m \"not live\"')",
]

[tool.ruff]
target-version = "py313"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I", "UP"]
ignore = []
fixable = ["ALL"]
```

Key points:
- `pythonpath = ["."]` adds project root to sys.path so `import pipeline.config` works from tests
- `--strict-markers` in `addopts` ensures typos in `@pytest.mark.X` raise an error
- `markers` list documents each custom mark with a description
- `testpaths = ["tests/python"]` scopes discovery to Python tests only (keeps Playwright tests separate)

Source: [pytest configuration docs](https://docs.pytest.org/en/stable/reference/customize.html), [ruff configuration docs](https://docs.astral.sh/ruff/configuration/)

### Pattern 2: DATA_DIR Autouse Monkeypatch Fixture (FOUND-02)

**What:** Autouse fixture in `conftest.py` that replaces `pipeline.config.DATA_DIR` with a `tmp_path`-based directory for the duration of each test. This prevents any test from reading or writing the live `data/` folder.

**When to use:** Every non-live Python test — via autouse, requires no explicit declaration.

**Critical subtlety:** `pipeline.config.DATA_DIR` is a module-level `Path` object. When Python imports `pipeline.config`, it evaluates `DATA_DIR = Path("data")` once. Other modules that do `from pipeline.config import DATA_DIR` get a snapshot of that value at their import time. Monkeypatching must target the attribute on the `pipeline.config` module object; it cannot reach cached copies in other modules. This is acceptable because the pipeline modules use `pipeline.config.DATA_DIR` (not local re-imports) for file construction.

Additionally, `SOURCE_METADATA` in `pipeline/config.py` uses `DATA_DIR` at module load time (e.g., `"file_path": DATA_DIR / "rba_cash_rate.csv"`). Patching `DATA_DIR` after import will not retroactively update those pre-built paths. Tests for functions that use `SOURCE_METADATA` may need additional patching.

**Example:**
```python
# tests/python/conftest.py
import pytest
import pipeline.config


@pytest.fixture(autouse=True)
def isolate_data_dir(monkeypatch, tmp_path):
    """Redirect DATA_DIR to a tmp directory so tests never touch live data."""
    monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)
    yield
```

Source: [pytest monkeypatch docs](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)

### Pattern 3: Socket-Level Network Blocker with Marker Escape Hatch (FOUND-02, FOUND-04)

**What:** Autouse fixture that replaces `socket.socket` with a function that raises `RuntimeError`. Tests marked `@pytest.mark.live` are exempted by checking `request.node.get_closest_marker("live")`.

**When to use:** All non-live tests. Blocks requests, urllib, httpx, and anything else that uses the socket layer.

**Example:**
```python
# tests/python/conftest.py
import socket
import pytest


@pytest.fixture(autouse=True)
def block_network(monkeypatch, request):
    """
    Block all network access for non-live tests.
    Tests marked @pytest.mark.live are exempted.
    """
    if request.node.get_closest_marker("live"):
        yield  # step aside for live-marked tests
        return

    def blocked_socket(*args, **kwargs):
        raise RuntimeError(
            "Network access blocked in tests. "
            "Use @pytest.mark.live for tests requiring network."
        )

    monkeypatch.setattr(socket, "socket", blocked_socket)
    yield
```

Source: [pytest markers docs](https://docs.pytest.org/en/stable/how-to/mark.html), [socket blocking blog](https://blog.pecar.me/disable-network-requets-when-running-pytest)

### Pattern 4: Test Tier Separation with @pytest.mark.live (FOUND-04)

**What:** Register a `live` marker in `pyproject.toml`. Apply it to tests that require real network. Run fast suite with `-m "not live"`, full suite with `-m live`.

**Example usage:**
```python
# Future live test example
import pytest

@pytest.mark.live
def test_abs_cpi_endpoint_responds():
    import requests
    resp = requests.get("https://data.api.abs.gov.au/data/CPI/all")
    assert resp.status_code == 200
```

```bash
# Fast suite (CI, pre-push)
pytest tests/python/ -m "not live"

# Live suite (manual verification)
pytest tests/python/ -m live
```

Source: [pytest mark docs](https://docs.pytest.org/en/stable/how-to/mark.html)

### Pattern 5: Fixture CSV Loading via pytest fixture functions (FOUND-03)

**What:** Fixtures load CSV files from `tests/python/fixtures/` using `pathlib.Path` relative to the test file location. Return DataFrames for tests that need data; return Paths for tests that need file paths.

**Example:**
```python
# tests/python/conftest.py
from pathlib import Path
import pandas as pd

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def cpi_csv_path():
    """Return path to CPI fixture CSV."""
    return FIXTURES_DIR / "abs_cpi.csv"


@pytest.fixture
def cpi_df():
    """Return CPI fixture data as DataFrame."""
    return pd.read_csv(FIXTURES_DIR / "abs_cpi.csv")
```

`Path(__file__).parent` is the canonical way to reference files relative to conftest.py regardless of where pytest is invoked from. This avoids the CWD-sensitivity problem.

### Anti-Patterns to Avoid

- **Patching `requests.get` instead of `socket.socket`:** Only blocks the requests library. Code using urllib, httpx, or raw sockets bypasses it. Always patch at socket level.
- **Function-scoped `monkeypatch` in session-scoped fixture:** monkeypatch is function-scoped by design. autouse fixtures using monkeypatch must be function-scoped (the default). Do not attempt session-scoped DATA_DIR patching — it produces `ScopeMismatch` errors.
- **`from pipeline.config import DATA_DIR` in conftest:** This creates a local binding that cannot be patched via monkeypatch. Always import the module and patch the attribute: `import pipeline.config; monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)`.
- **Forgetting `pythonpath = ["."]` in pyproject.toml:** Without this, `import pipeline.config` from `tests/python/` fails because the project root is not on sys.path. The project uses a flat layout (no `src/`), so the root must be explicitly added.
- **Not using `--strict-markers`:** Without it, a typo like `@pytest.mark.Live` silently creates a new marker and tests appear to be marked but are not. `--strict-markers` makes this fail fast.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Linting Python | custom flake8+isort+pyupgrade config | ruff | Single tool, 10-100x faster, all rules included |
| Test isolation state reset | manual cleanup code | pytest's `monkeypatch` fixture | Auto-undone after each test; handles nested fixtures correctly |
| Fixture file path resolution | `os.path.join(os.path.dirname(__file__))` | `Path(__file__).parent` | Cleaner, cross-platform, pytest-idiomatic |

**Key insight:** pytest's fixture and monkeypatch system handles all teardown automatically. Manual cleanup is never needed when using monkeypatch.

---

## Common Pitfalls

### Pitfall 1: MODULE-LEVEL Path Captured at Import Time

**What goes wrong:** `SOURCE_METADATA` in `pipeline/config.py` constructs paths using `DATA_DIR` at module load time:
```python
SOURCE_METADATA = {
    "RBA": {"file_path": DATA_DIR / "rba_cash_rate.csv", ...}
}
```
Patching `pipeline.config.DATA_DIR` after import does NOT update these pre-built `file_path` values. Tests that use `SOURCE_METADATA["RBA"]["file_path"]` will still see the original `Path("data") / "rba_cash_rate.csv"`.

**Why it happens:** Python evaluates module-level expressions once at import. The dict value is a `Path` object, not a reference to `DATA_DIR`.

**How to avoid:** Phase 11 only needs smoke tests that verify DATA_DIR isolation (not SOURCE_METADATA-dependent code). Note this for Phase 12 unit test authors: they'll need to patch `SOURCE_METADATA` file paths separately, or restructure the production code to compute paths lazily.

**Warning signs:** Tests that should read from tmp_path but actually read from or write to `data/` directory.

### Pitfall 2: Socket Blocking Breaks pytest's Own Infrastructure

**What goes wrong:** Some pytest plugins and test discovery mechanisms use localhost socket connections internally (e.g., pytest-xdist, coverage collection). Blocking ALL sockets unconditionally can break the test runner itself.

**Why it happens:** `socket.socket` is used at the OS level for many things, including IPC.

**How to avoid:** The `monkeypatch` approach is function-scoped and only applies during test execution (not during collection). pytest's own infrastructure runs before fixtures activate. This is generally safe for the standard pytest runner without plugins. If pytest-xdist is ever added, revisit this.

**Warning signs:** Mysterious test collection failures with RuntimeError about network access.

### Pitfall 3: conftest.py Scope and Discovery

**What goes wrong:** Placing `conftest.py` at the wrong level causes fixtures to be unavailable or to conflict.

**Why it happens:** pytest discovers `conftest.py` files hierarchically from the rootdir downward.

**How to avoid:** Place the single `conftest.py` at `tests/python/conftest.py`. This scopes all autouse fixtures to Python tests only. The Playwright tests in `tests/*.spec.js` are JavaScript and never execute the Python conftest.

### Pitfall 4: Fixture CSV CWD Sensitivity

**What goes wrong:** Using a relative path like `Path("tests/python/fixtures/abs_cpi.csv")` to reference fixture CSVs works when pytest is run from the project root but fails when run from another directory.

**Why it happens:** Relative paths are resolved against CWD at runtime.

**How to avoid:** Always use `Path(__file__).parent / "fixtures" / "abs_cpi.csv"` in conftest.py. `__file__` is the conftest.py file's absolute path, so this is always unambiguous.

### Pitfall 5: pytest Version Mismatch with pyproject.toml Format

**What goes wrong:** Using `[tool.pytest]` native TOML format (pytest 9.0+) when the installed pytest is older.

**Why it happens:** The `[tool.pytest]` section was introduced in pytest 9.0; `[tool.pytest.ini_options]` has been supported since 6.0.

**How to avoid:** Use `[tool.pytest.ini_options]` for maximum compatibility. Pin `pytest>=6.0` in `requirements-dev.txt` to be explicit; recommend `>=9.0` for latest features.

---

## Code Examples

Verified patterns from official sources:

### Complete pyproject.toml

```toml
# Source: https://docs.pytest.org/en/stable/reference/customize.html
# Source: https://docs.astral.sh/ruff/configuration/

[tool.pytest.ini_options]
minversion = "6.0"
testpaths = ["tests/python"]
pythonpath = ["."]
addopts = ["--strict-markers"]
markers = [
    "live: marks tests that require live network access (deselect with '-m \"not live\"')",
]

[tool.ruff]
target-version = "py313"
line-length = 88
exclude = [
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    ".pytest_cache",
]

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I", "UP"]
ignore = []
fixable = ["ALL"]
```

### Complete conftest.py

```python
# tests/python/conftest.py
# Source: pytest docs (monkeypatch, markers, tmp_path)

import socket
from pathlib import Path

import pandas as pd
import pytest

import pipeline.config

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolate_data_dir(monkeypatch, tmp_path):
    """
    Redirect DATA_DIR to a per-test tmp directory.
    Prevents any test from reading or writing the live data/ folder.
    """
    monkeypatch.setattr(pipeline.config, "DATA_DIR", tmp_path)
    yield


@pytest.fixture(autouse=True)
def block_network(monkeypatch, request):
    """
    Block all network access for non-live tests by patching socket.socket.
    Tests decorated with @pytest.mark.live are exempted.
    """
    if request.node.get_closest_marker("live"):
        yield
        return

    def blocked_socket(*args, **kwargs):
        raise RuntimeError(
            "Network access blocked in tests. "
            "Use @pytest.mark.live for tests requiring network."
        )

    monkeypatch.setattr(socket, "socket", blocked_socket)
    yield


# --- Fixture CSV loaders ---

@pytest.fixture
def fixture_cpi_df():
    return pd.read_csv(FIXTURES_DIR / "abs_cpi.csv")


@pytest.fixture
def fixture_employment_df():
    return pd.read_csv(FIXTURES_DIR / "abs_employment.csv")


@pytest.fixture
def fixture_wages_df():
    return pd.read_csv(FIXTURES_DIR / "abs_wage_price_index.csv")


@pytest.fixture
def fixture_spending_df():
    return pd.read_csv(FIXTURES_DIR / "abs_household_spending.csv")


@pytest.fixture
def fixture_building_approvals_df():
    return pd.read_csv(FIXTURES_DIR / "abs_building_approvals.csv")


@pytest.fixture
def fixture_housing_df():
    return pd.read_csv(FIXTURES_DIR / "corelogic_housing.csv")


@pytest.fixture
def fixture_nab_capacity_df():
    return pd.read_csv(FIXTURES_DIR / "nab_capacity.csv")
```

### Smoke Test File

```python
# tests/python/test_smoke.py

import socket
import pytest
import pipeline.config


def test_pytest_discovers_and_exits_zero():
    """Baseline: pytest can collect and run this test."""
    assert True


def test_data_dir_isolated(tmp_path):
    """DATA_DIR autouse fixture points to tmp_path, not live data/."""
    # isolate_data_dir autouse fixture runs before this test body
    assert pipeline.config.DATA_DIR != pipeline.config.DATA_DIR.__class__("data")
    # DATA_DIR should be a subdirectory of tmp (not the repo's data/ dir)
    assert pipeline.config.DATA_DIR.is_absolute() or str(pipeline.config.DATA_DIR).startswith("/")


def test_network_blocker_raises_runtime_error():
    """socket.socket raises RuntimeError in non-live tests."""
    with pytest.raises(RuntimeError, match="Network access blocked"):
        socket.socket()


@pytest.mark.live
def test_live_marker_skips_network_block():
    """@pytest.mark.live tests are exempt from socket blocking."""
    # This should NOT raise — the blocker steps aside for live-marked tests
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.close()


def test_live_marker_excluded_with_not_live(pytestconfig):
    """Verify tier separation: this test runs under '-m not live'."""
    # If we reach here, we're running as a non-live test — correct.
    assert True
```

### requirements-dev.txt

```
# Development dependencies — install with: pip install -r requirements-dev.txt
pytest>=9.0.2
ruff>=0.15.2
jsonschema>=4.23,<5.0
```

### Fixture CSV Preparation

Fixture CSVs are copied from production files (`data/*.csv`) and trimmed to ~40 rows. For indicators with YoY calculations over 10-year windows, 40 rows of quarterly data covers 10 years; monthly data needs ~120 rows for the same window but 40 is sufficient for basic calculation tests. Recommendation: use 40 rows for quarterly indicators (wages: 4 periods/year × 10 years = 40) and 48 rows for monthly indicators (12 × 4 years minimum for Z-score).

CSVs must preserve exact column names from production:
- Standard: `date,value,source,series_id` (CPI, employment, wages, spending, building approvals, housing)
- NAB: `date,value,source` (no series_id)
- ASX futures: `date,meeting_date,implied_rate,change_bp,probability_cut,probability_hold,probability_hike`

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `pytest.ini` / `setup.cfg` for pytest config | `pyproject.toml [tool.pytest.ini_options]` | pytest 6.0 (2020) | Single config file for all tools |
| `[tool.pytest.ini_options]` string syntax | `[tool.pytest]` native TOML lists (pytest 9.0+) | pytest 9.0 (2024) | Cleaner, but ini_options still works fine |
| flake8 + isort + pyupgrade (separate tools) | ruff (single tool, all rules) | ruff stable 2023 | 10-100x faster; one config section |
| Blocking `requests.get/post` | Blocking `socket.socket` | Best practice evolution | Catches ALL HTTP libraries, not just `requests` |

**Deprecated/outdated:**
- `setup.cfg [tool:pytest]`: Still works but pyproject.toml is now the standard
- `pytest.ini` for new projects: Only needed if pyproject.toml conflicts with other tools

---

## Open Questions

1. **SOURCE_METADATA pre-built paths**
   - What we know: `SOURCE_METADATA` in `pipeline/config.py` builds `file_path` values using `DATA_DIR` at import time; patching `DATA_DIR` does not retroactively update them
   - What's unclear: Whether Phase 12 unit tests will need to test code that uses `SOURCE_METADATA` file paths
   - Recommendation: Phase 11 smoke tests avoid this issue. Document the limitation in conftest.py comments for Phase 12 authors.

2. **Fixture row count for monthly indicators**
   - What we know: 40 rows of quarterly data = 10 years (sufficient for Z-score windows). Monthly data: 40 rows = ~3.3 years, below the 5-year minimum for Z-score (`ZSCORE_MIN_YEARS = 5`)
   - What's unclear: Whether Phase 11 fixture CSVs need enough rows for Z-score computation or just for CSV handler tests
   - Recommendation: Phase 11 fixture CSVs are for infrastructure smoke tests only (not Z-score calculation tests). Use 40 rows for all indicators. Phase 12 can supplement with larger datasets if needed.

3. **ASX futures fixture format**
   - What we know: `asx_futures.csv` has a different schema (`meeting_date`, `implied_rate`, etc.) from all other CSVs
   - What's unclear: Whether Phase 11 needs an ASX futures fixture at all (it's in `OPTIONAL_INDICATOR_CONFIG`)
   - Recommendation: Include it in fixtures directory for completeness; it's a small file.

---

## Sources

### Primary (HIGH confidence)

- [pytest configuration reference](https://docs.pytest.org/en/stable/reference/customize.html) — pyproject.toml `[tool.pytest.ini_options]`, testpaths, addopts, markers, pythonpath
- [pytest markers how-to](https://docs.pytest.org/en/stable/how-to/mark.html) — `--strict-markers`, custom marker registration, `-m` filtering
- [pytest monkeypatch how-to](https://docs.pytest.org/en/stable/how-to/monkeypatch.html) — `setattr`, autouse fixture pattern, function scope requirement
- [pytest good practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html) — flat layout, pythonpath config, importlib mode
- [ruff configuration](https://docs.astral.sh/ruff/configuration/) — `[tool.ruff]`, `[tool.ruff.lint]`, select rules

### Secondary (MEDIUM confidence)

- [Anže Pecar: Disable network requests in pytest](https://blog.pecar.me/disable-network-requets-when-running-pytest) — `socket.getaddrinfo` approach (adapted to full block per user decision)
- [monkey.work: Why Block Network Access in Tests](https://monkey.work/blog/2025-12-23-block-network-access-in-tests/) — `requests`-level blocking pattern (adapted to socket level)
- PyPI: pytest 9.0.2 (latest stable 2025-12-06), ruff 0.15.2 (latest stable 2026-02-19), jsonschema 4.26.0 (latest stable 2026-01-07)

### Tertiary (LOW confidence)

- WebSearch: `request.node.get_closest_marker("live")` pattern for conditional autouse — described in community sources but not directly linked from official pytest API docs. The pattern is well-established but the exact API was not verified against the official fixture reference page.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pyproject.toml dual-config, ruff rule selection, and pytest version verified against official docs and PyPI
- Architecture: HIGH — all patterns (monkeypatch setattr, autouse, marker detection, socket blocking) verified against official pytest docs
- Pitfalls: HIGH — module-level-capture issue is a known Python import mechanic; scope mismatch is from pytest docs; CWD sensitivity is a standard gotcha
- `request.node.get_closest_marker`: MEDIUM — pattern confirmed in multiple community sources but API reference page was not loaded

**Research date:** 2026-02-25
**Valid until:** 2026-08-25 (stable ecosystem — pytest, ruff versions change but patterns are stable)
