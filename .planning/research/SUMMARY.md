# Project Research Summary

**Project:** RBA Hawk-O-Meter — v2.0 Local CI & Test Infrastructure
**Domain:** Developer tooling — Python + vanilla JS economic dashboard
**Researched:** 2026-02-24
**Confidence:** HIGH

## Executive Summary

The v2.0 milestone adds local CI and test infrastructure to an existing Python+vanilla JS dashboard that has no unit tests, no linting, and no pre-push gates. The project already has 24 Playwright E2E tests and two GitHub Actions workflows; the gap is purely in fast, local quality feedback. Research across stack, features, architecture, and pitfalls converges on a single recommendation: a lean, two-tier test system using pytest (unit tests) + ruff (Python linting) + ESLint v10 (JS linting) + lefthook (pre-push hook), all orchestrated through npm scripts, with no new abstraction layers or frameworks beyond what these tools provide out of the box.

The critical architectural decision is strict separation between fast "unit" tests and slow "live" tests. Unit tests must never make real HTTP calls or read from live `data/*.csv` files; they run in the pre-push hook and must complete in under 10 seconds. Live tests (marked `@pytest.mark.live`) hit real external APIs and run only on demand via `npm run verify`. This separation is the single most important design decision — every pitfall identified in research flows from violating it. The `conftest.py` in `tests/python/` must enforce this from day one via an `autouse` network-blocking fixture and a `DATA_DIR` patch redirecting all file I/O to `tmp_path`.

The tooling choices are deliberate and minimal: ruff 0.15.x replaces flake8 + black + isort in a single binary; lefthook manages the pre-push hook without shell-script juggling; ESLint v10 flat config is the only valid ESLint format going forward. The right output for this milestone is 8-15 meaningful test functions covering the pure math modules (`zscore.py`, `gauge.py`, `ratios.py`, `csv_handler.py`), a schema validation test for `status.json`, and a pre-push hook that runs clean in under 10 seconds. That is the complete scope — resist the pull toward over-engineering.

---

## Key Findings

### Recommended Stack

The existing stack (pandas, numpy, requests, beautifulsoup4, pdfplumber, Playwright, GitHub Actions) is untouched. Five Python packages and four Node.js packages are added, all at their current stable versions. No build system, no type checker, no coverage enforcement tool, and no task runner beyond npm scripts. See STACK.md for full rationale.

**Core technologies:**

