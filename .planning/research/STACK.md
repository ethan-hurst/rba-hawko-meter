# Technology Stack

**Project:** RBA Hawk-O-Meter — v2.0 Local CI & Test Infrastructure
**Researched:** 2026-02-24
**Scope:** NEW capabilities only — Python unit testing, data validation, linting, git hooks, task runner

---

## Context: What Already Exists (Do Not Change)

| Layer | Technology | Version | Do Not Touch |
|-------|------------|---------|--------------|
| Python pipeline | pandas, numpy, requests, beautifulsoup4, pdfplumber | Per requirements.txt | Already in requirements.txt |
| E2E tests | Playwright | ^1.50.0 | Already in package.json |
| Python runtime | Python 3.11 (GitHub Actions), 3.13.12 (local) | 3.11+ | Used in weekly-pipeline.yml |
| Node.js runtime | v25.6.1 (local) | v25 | Already installed |
| Hosting | Netlify + GitHub Actions | — | Unchanged |

---

## Recommended Stack Additions

### Python Testing

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **pytest** | `>=9.0,<10` | Unit test runner | Industry standard for Python. Pure function coverage (zscore.py, gauge.py, ratios.py) maps cleanly to pytest's fixture + parametrize model. 9.0.2 is current stable (Dec 2025). |
| **pytest-cov** | `>=7.0,<8` | Coverage reporting | Direct pytest integration. Version 7.0.0 (Sep 2025) is current. Produces terminal + HTML reports. `--cov-fail-under=80` enforces a floor without being painful. |
| **pytest-mock** | `>=3.15,<4` | Mocking HTTP calls in tests | Thin wrapper around `unittest.mock`. Needed to unit-test scrapers without live network calls (mock `requests.get`, `pdfplumber.open`). 3.15.1 is current. |

**No pytest-xdist.** Test suite will be small (< 100 tests). Parallel execution adds complexity with no payoff at this scale.

**No pytest-asyncio.** Pipeline is synchronous — no async code to test.

### Python Data Validation

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **jsonschema** | `>=4.26,<5` | status.json schema validation | Validates status.json against a defined JSON Schema — catches missing keys, wrong types, out-of-range gauge values (0–100), invalid zone strings. 4.26.0 (Jan 2026) is current stable. Requires Python >=3.10, compatible with Python 3.11+. Used directly in a pytest test, no plugin needed. |

**No Pydantic for this use case.** Pydantic is excellent for runtime validation in web apps. For a one-file test-time JSON assertion against a fixed schema, jsonschema is lighter and more declarative — the schema file serves as living documentation of the status.json contract.

**No Great Expectations.** GE is a data pipeline observability platform for enterprise ETL workflows. Massive over-engineering for a 7-indicator JSON file.

**No Cerberus or Voluptuous.** Active but niche. jsonschema is the JSON Schema standard — portable, tooling-supported, well-understood.

### Python Linting

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **ruff** | `>=0.15,<1` | Python linting + formatting | Replaces flake8 + isort + black in a single binary. 10–100x faster than legacy tools. v0.15.2 released 2026-02-19. Configured via `ruff.toml` (no pyproject.toml required — project has none). Single `ruff check` + `ruff format --check` command covers everything. |

**No flake8.** Superseded by ruff. Slower, requires separate isort/black plugins.

**No black standalone.** Ruff's formatter is black-compatible; no need for two tools.

**No mypy/pyright.** Type checking is not in scope for v2.0 and adds significant configuration overhead for a dynamically-typed ETL pipeline that predates type annotations.

### JavaScript Linting

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **eslint** | `^10.0.0` | JS linting for vanilla IIFE modules | v10.0.0 released Feb 2026. Node.js v25.6.1 (installed) satisfies the `>=20.19.0` requirement. ESLint v10 removes the legacy eslintrc system entirely — flat config (`eslint.config.js`) is the only format. Catches real bugs in the IIFE-pattern JS files: undefined vars, unreachable code, `no-undef` on global APIs. |
| **@eslint/js** | `^10.0.0` | ESLint recommended rule set | Ships with ESLint. Provides `eslint.configs.recommended` — the baseline rule set for JS linting. No TypeScript parser needed. |
| **globals** | `^16.0.0` | Browser global definitions | Required for flat config to recognize `window`, `document`, `Plotly`, `Decimal` as known globals (not errors). Must be installed explicitly — ESLint v10 no longer bundles it. |

**No TypeScript/tsx support.** Codebase is vanilla JS — no TS needed.

**No prettier for JS.** Codebase has no build system; formatting enforcement on vanilla JS is not in scope for v2.0. ESLint handles correctness, not style.

**No @eslint/eslintrc compatibility layer.** Project starts fresh with flat config — no legacy config to migrate.

