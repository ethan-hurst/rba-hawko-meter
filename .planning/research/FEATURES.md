# Feature Research

**Domain:** Local CI and test infrastructure — Python+vanilla JS automated economic dashboard
**Researched:** 2026-02-24
**Confidence:** HIGH (patterns verified against official pytest/ruff/ESLint docs and live codebase)

---

## Context: What This Milestone Is Adding

The v1.1 milestone completed the data pipeline (scrapers for CoreLogic, NAB, ASX). This new milestone adds
**developer-facing quality infrastructure** to a project that currently has:

- 24 Playwright E2E tests (`npm test` → 3 suites: calculator, dashboard, UX)
- 2 GitHub Actions workflows (daily ASX + weekly full pipeline)
- Python pipeline across `pipeline/ingest/`, `pipeline/normalize/`, `pipeline/utils/`
- No Python unit tests, no linting, no pre-push hooks, no data validation

The codebase is Python + vanilla JS (no React/Next.js, no Django/Flask). Test infrastructure must fit
that stack specifically.

---

## Feature Landscape

### Table Stakes (Developers Expect These)

Features that are non-negotiable for a project claiming to have a CI pipeline. Missing these = CI
feels incomplete or untrustworthy.

#### Python Unit Tests (pytest)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **pytest test discovery via `pyproject.toml`** | Standard: running `pytest` from project root should find all Python tests without arguments | LOW | Set `testpaths = ["tests/python"]` in `[tool.pytest.ini_options]`. Keeps Python tests separate from Playwright's `tests/` JS files. No collision risk with existing JS test dir. |
| **Pure function unit tests for `zscore.py` and `gauge.py`** | These modules are pure math — `calculate_mad()`, `robust_zscore()`, `zscore_to_gauge()`, `classify_zone()`, `compute_hawk_score()` — the highest-value unit test targets in the codebase | LOW | No fixtures needed. Input array → assert output value. Each function has well-defined edge cases: empty window, MAD=0, NaN propagation, clamp boundaries at 0 and 100. |
| **Unit tests for `csv_handler.py` dedup logic** | `append_to_csv()` contains critical deduplication logic: existing file, no file, duplicate rows on date column. Bugs here silently corrupt data CSVs. | MEDIUM | Use `tmp_path` built-in pytest fixture — no temp dir management needed. Test: new file creation, append with dedup, sort order preserved. |
| **Unit tests for `ratios.py` normalization** | `yoy_pct_change` and `direct` normalization paths are the contract between raw CSV data and the Z-score engine. Edge cases include sparse data, quarterly cadence, fewer rows than yoy_periods. | MEDIUM | Use minimal synthetic DataFrames. No file I/O needed — functions accept DataFrames directly. |
| **Test isolation — no real file I/O or network in fast tests** | Unit tests must run offline and without touching `data/` CSVs or external APIs | LOW | Use `monkeypatch` and `tmp_path` fixtures for file operations. Use `mocker.patch` for any `requests` calls that leak through. An `autouse=True` fixture in `conftest.py` that patches `requests.get` to raise `RuntimeError` enforces this globally. |

#### Python Linting (ruff)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **`ruff check` on all pipeline Python** | Catch unused imports, undefined names (F-rules), and bugbear issues (B-rules) before they reach CI | LOW | Single binary, zero config dependencies. `ruff check pipeline/` from project root. Configure in `pyproject.toml` under `[tool.ruff]`. |
| **`ruff format --check` for code style** | Consistent formatting across a solo project prevents diff noise and keeps scraper code readable | LOW | Replaces Black. `ruff format --check pipeline/` in CI mode. Use `ruff format pipeline/` locally to auto-fix. |
| **`pyproject.toml` as the single config file** | Project already has `requirements.txt` but no `pyproject.toml`. Adding one consolidates pytest + ruff config in one place. | LOW | No `setup.py`, no `setup.cfg`, no `.flake8`. Single file. Target Python 3.11 (matches GitHub Actions config). |