- **pytest 9.0.2**: Unit test runner — industry standard; parametrize and fixtures cover all use cases at this scale; requires Python >=3.8
- **pytest-cov 7.0.0**: Coverage reporting — available for visibility but not enforced; coverage % is a vanity metric for this solo project
- **pytest-mock 3.15.1**: HTTP mocking — thin wrapper over `unittest.mock`; needed to isolate scraper tests from live APIs
- **jsonschema 4.26.0**: Data validation — declarative schema assertion for `status.json` contract; requires Python >=3.10 (compatible with project's Python 3.11)
- **ruff 0.15.2**: Python linting + formatting — replaces flake8 + isort + black in one binary; released 2026-02-19; configured via `ruff.toml` (no pyproject.toml required)
- **eslint 10.0.0**: JS linting — flat config only (v10 removed legacy `.eslintrc` entirely); released Feb 2026; targets `public/js/` IIFE modules
- **@eslint/js 10.0.0 + globals 16.x**: ESLint recommended rules + browser global definitions (required for ESLint v10 flat config)
- **lefthook 2.1.1**: Pre-push hook runner — language-agnostic, single YAML config, binary (no Node.js startup overhead); manages both Python and JS hooks in one file

**Critical version requirements:**
- Python 3.11+ required (matches GitHub Actions; jsonschema requires >=3.10)
- Node.js v25.6.1 locally installed — satisfies ESLint v10's `>=20.19.0` requirement
- ESLint v10 uses flat config (`eslint.config.js`) only; no `.eslintrc` supported

**STACK.md recommends `pytest.ini` over `pyproject.toml`** for pytest config (project has no pyproject.toml and adding one just for tool config is overhead). **FEATURES.md and ARCHITECTURE.md both recommend `pyproject.toml`** as the single config hub for pytest + ruff. Recommendation: use `pyproject.toml` — it consolidates both tools in one file and is the direction both tools favour long-term.

### Expected Features

All features are developer-facing quality infrastructure with no user-visible changes.

**Must have (P1 — table stakes for "this project has CI"):**
- `pyproject.toml` with pytest + ruff config — foundation that enables everything else; without it pytest finds no tests and ruff has no target-version
- pytest unit tests for `zscore.py` and `gauge.py` — guards the mathematical core; pure functions, no fixtures required; highest value, lowest cost
- `ruff check` + `ruff format --check` on `pipeline/` — enforces code quality on all current and future scraper code; single binary
- ESLint flat config for `public/js/` — catches JS errors in 3 source files; must use `sourceType: 'script'` for IIFE modules
- Pre-push hook via lefthook — makes checks automatic; delegates entirely to `npm run test:fast`; must complete in < 10 seconds

**Should have (P2 — add within this milestone):**
- `conftest.py` with `DATA_DIR` isolation (`autouse` monkeypatch to `tmp_path`) and network-blocking autouse fixture
- pytest unit tests for `csv_handler.py` dedup logic — requires conftest `tmp_path` pattern first
- pytest unit tests for `ratios.py` normalization — requires conftest with synthetic DataFrames
- `status.json` JSON schema validation test — validates schema and constraints only, never specific float values
- Two-tier marker system (`@pytest.mark.live` for opt-in API tests; default is unit tier)

**Defer (P3 — nice-to-have, can slip):**
- `@pytest.mark.live` API health-check tests for ABS, RBA, ASX endpoints — opt-in only, never in pre-push hook

**Future / not this milestone:**
- Type annotations + mypy — requires annotating all pipeline code; substantial effort; out of scope for v2.0
- Playwright in GitHub Actions — requires display/browser CI setup; separate milestone

### Architecture Approach

The infrastructure integrates into the existing project without structural changes to `pipeline/` or the existing `tests/` Playwright directory. A new `tests/python/` directory holds all pytest tests alongside a `conftest.py` and a `fixtures/` subdirectory of static CSVs. A root `pyproject.toml` consolidates pytest and ruff configuration. `eslint.config.js` at root targets `public/js/`. The pre-push hook (managed by lefthook) delegates entirely to `npm run test:fast`, making the npm script the single source of truth for what "fast" means.

**Major components:**

1. **`pyproject.toml`** — Configuration hub: pytest `testpaths = ["tests/python"]`, `pythonpath = ["."]`, `markers`, `addopts = "--strict-markers -ra"`; ruff `target-version = "py311"`, `select`, `ignore`, `per-file-ignores`. Single file replaces pytest.ini + .flake8 + setup.cfg.

2. **`tests/python/conftest.py`** — Fixture hub (scoped to `tests/python/` only, not root): `autouse` `DATA_DIR` patch redirecting to `tmp_path`; `autouse` network blocker raising `RuntimeError` on any `requests.get/post`; static fixture loaders from `tests/python/fixtures/`; `tmp_csv` factory for write tests. Must exist before any file-touching test is written.

3. **`tests/python/` test files** — Six files: `test_zscore.py`, `test_gauge.py`, `test_ratios.py`, `test_csv_handler.py`, `test_status_schema.py`, `test_live_apis.py`. Pure-function tests need no fixtures; file-I/O tests use `tmp_csv`; live tests marked `@pytest.mark.live`.

4. **`eslint.config.js`** — Flat config with `sourceType: 'script'` (IIFE modules, not ES modules), `globals.browser`, explicit `Plotly`/`Decimal` globals for CDN-loaded libraries. Targets `public/js/**/*.js` only; ignores `tests/` and `node_modules/`.

5. **`lefthook.yml`** — Pre-push hook: runs ruff check, ruff format check, eslint, pytest fast tier in sequence with fail-fast. Installed via `npm install` (using `package.json` `prepare` script).

6. **npm scripts** — `test:fast` (the pre-push gate), `test:python`, `test:python:live`, `lint:py`, `lint:js`, `verify` (full: fast + live pytest + Playwright). `test:fast` chains with `&&` (first failure stops the chain).

**Build order (critical path):**
`pyproject.toml` → `conftest.py` + `fixtures/` → unit test files → ruff baseline audit → `eslint.config.js` → `lefthook.yml` + hook install

### Critical Pitfalls

1. **External API calls in unit tests** — Never write a test for `abs_data.py` or any ingestor that calls real HTTP. The `autouse` network-blocking fixture in `conftest.py` enforces this. Any test hitting a live URL belongs in `test_live_apis.py` with `@pytest.mark.live`. Violating this makes the pre-push hook flaky and slow within weeks; developers start using `--no-verify` and the hook is dead.

2. **Tests reading from `data/*.csv` without patching `DATA_DIR`** — `config.py` sets `DATA_DIR = Path("data")` (relative path). Tests that inherit this read from the live, mutable data CSVs. Tests become "temporally fragile" — they break after each weekly pipeline run or, worse, silently corrupt committed CSVs by writing fixture data via `append_to_csv()`. The `autouse` `DATA_DIR` patch in `conftest.py` is load-bearing; it must be in place before any file-touching test is written.

3. **Ruff on an unaudited existing codebase** — First `ruff check pipeline/` on an unaudited codebase will produce 50-200+ violations. The pre-push hook fails on day one. Fix: create `pyproject.toml` with a conservative rule set (E, F, W, I, UP — no ANN, no D, no BLE001 for intentional bare excepts in scraper graceful-degradation paths), run a one-time `ruff check --fix` baseline commit, then enable the hook. Never use `ruff --fix` in the hook itself — it auto-modifies files the developer hasn't reviewed.

4. **`status.json` validation tests asserting specific float values** — `status.json` changes every Monday after the pipeline runs. Tests asserting `hawk_score == 34.2` become false alarms and get permanently disabled. Validate schema and constraints only: required keys exist, `hawk_score` in [0, 100], zone is one of the valid enum values, no NaN gauge values, `staleness_days >= 0`. These constraints hold regardless of economic conditions.

5. **Pre-push hook that is too slow or fails without Node.js** — The hook must complete in under 10 seconds on a Python-only change. Lefthook runs commands in parallel where configured, but ESLint via `npx` can add 2-8 seconds on first run and fails entirely if `node_modules/` is not installed. Guard with a conditional check or make JS linting optional in the hook (Python lint + pytest is the primary gate).

---

## Implications for Roadmap

Based on research, the dependency graph dictates a clear 4-phase structure. Each phase is a prerequisite for the next — there are no optional orderings for the core phases.

### Phase 1: Foundation — Configuration and Test Harness

**Rationale:** `pyproject.toml` is required before pytest can discover tests and before ruff knows its target version. `conftest.py` with `DATA_DIR` isolation and network blocking is required before any test can be written safely. These are not optional prerequisites — skipping them and writing tests first causes pitfalls 2 and 1 immediately and irreversibly (correcting them later requires re-examining every test).

**Delivers:**
- `pyproject.toml` with pytest config (`testpaths`, `pythonpath = ["."]`, `markers`, `--strict-markers`) and ruff config (`target-version = "py311"`, `select = ["E", "F", "W", "I", "UP"]`, `ignore = ["E501", "BLE001"]`)
- `tests/python/conftest.py` with `autouse` `DATA_DIR` patch and `autouse` network blocker
- `tests/python/fixtures/` with minimal synthetic CSVs (CPI, employment, cash rate — 20-25 rows each, fixed known values)
- Updated `requirements.txt` with pytest, pytest-cov, pytest-mock, jsonschema, ruff
- Verified: `pytest tests/python/ -m "not live"` discovers and passes with zero tests (empty suite is the correct starting state)

**Addresses:** FEATURES.md P1 (pyproject.toml foundation), FEATURES.md P2 (conftest isolation)

**Avoids:** PITFALLS.md Pitfall 2 (DATA_DIR corruption), Pitfall 1 (live API calls in unit tests), Pitfall 6 (over-engineering — conftest stays under 50 lines, no custom plugins)

### Phase 2: Python Unit Tests — Pure Function Coverage

**Rationale:** The highest-value, lowest-cost tests are for `zscore.py` and `gauge.py` — pure math functions with no I/O dependencies. These are the mathematical core of the hawk score; regressions here are catastrophic and invisible without tests. `ratios.py` and `csv_handler.py` follow because they require the `tmp_csv` and `DATA_DIR` isolation from Phase 1. `status.json` schema validation is last because it validates a contract rather than computation logic and requires jsonschema.

**Delivers:**
- `test_zscore.py`: rolling z-score min-window requirement, zero-MAD handling (returns 0.0, not NaN), confidence thresholds (HIGH/MEDIUM/LOW), NaN propagation through window
- `test_gauge.py`: `zscore_to_gauge()` clamp at [0, 100], `classify_zone()` boundary values at zone thresholds, `compute_hawk_score()` weighted average correctness
- `test_ratios.py`: `yoy_pct_change` with sparse data and quarterly cadence, `direct` normalization path, edge case of fewer rows than `yoy_periods`
- `test_csv_handler.py`: dedup logic (new file creation, append with dedup on date column, sort order preserved)
- `test_status_schema.py`: required top-level keys, `hawk_score` in [0, 100], zone enum validity, no NaN gauge values, `staleness_days >= 0` — schema constraints only, no value assertions

**Addresses:** FEATURES.md P1 (zscore/gauge tests), FEATURES.md P2 (csv_handler, ratios, status.json validation, two-tier markers)

**Avoids:** PITFALLS.md Pitfall 5 (specific float assertions), Pitfall 2 (confirmed by autouse fixture from Phase 1), Pitfall 6 (target 8-15 test functions total, not 50)

### Phase 3: Linting — Ruff and ESLint

**Rationale:** Linting is logically independent of the pytest chain but is placed after it because the test suite should be green before adding another source of failures. The ruff baseline audit must happen before the hook is enabled — running `ruff check pipeline/` on an unaudited codebase produces noise that drowns real errors and poisons the signal. ESLint v10 flat config must be set up correctly from the start (`sourceType: 'script'` for IIFE modules, explicit Plotly/Decimal globals) or it will generate false positives on every push.

**Delivers:**
- One-time ruff baseline audit: `ruff check pipeline/ --statistics` to count violations; then `ruff check --fix pipeline/` baseline cleanup committed as "chore: ruff baseline"
- `pyproject.toml` ruff section confirmed: `select = ["E", "F", "W", "I", "UP"]`, `ignore = ["E501", "BLE001"]`
- `eslint.config.js` with `sourceType: 'script'`, `globals.browser`, Plotly/Decimal globals, `files: ["public/js/**/*.js"]`
- npm devDependencies: `eslint@^10.0.0`, `@eslint/js@^10.0.0`, `globals@^16.0.0`
- `npm run lint:py` and `npm run lint:js` scripts verified clean on existing codebase before hook is enabled

**Addresses:** FEATURES.md P1 (ruff check/format, ESLint flat config, npm lint script)

**Avoids:** PITFALLS.md Pitfall 3 (ruff noise on existing code), Pitfall 3 variant (`--fix` never runs in hook), Pitfall 7 (ESLint `sourceType: 'module'` false positives on IIFE files)

### Phase 4: Pre-Push Hook — Automated Gate

**Rationale:** The hook is the last phase because it depends on all previous phases working end-to-end. Enabling the hook before the test suite and linting are clean guarantees the hook rejects every push immediately, training developers to use `--no-verify`. The hook must be verified by deliberately pushing a violation (unused import) and confirming rejection, then pushing a clean commit and confirming it passes in under 10 seconds.

**Delivers:**
- `lefthook.yml` with `pre-push` hook: ruff check, ruff format check, eslint (conditional on `node_modules/` existing), pytest `-m "not live"`
- `npm run test:fast` as the single source of truth for the fast gate (hook delegates here)
- `npm run verify` (fast + live pytest + Playwright — on-demand full gate, never run in CI)
- `npm run test:python:live` for opt-in API verification
- lefthook installed as devDependency; `package.json` `prepare` script installs hook on `npm install`
- Verified: hook completes < 10 seconds on Python-only change; `git push --no-verify` escape hatch documented
- `.gitignore` updated with `.pytest_cache/`, `.ruff_cache/`

**Addresses:** FEATURES.md P1 (pre-push hook), P3 (`@pytest.mark.live` tests can be added here as `test_live_apis.py` stub)

**Avoids:** PITFALLS.md Pitfall 7 (slow/broken hook due to JS linting), Pitfall 4 (hook corrupting staging area — no `ruff --fix`, no DATA_DIR writes in tests), Pitfall 1 (live tests excluded via `-m "not live"`)

### Phase Ordering Rationale

- Configuration before code: `pyproject.toml` is discovered by pytest at collection time; tests written without it have no `pythonpath`, no markers, and wrong discovery settings — everything breaks silently
- Fixtures before tests: `conftest.py` `DATA_DIR` patch must exist before any test importing `pipeline.*` runs, or tests silently read from live `data/` CSVs on the first run
- Test suite green before linting enabled: confirms lint failures in the hook are genuinely new violations, not pre-existing noise masking the signal
- Hook last: once enabled, every push validates all previous phases; enabling it before they're stable creates pressure to disable it permanently

### Research Flags

Phases with standard patterns (skip research-phase — documentation is definitive):
- **Phase 1 (Configuration):** pyproject.toml + conftest.py patterns are fully documented with working code examples in both FEATURES.md and ARCHITECTURE.md. No research needed.
- **Phase 2 (Unit Tests):** Pure function testing with pytest is a solved problem. ARCHITECTURE.md provides production-ready code examples for all six test files.
- **Phase 3 (Linting):** Ruff and ESLint v10 flat config are fully documented with official sources verified at current versions. STACK.md and ARCHITECTURE.md provide ready-to-use config blocks.

Phases requiring care during execution (not research — just attention):
- **Phase 4 (Pre-Push Hook):** Lefthook's interaction with the Python venv requires verifying that `ruff` and `pytest` are on PATH when lefthook runs. Configure lefthook to use explicit venv paths (`.venv/bin/ruff`, `.venv/bin/pytest`) or document the venv activation prerequisite clearly.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All packages verified against PyPI and npm with exact version numbers. Node.js v25.6.1 confirmed locally. ESLint v10 official release blog cited (Feb 2026). Version compatibility cross-checked against Python 3.11 requirement. |
| Features | HIGH | Feature list derived from direct codebase analysis (live `pipeline/` read). Official docs cited for pytest, ruff, ESLint. Feature priorities are explicit and justified. Anti-features section is strong — clearly explains what NOT to add and why. |
| Architecture | HIGH | All patterns verified against the live codebase. File paths, import structures, and config key names confirmed against actual project files. Code examples are production-ready, not illustrative. Build order dependencies are concrete. |
| Pitfalls | HIGH | Pitfalls derived from direct codebase analysis — specifically identified `DATA_DIR = Path("data")` in `config.py`, pdfplumber lazy import pattern, `create_session()` injection point. Prevention strategies reference official patterns. |

**Overall confidence: HIGH**

### Gaps to Address

- **Lefthook venv activation:** Lefthook runs pre-push commands as separate processes. If the Python venv is not activated before `git push`, lefthook's `ruff` and `pytest` commands may find system Python. Resolution: configure lefthook to use explicit `.venv/bin/` paths, or document the venv activation prerequisite. Low risk — single developer project, easy to resolve in Phase 4.

- **Ruff baseline violation count:** The exact number of ruff violations on the existing `pipeline/` codebase is unknown. This is a 30-second audit (`ruff check pipeline/ --statistics`), not a research gap. Run it on day one of Phase 3 before committing to the baseline approach.

- **ESLint violation count on `public/js/`:** The number of existing violations in the 3 JS source files is unknown. Run `npx eslint public/js/` before enabling in the hook; fix or configure-away existing violations as part of Phase 3.

- **Conflict on config file choice (pytest.ini vs pyproject.toml):** STACK.md recommends `pytest.ini` (no pyproject.toml needed); FEATURES.md and ARCHITECTURE.md recommend `pyproject.toml` (single config hub). Resolution: use `pyproject.toml` — it is the long-term direction for both pytest and ruff, and the project has no conflicting use for it.

---

## Sources

### Primary (HIGH confidence)

- PyPI: pytest 9.0.2, pytest-cov 7.0.0, pytest-mock 3.15.1, jsonschema 4.26.0, ruff 0.15.2 — confirmed stable versions
- https://docs.astral.sh/ruff/configuration/ — `ruff.toml` supported; rule set documentation
- https://eslint.org/blog/2026/02/eslint-v10.0.0-released/ — ESLint v10 flat config mandatory, Node.js >=20.19.0 requirement
- https://eslint.org/docs/latest/use/configure/configuration-files — flat config structure and `sourceType` options
- https://docs.pytest.org/en/stable/reference/customize.html — `pyproject.toml` pytest configuration keys
- https://docs.pytest.org/en/stable/how-to/fixtures.html — conftest.py, autouse, monkeypatch patterns
- https://docs.pytest.org/en/stable/explanation/goodpractices.html — `pythonpath`, discovery, `tests/python/` structure recommendation
- https://www.npmjs.com/package/lefthook — lefthook 2.1.1, language-agnostic hook manager, YAML config format
- Live codebase: `/Users/annon/projects/rba-hawko-meter/pipeline/` — `DATA_DIR` relative path pattern, import structure, pdfplumber lazy imports, `create_session()` injection point confirmed

### Secondary (MEDIUM confidence)

- https://python-jsonschema.readthedocs.io/en/stable/validate/ — schema validation pattern for use in pytest
- https://pytest-with-eric.com/mocking/pytest-mocking/ — pytest-mock HTTP mocking patterns
- https://dev.to/bowmanjd/two-methods-for-testing-https-api-calls-with-python-and-pytest — VCR.py vs live testing tradeoffs

---

*Research completed: 2026-02-24*
*Ready for roadmap: yes*