### Git Hooks

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| **lefthook** | `^2.1.1` | Pre-push git hook runner | Language-agnostic (runs both Python and JS commands in one config). Single `lefthook.yml` file — no shell script scaffolding. Binary-based: no Node.js startup overhead in the hook. Pre-push (not pre-commit) is the right trigger — fast enough that it doesn't block every commit, catches regressions before they reach GitHub. Installs via `npm i --save-dev lefthook`; integrates into `package.json prepare` script for auto-setup. |

**Not husky.** Husky only runs shell commands — works fine, but lefthook's single-file config and parallel execution capability justify the swap. For this project the difference is minor, but lefthook cleanly separates Python (`pytest`) and JS (`eslint`) hooks without shell script juggling.

**Not pre-commit (Python tool).** pre-commit is Python-ecosystem-first. Managing it alongside npm-installed tools adds a second tool registry. Lefthook handles both languages with one config.

**Not plain shell scripts in `.git/hooks/`.** Not portable across team members (not committed to git). Lefthook scripts are committed and auto-installed.

### Task Runner

**No new tool needed.** npm scripts in `package.json` are the task runner. The existing `package.json` already has `test` and `test:headed` scripts. Adding `test:fast`, `test:python`, `lint`, `lint:py`, `lint:js`, and `verify` scripts is sufficient.

**Not Makefile.** Project is macOS/Linux only and simple enough that npm scripts cover it. A Makefile would be a third configuration system alongside `lefthook.yml` and `package.json`.

**Not Just (Justfile).** Just is excellent but adds a Rust binary dependency with no payoff over npm scripts at this complexity level.

---

## Installation

### Python additions (add to requirements.txt)

```
pytest>=9.0,<10
pytest-cov>=7.0,<8
pytest-mock>=3.15,<4
jsonschema>=4.26,<5
ruff>=0.15,<1
```

### JavaScript additions (add to package.json devDependencies)

```bash
npm install --save-dev eslint@^10.0.0 @eslint/js@^10.0.0 globals@^16.0.0 lefthook@^2.1.1
```

---

## Configuration Files to Create

| File | Tool | Location | Notes |
|------|------|----------|-------|
| `ruff.toml` | ruff | repo root | `target-version = "py311"`, select E/F/I/W, exclude `pipeline/__init__.py` stubs |
| `eslint.config.js` | ESLint | repo root | Flat config with `globals.browser`, IIFE globals (Plotly, Decimal) |
| `lefthook.yml` | lefthook | repo root | `pre-push` hook: runs `pytest` (fast subset) + `ruff check` + `eslint` |
| `pytest.ini` or `[tool.pytest.ini_options]` in `pyproject.toml` | pytest | repo root | `testpaths = tests/python`, `--cov=pipeline`, `--cov-report=term-missing` |

**Use `pytest.ini` (not `pyproject.toml`)** — project has no pyproject.toml and adding one just for pytest config is unnecessary overhead. `pytest.ini` is a single-purpose file.

---

## Integration with Existing Files

### package.json — New Scripts

```json
{
  "scripts": {
    "test": "npx playwright test",
    "test:headed": "npx playwright test --headed",
    "test:python": "python -m pytest tests/python/ -v",
    "test:fast": "python -m pytest tests/python/ -v -m 'not live' && npm run lint",
    "lint": "npm run lint:py && npm run lint:js",
    "lint:py": "ruff check . && ruff format --check .",
    "lint:js": "npx eslint public/js/",
    "verify": "python -m pytest tests/python/ -v -m live && npm test"
  },
  "prepare": "lefthook install"
}
```

**Two-tier design:**
- `npm run test:fast` — pytest unit tests (mocked, no network) + linting. Runs in ~5-15 seconds. Triggered by lefthook pre-push hook.
- `npm run verify` — full pipeline with live API calls + Playwright E2E. Runs on demand; too slow for git hooks.

### requirements.txt — Additions Only

```
# Existing (unchanged)
pandas>=2.0,<3.0
numpy>=1.24,<3.0
requests>=2.28,<3.0
beautifulsoup4>=4.12,<5.0
lxml>=4.9,<6.0
python-dateutil>=2.8,<3.0
pdfplumber>=0.11,<1.0

# NEW: testing and linting (v2.0)
pytest>=9.0,<10
pytest-cov>=7.0,<8
pytest-mock>=3.15,<4
jsonschema>=4.26,<5
ruff>=0.15,<1
```

---

## What NOT to Add