#### JS Linting (ESLint)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **ESLint with flat config (`eslint.config.js`)** | ESLint v10 (released Feb 2026) removed the legacy `.eslintrc` format entirely. Any new ESLint setup must use flat config. The project has 3 vanilla JS source files in `public/js/`. | LOW | `npm install --save-dev eslint @eslint/js`. Create `eslint.config.js` with `js.configs.recommended`. No framework plugins needed — vanilla JS only. Run via `npx eslint public/js/`. |
| **ESLint scoped to `public/js/` only** | Playwright test files in `tests/` use CommonJS `require()` and Node-specific patterns (not browser JS). ESLint config should exclude `tests/` and `node_modules/`. | LOW | Flat config `files: ["public/js/**/*.js"]` glob targets only dashboard JS. `tests/*.spec.js` excluded by default or via explicit ignore. |
| **`npm run lint` script** | Developers expect `npm run lint` to exist alongside `npm test`. Discoverability matters. | LOW | Add to `package.json` scripts: `"lint": "eslint public/js/"`. One command, no flags required. |

#### Pre-Push Git Hook

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **`pre-push` hook that runs fast tests + linting** | Prevents broken code from reaching remote. The most common expectation for a CI-capable project. | LOW | Shell script at `.git/hooks/pre-push`. Not version-controlled by default — install via a `scripts/setup-hooks.sh` that copies the hook and `chmod +x`. |
| **Fast-tier only in pre-push (not Playwright)** | Playwright E2E takes 30+ seconds (needs webserver). Pre-push should complete in under 10 seconds. | LOW | Pre-push runs: `ruff check pipeline/`, `ruff format --check pipeline/`, `npx eslint public/js/`, `pytest tests/python/ -m "not live"`. Playwright (`npm test`) runs only in GitHub Actions, not pre-push. |
| **`--no-verify` escape hatch documented** | Developers need to know they can bypass the hook in emergencies. | LOW | Add comment at top of pre-push script: "Skip with: git push --no-verify". |

#### Data Validation (status.json contract)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **JSON schema validation of `public/data/status.json`** | The pipeline writes `status.json` and the frontend reads it. A malformed `status.json` silently breaks the dashboard. Schema validation catches pipeline output regressions. | MEDIUM | Use `jsonschema` Python library. Define a schema covering: `generated_at` (string), `overall.hawk_score` (0-100 number), `gauges` (object with known keys), `asx_futures` (object or null). Run as a pytest test against the actual `status.json` file. |
| **Gauge range assertions (0-100, no NaN in production)** | Gauge values outside 0-100 or NaN values in `status.json` are silent bugs that corrupt the dashboard display. | LOW | A single pytest parametrized test: for each gauge in `status.json`, assert `0 <= value <= 100` and `value is not None`. Uses the real `status.json` file from `public/data/`. |

---

### Differentiators (Competitive Advantage)

Features that make the CI infrastructure more robust than the minimum. Not required, but valuable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Two-tier test execution (`fast` vs `full`)** | Separate fast pytest run (pure unit tests, <5s) from full run (includes data validation against real status.json). Enables quick local feedback without waiting for validation tests that need real pipeline output. | LOW | Use pytest markers: `@pytest.mark.unit` (pure math, no I/O) vs unmarked tests. `pytest -m unit` = fast tier. `pytest` = full tier. Register markers in `pyproject.toml` to suppress warnings. |
| **`@pytest.mark.live` for opt-in API verification** | The MarkitDigital ASX endpoint and ABS SDMX API are confirmed live. A smoke test that actually hits these endpoints gives confidence before a major push. Should be opt-in, not part of the pre-push hook. | MEDIUM | Mark with `@pytest.mark.live`. Run via `pytest -m live` manually or in a separate GitHub Actions job. Separate from unit tests — avoids network dependency in fast tier. Skips gracefully if network is unavailable using `pytest.mark.skipif` + a connectivity fixture. |
| **`conftest.py` with reusable fixtures for pipeline modules** | Pipeline functions depend on `config.py` constants (`DATA_DIR`, `ZSCORE_WINDOW_YEARS`, etc.). A shared conftest fixture that provides a temporary `DATA_DIR` pointing at `tmp_path` prevents tests from writing to real `data/`. | LOW | Root-level `tests/python/conftest.py` with `@pytest.fixture(autouse=True) def isolate_data_dir(tmp_path, monkeypatch)` patches `pipeline.config.DATA_DIR`. All tests that import pipeline modules get isolation automatically. |
| **Ruff isort integration (`I` rule set)** | Import ordering is already inconsistent across scraper files. Ruff's `I` rule set replaces isort and auto-fixes on `ruff format`. Prevents future diff noise from import reordering. | LOW | Add `"I"` to `[tool.ruff.lint] select`. Run `ruff check --fix pipeline/` once to bulk-fix existing violations. |
| **`npm run check` composite script** | Combines `npm run lint` + any future type-checking into one command that matches what CI runs. | LOW | `"check": "npm run lint"` now; extendable later. Makes developer mental model match CI exactly. |

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem like good CI additions but create problems in this specific context.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **`pre-commit` framework (via PyPI)** | Manages multi-language hooks in a version-controlled `.pre-commit-config.yaml`. Popular in Python ecosystem. | Adds a separate install step (`pip install pre-commit && pre-commit install`). Developers forget to install it after cloning. Since this is a solo project, the overhead of pre-commit's framework outweighs its benefits. | Simple `.git/hooks/pre-push` shell script copied by `scripts/setup-hooks.sh`. Explicit, no extra install, no framework dependency. |
| **Playwright tests in pre-push hook** | Would catch E2E regressions before any push, not just in CI | Playwright tests take 30-90 seconds (webserver spin-up + 24 test cases). Pre-push hook must be under 10 seconds or developers bypass with `--no-verify`. E2E tests already run in GitHub Actions on every push — running them pre-push is redundant. | Keep Playwright in GitHub Actions only. Pre-push runs only: ruff + ESLint + pytest fast tier. |
| **mypy or pyright type checking** | Would catch type errors in the pipeline's type-annotated functions | The pipeline uses few explicit type annotations (only `fetch_and_save() -> Dict[...]` return types on scrapers). Running mypy on unannotated code produces noise without value. Adding annotations project-wide is a large undertaking. | Ruff's `UP` rules modernize syntax without requiring full annotation. If type safety becomes a priority, annotate incrementally and add mypy then. |
| **Coverage enforcement (pytest-cov with minimum %)** | Encourages thorough testing | Coverage % is a vanity metric for a solo project. Chasing 80% coverage forces tests for boilerplate that provides no insight. The pipeline has scraper code that is genuinely hard to unit test without live external dependencies. | Write tests for the pure functions (zscore, gauge, csv_handler). Scraper integration code is better covered by the existing Playwright E2E + live marker tests. |
| **Jest/Vitest for vanilla JS unit tests** | React/Node ecosystems use Jest as standard. | The JS codebase has 3 source files with no module exports — all logic is driven by DOM manipulation on a static page. There are no pure functions to unit test independently of the browser. Playwright already covers JS behavior end-to-end. | Continue with Playwright for all JS testing. Add ESLint to catch JS errors statically. No need for Jest. |
| **VCR.py / cassette recording for HTTP mocking** | Record real HTTP interactions once, replay without network | Cassettes go stale when APIs change (the MarkitDigital and ABS APIs both evolve). Stale cassettes pass tests against outdated API contracts. | Use `pytest-mock` / `unittest.mock` for unit tests (simple mock responses). Use `@pytest.mark.live` for real API verification when you actually need to confirm the live contract. |
| **`tox` for multi-environment testing** | Tests across Python 3.9, 3.10, 3.11, 3.12 | GitHub Actions already pins Python 3.11. This is a single-environment project — there is no support matrix to test. Tox adds complexity (`.tox/` venvs, `tox.ini`) with zero benefit. | Pin `requires-python = ">=3.11"` in `pyproject.toml`. Test once, in the environment that deploys. |

---

## Feature Dependencies