| Avoid | Why |
|-------|-----|
| **Pydantic** | Overkill for a static JSON validation test. jsonschema is self-documenting and schema-portable. |
| **Great Expectations** | Enterprise data pipeline observability — 100x more than needed for status.json validation. |
| **mypy / pyright** | Type checking is out of scope for v2.0. Pipeline pre-dates type annotations. |
| **black (standalone)** | Ruff's formatter is black-compatible. Two formatters cause conflicts. |
| **flake8 + isort** | Superseded by ruff entirely. |
| **prettier** | JS formatting not in scope. Project has no build system; prettier requires a config + ignore file for every dev. |
| **Jest / Vitest** | Vanilla IIFE JS is not modular — no `import`/`export` to unit-test without a bundler. Playwright E2E already covers JS behavior. |
| **webpack / esbuild** | No build system is a deliberate architectural decision. No bundler = no module graph = no bundler needed for tests. |
| **pytest-xdist** | Parallel test execution not needed at < 100 tests. |
| **tox** | Multi-environment testing not needed. Single Python 3.11 target matches GitHub Actions. |
| **pyproject.toml** | Project has no build system. Adding pyproject.toml just for tool config (ruff + pytest already have standalone alternatives: `ruff.toml` and `pytest.ini`) adds a config system with no payoff. |
| **husky + lint-staged** | Lefthook handles both Python and JS hooks in one file without shell scripting. |
| **Makefile** | npm scripts are sufficient; Makefile is a third config system with no advantage here. |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Python test runner | pytest | unittest | pytest fixtures, parametrize, and plugin ecosystem are substantially better DX. unittest has no equivalent of `mocker` or `pytest-cov` integration. |
| Python linter | ruff 0.15.x | flake8 + black + isort | Three tools → one. Ruff is 10–100x faster. Active development (released 2026-02-19). |
| Data validation | jsonschema 4.26 | Pydantic | jsonschema is declarative + portable. Pydantic is runtime validation for typed models — wrong fit for a one-off JSON file assertion in tests. |
| JS linter | ESLint v10 | Biome | Biome is excellent but ESLint has broader vanilla JS rule coverage and better established community configs. No TypeScript = no Biome advantage for this project. |
| Git hook manager | lefthook | husky | lefthook handles Python + JS in one YAML file without shell scripts. Binary = faster. |
| Git hook manager | lefthook | pre-commit (Python tool) | pre-commit is Python-ecosystem-first and installs via pip — mixing it with npm-managed tools creates two registration systems. |
| Task runner | npm scripts | Makefile / Just | npm scripts are already in place. Adding Makefile or Just is a third config system with no payoff at this complexity level. |

---

## Version Compatibility

| Package | Python | Node.js | Conflicts |
|---------|--------|---------|-----------|
| pytest 9.0.2 | >=3.8 | — | None |
| pytest-cov 7.0.0 | >=3.9 | — | Requires coverage >=7.10.6 (auto-installed) |
| pytest-mock 3.15.1 | >=3.8 | — | None |
| jsonschema 4.26.0 | >=3.10 | — | None (Python 3.11 matches) |
| ruff 0.15.2 | >=3.7 | — | None |
| ESLint 10.0.x | — | ^20.19.0 \|\| ^22.13.0 \|\| >=24 | Node.js v25.6.1 installed — requirement met |
| globals 16.x | — | — | None |
| lefthook 2.1.1 | — | any | None (binary, not Node.js dependent) |

**GitHub Actions compatibility:** GitHub Actions uses Python 3.11 (set in `weekly-pipeline.yml`). All Python additions require >=3.8 or >=3.10 — compatible. GitHub Actions does not install Node.js by default; any JS linting steps in Actions would need `actions/setup-node`. This is NOT needed for the pre-push hook (local only) but would be needed if ESLint is added to a CI workflow in the future.

---

## Sources

- **pytest 9.0.2** — https://pypi.org/project/pytest/ — confirmed latest stable Dec 2025 (HIGH confidence)
- **pytest-cov 7.0.0** — https://pypi.org/project/pytest-cov/ — confirmed Sep 2025 (HIGH confidence)
- **pytest-mock 3.15.1** — https://pypi.org/project/pytest-mock/ — confirmed current (HIGH confidence)
- **jsonschema 4.26.0** — https://pypi.org/project/jsonschema/ — confirmed Jan 2026, requires Python >=3.10 (HIGH confidence)
- **ruff 0.15.2** — https://pypi.org/project/ruff/ — confirmed released 2026-02-19 (HIGH confidence)
- **ruff configuration** — https://docs.astral.sh/ruff/configuration/ — `ruff.toml` supported, no pyproject.toml needed (HIGH confidence)
- **ESLint v10.0.0** — https://eslint.org/blog/2026/02/eslint-v10.0.0-released/ — released Feb 2026, requires Node.js >=20.19.0 (HIGH confidence)
- **ESLint flat config** — https://eslint.org/docs/latest/use/configure/configuration-files — flat config is now the only system in v10 (HIGH confidence)
- **globals package** — https://www.npmjs.com/package/globals — required for ESLint flat config browser globals (HIGH confidence)
- **lefthook 2.1.1** — https://www.npmjs.com/package/lefthook — latest published ~7 days ago as of 2026-02-24 (HIGH confidence)
- **Node.js v25.6.1** — verified locally via `node --version` — satisfies ESLint v10 Node.js requirement (HIGH confidence)

---

*Stack research for: RBA Hawk-O-Meter v2.0 Local CI & Test Infrastructure*
*Researched: 2026-02-24*