```
[pyproject.toml]
    └──enables──> [pytest configuration: testpaths, markers, addopts]
    └──enables──> [ruff configuration: select, ignore, target-version]
    (single file replaces: pytest.ini + .flake8 + setup.cfg)

[tests/python/conftest.py]
    └──provides──> [tmp_path-based DATA_DIR isolation fixture]
                       └──required by──> [csv_handler tests]
                       └──required by──> [ratios.py tests]
    └──provides──> [autouse network guard fixture]
                       └──required by──> [all unit tests — prevents accidental live calls]

[pytest unit tests — zscore.py, gauge.py]
    └──no dependencies──> [run offline, no fixtures, pure math]
    └──fastest to write, highest value]

[pytest unit tests — csv_handler.py, ratios.py]
    └──requires──> [conftest.py tmp_path fixture]
    └──medium complexity]

[status.json schema validation test]
    └──requires──> [real public/data/status.json exists]
    └──requires──> [jsonschema pip dependency]
    └──NOT in @pytest.mark.unit tier — depends on real pipeline output]

[@pytest.mark.live tests]
    └──requires──> [network connectivity]
    └──opt-in only, not run in pre-push hook]
    └──validates: MarkitDigital API, ABS SDMX API response shapes]

[.git/hooks/pre-push]
    └──requires──> [ruff installed in venv]
    └──requires──> [eslint installed in node_modules]
    └──requires──> [pytest installed with tests/python/ present]
    └──installed via──> [scripts/setup-hooks.sh]
    └──runs: ruff check + ruff format --check + eslint + pytest -m "not live"]

[eslint.config.js]
    └──requires──> [eslint @eslint/js installed]
    └──targets──> [public/js/ only — NOT tests/*.spec.js]
    └──no framework plugins needed — vanilla JS]
```

### Dependency Notes

- **`pyproject.toml` is the foundation:** Everything else depends on it existing. Create it first, populate pytest + ruff config sections before writing any tests.
- **`conftest.py` DATA_DIR isolation is load-bearing:** Tests for `csv_handler.py` and `ratios.py` will corrupt real data files without it. Must be in place before those tests are written.
- **Schema validation test is not in the unit tier:** It reads `public/data/status.json` which only exists after running the pipeline. Runs in the default `pytest` (full) tier, not `pytest -m unit`.
- **`@pytest.mark.live` tests are fully independent:** Can be added in any phase, have no dependencies on the other features.
- **ESLint is independent of all Python tooling:** Can be installed and configured before or after pytest work. No cross-dependencies.

---

## MVP Definition

### Launch With (This Milestone)

Minimum needed to say "this project has local CI infrastructure."

- [ ] **`pyproject.toml` with pytest + ruff config** — Foundation. Without it, pytest finds no tests and ruff has no target-version. One file, five minutes of setup.
- [ ] **pytest unit tests for `zscore.py` and `gauge.py`** — Highest value, lowest cost. Pure math functions with zero external dependencies. These are the mathematical core of the hawk score — regressions here are catastrophic.
- [ ] **`ruff check` + `ruff format --check` on `pipeline/`** — Enforces code quality on all current and future scraper code. Catches import errors and style violations before they accumulate.
- [ ] **ESLint flat config for `public/js/`** — Catches JS errors in dashboard source. ESLint v10 is the required format; set it up correctly from the start.
- [ ] **`.git/hooks/pre-push` installed via `scripts/setup-hooks.sh`** — Makes the fast test + lint gate automatic without requiring developers to remember to run checks.

### Add After Core Tests Are Green (Later in Milestone)

- [ ] **pytest tests for `csv_handler.py`** — Important but lower priority than zscore/gauge. Requires `conftest.py` with `tmp_path` isolation first.
- [ ] **pytest tests for `ratios.py` normalization** — Medium complexity. Add after csv_handler tests confirm the `conftest.py` pattern works.
- [ ] **`status.json` JSON schema validation test** — Useful regression guard, but requires a real pipeline run to produce the file. Add after the unit tests are stable.
- [ ] **`@pytest.mark.live` API health-check tests** — Nice-to-have for confirming live endpoints. Add last; opt-in only.

### Future Consideration (Not This Milestone)

- [ ] **Annotate pipeline Python with type hints** — Prerequisite for mypy. Current code has minimal annotations. Worthwhile eventually, but a substantial effort.
- [ ] **Playwright tests in GitHub Actions on PR** — Currently only runs manually with `npm test`. Setting up a GHA job for Playwright requires display/browser setup. Separate milestone.

---

## Feature Prioritization Matrix

| Feature | Developer Value | Implementation Cost | Priority |
|---------|-----------------|---------------------|----------|
| `pyproject.toml` (pytest + ruff config) | HIGH — enables everything else | LOW — one file | P1 |
| pytest unit tests: zscore.py + gauge.py | HIGH — guards mathematical core | LOW — pure functions, no fixtures | P1 |
| `ruff check` + `ruff format --check` | HIGH — enforces code quality on all scraper code | LOW — single binary | P1 |
| ESLint flat config for public/js/ | MEDIUM — catches JS errors | LOW — 3 source files, no framework | P1 |
| Pre-push hook via setup-hooks.sh | HIGH — makes checks automatic | LOW — shell script | P1 |
| conftest.py DATA_DIR isolation | HIGH — prerequisite for file-touching tests | LOW — monkeypatch pattern | P2 |
| pytest tests: csv_handler.py | MEDIUM — guards dedup logic | MEDIUM — needs tmp_path fixtures | P2 |
| pytest tests: ratios.py | MEDIUM — guards normalization | MEDIUM — needs synthetic DataFrames | P2 |
| status.json schema validation | MEDIUM — guards frontend contract | MEDIUM — needs jsonschema, real file | P2 |
| Two-tier markers (unit vs full) | LOW — nice organisation | LOW — just marker registration | P2 |
| @pytest.mark.live API tests | LOW — opt-in confidence check | LOW — simple requests + assertions | P3 |

**Priority key:**
- P1: Must have for milestone to be "done"
- P2: Should have, add within this milestone
- P3: Nice to have, can slip to next milestone

---

## Implementation Patterns

### Pattern 1: pytest Discovery Configuration

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests/python"]
addopts = "-ra -q"
markers = [
    "unit: pure unit tests — no I/O, no network (fast)",
    "live: tests that make real network calls (opt-in only)",
]
```

Why `tests/python/` and not `tests/`? The existing `tests/` directory contains Playwright `.spec.js` files. Pointing pytest at `tests/` causes it to discover JS files and error. Separate directories prevent collision.

### Pattern 2: ruff Configuration for This Codebase

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"   # matches GitHub Actions python-version: '3.11'
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "W", "B", "I", "UP"]
ignore = ["E501"]           # line length handled by formatter
per-file-ignores = {"pipeline/__init__.py" = ["F401"]}

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

Rules selected: `E/F/W` (pycodestyle + pyflakes, core), `B` (bugbear, catches real bugs), `I` (isort, fixes import order), `UP` (pyupgrade, modernizes Python syntax). Avoids `N` (naming conventions would require renaming existing config constants).

### Pattern 3: ESLint Flat Config (Vanilla JS, ESLint v10)

```js
// eslint.config.js
import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    files: ["public/js/**/*.js"],
    rules: {
      "no-unused-vars": "warn",
      "no-console": "off",   // dashboard uses console.log for debug output
    }
  }
];
```

Note: ESLint v10 removed `.eslintrc` format entirely. The `eslint.config.js` flat config is the only valid format. Running `npx eslint --init` generates a starting point, then narrow it to `public/js/`.

### Pattern 4: Pre-Push Hook Structure

```bash
#!/bin/bash
# .git/hooks/pre-push
# Skip with: git push --no-verify

set -e

echo "Running pre-push checks..."

echo "  [1/4] ruff lint..."
ruff check pipeline/

echo "  [2/4] ruff format check..."
ruff format --check pipeline/

echo "  [3/4] ESLint..."
npx eslint public/js/

echo "  [4/4] pytest (fast tier)..."
pytest tests/python/ -m "not live" -q

echo "Pre-push checks passed."
```

Note: `set -e` exits immediately on any non-zero return code. Each step runs in order; a failure in step 2 stops step 3. This is intentional — no point linting JS if Python is broken.

### Pattern 5: conftest.py DATA_DIR Isolation

```python
# tests/python/conftest.py
import pytest
from pathlib import Path
import pipeline.config as config

@pytest.fixture(autouse=True)
def isolate_data_dir(tmp_path, monkeypatch):
    """Redirect pipeline DATA_DIR to a tmp directory for test isolation."""
    fake_data = tmp_path / "data"
    fake_data.mkdir()
    monkeypatch.setattr(config, "DATA_DIR", fake_data)
    return fake_data

@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Prevent accidental live HTTP calls from unit tests."""
    import requests
    def _blocked(*args, **kwargs):
        raise RuntimeError(
            f"Unit test made a live network call to: {args[0]!r}. "
            "Use @pytest.mark.live for tests that need real network."
        )
    monkeypatch.setattr(requests, "get", _blocked)
    monkeypatch.setattr(requests, "post", _blocked)
```

The `autouse=True` on both fixtures means every test in `tests/python/` gets isolation without needing to declare the fixture explicitly. Tests marked `@pytest.mark.live` override this by declaring a `requests_session` fixture that bypasses the block.

### Pattern 6: API Mocking vs Live Testing Decision

| Test goal | Use | Reason |
|-----------|-----|--------|
| Test `asx_futures_scraper.py` parses JSON correctly | `mocker.patch("requests.Session.get")` returning fixture JSON | Fast, deterministic, no network needed |
| Test MarkitDigital API is still live and returning expected shape | `@pytest.mark.live` test with real `requests.get()` | Confirms actual API contract, not mocked data |
| Test `csv_handler.py` dedup logic | `tmp_path` fixture with synthetic CSV files | Pure I/O test, no network, no real data dir |
| Test status.json schema is correct | Load real `public/data/status.json` file | Validates actual pipeline output, not a mock |

The rule: if you're testing your code's logic, mock the dependency. If you're testing the dependency itself (is the API alive? does it return the fields we expect?), use a live test with `@pytest.mark.live`.

---

## Competitor Feature Analysis

This table compares local CI approaches across similar Python+JS data dashboard projects.

| Feature | Typical Python data project | Typical Node-first project | This project |
|---------|----------------------------|---------------------------|--------------|
| Python testing | pytest + pytest-cov | N/A | pytest, no coverage enforcement |
| Python linting | flake8 + black + isort | N/A | ruff (replaces all three) |
| JS testing | N/A | Jest / Vitest | Playwright (E2E only — no unit JS tests needed for vanilla JS) |
| JS linting | N/A | ESLint | ESLint v10 flat config |
| Hook management | pre-commit framework | husky + lint-staged | Shell script (simpler, solo project) |
| Test tiers | pytest-cov with markers | separate jest/playwright | pytest markers (unit vs live) |
| Data validation | manual inspection | N/A | jsonschema on status.json |
| Config consolidation | multiple files | package.json | pyproject.toml + package.json |

---

## Sources

- pytest discovery and `testpaths`: https://docs.pytest.org/en/stable/reference/customize.html (HIGH confidence)
- pytest fixtures and `conftest.py`: https://docs.pytest.org/en/stable/how-to/fixtures.html (HIGH confidence)
- pytest markers (unit/integration split): https://docs.pytest.org/en/stable/reference/reference.html (HIGH confidence)
- ruff configuration in `pyproject.toml`: https://docs.astral.sh/ruff/configuration/ (HIGH confidence)
- ruff rule sets: https://docs.astral.sh/ruff/linter/ (HIGH confidence)
- ESLint v10 flat config announcement: https://eslint.org/blog/2026/02/eslint-v10.0.0-released/ (HIGH confidence — published Feb 2026)
- ESLint flat config basics: https://eslint.org/docs/latest/use/configure/migration-guide (HIGH confidence)
- pytest-mock for HTTP mocking: https://pytest-with-eric.com/mocking/pytest-mocking/ (MEDIUM confidence)
- VCR.py vs live testing tradeoffs: https://dev.to/bowmanjd/two-methods-for-testing-https-api-calls-with-python-and-pytest (MEDIUM confidence)
- jsonschema validation in pytest: https://python-jsonschema.readthedocs.io/en/stable/validate/ (HIGH confidence)
- Git pre-push hooks pattern: https://www.dolpa.me/automating-tasks-with-git-hooks-code-linting-and-running-tests/ (MEDIUM confidence)
- Two-tier test split with markers: https://www.pythontutorials.net/blog/how-to-keep-unit-tests-and-integrations-tests-separate-in-pytest/ (MEDIUM confidence)
- Live project codebase: `/Users/annon/projects/rba-hawko-meter/pipeline/` (HIGH confidence — verified directly)

---

*Feature research for: RBA Hawk-O-Meter v1.2 — local CI and test infrastructure*
*Researched: 2026-02-24*
