# Pitfalls Research

**Domain:** Adding local CI and test infrastructure to an existing Python+JS pipeline project
**Researched:** 2026-02-24
**Confidence:** HIGH (based on direct codebase analysis, established pytest/ruff/git-hooks patterns)

---

## Critical Pitfalls

### Pitfall 1: Testing External APIs Directly in the Unit Test Suite

**What goes wrong:**
Tests for `abs_data.py`, `asx_futures_scraper.py`, `nab_scraper.py`, and `corelogic_scraper.py` call out to real government and market APIs. The pre-push hook runs these tests on every push. After a few weeks, the suite is "slow and flaky" — developers start bypassing the hook with `git push --no-verify`. The hook is dead.

**Why it happens:**
The natural instinct when adding tests to an ingestor is to write a test that calls `fetch_and_save()` and checks the return value. This is an integration test disguised as a unit test. External APIs (ABS SDMX, ASX MarkitDigital, NAB, Cotality) have no SLA guarantees for developer test traffic. The ABS API returns HTTP 429 during scraper development load. NAB has Cloudflare bot detection that trips on automated requests from CI IPs.

**Consequences:**
- Pre-push hook takes 30+ seconds for a change to a CSS file.
- Tests pass locally, fail in CI because ABS is temporarily down.
- Developers learn `--no-verify`. The hook provides no protection.
- Test run marks the whole suite red due to a 503 from a government server.

**How to avoid:**
Strictly separate unit tests from integration tests at the architecture level:
- **Unit tests** (`pytest tests/unit/`): Only use fixtures/mocks. Never call `requests.get()`. Use `pytest-mock` or `responses` library to intercept HTTP calls. These are what the pre-push hook runs.
- **Integration/live tests** (`pytest tests/live/`): Call real APIs. Run manually via `npm run verify`. Marked with `@pytest.mark.live` so `pytest -m "not live"` excludes them automatically.

The `pipeline/utils/http_client.py` `create_session()` function is the injection point — unit tests pass a mock session.

**Warning signs:**
- Any test file in `tests/unit/` that imports `requests` and does not import `responses` or `unittest.mock`.
- Test runtime for the unit suite exceeds 5 seconds.
- Intermittent CI failures not caused by code changes.

**Phase to address:**
Phase 1 (pytest unit tests). Establish the two-tier architecture before writing the first test.

---

### Pitfall 2: Testing Against Committed CSVs Instead of Isolated Fixtures

**What goes wrong:**
Tests for normalization (`ratios.py`, `zscore.py`, `engine.py`) read from `data/abs_cpi.csv`, `data/rba_cash_rate.csv`, etc. — the real committed data files. When the pipeline updates these CSVs, tests that previously passed now fail because a new data point changes the latest z-score or gauge value. A test asserting `gauge_value == 42.3` breaks the week after a new CPI release.

**Why it happens:**
The normalize/engine functions use `DATA_DIR` from `config.py`, which resolves to `./data/` relative to the working directory. Tests that call these functions without redirecting the data path inherit this implicit dependency on the working repo state.

**Consequences:**
- Tests become "temporally fragile" — they pass when written and fail three months later.
- To fix, developers start hardcoding the expected value to whatever the latest run produces. Now the tests assert nothing meaningful.
- Tests can only be run from the repo root in a specific directory, breaking in any CI environment that has a different working directory.

**How to avoid:**
Create isolated fixture CSVs in `tests/fixtures/` with a fixed, known dataset (e.g., 20 rows of synthetic quarterly data). Patch `pipeline.config.DATA_DIR` in conftest.py to point to the fixtures directory for all unit tests:

```python
# tests/conftest.py
import pytest
from pathlib import Path
from unittest.mock import patch

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture(autouse=True)
def mock_data_dir():
    with patch("pipeline.config.DATA_DIR", FIXTURES_DIR):
        with patch("pipeline.normalize.ratios.DATA_DIR", FIXTURES_DIR):
            with patch("pipeline.normalize.engine.DATA_DIR", FIXTURES_DIR):
                yield FIXTURES_DIR
```

The fixture CSVs never change unless intentionally updated. Tests assert against known expected outputs (e.g., "with these 20 CPI values, YoY pct change for row 13 is 3.2%").

**Warning signs:**
- Any test that reads from `Path("data/")` without patching `DATA_DIR`.
- Tests that pass today but are silently wrong (asserting the computed value equals whatever the current data produces without an independent expected value).
- Test output changes after a pipeline run even without code changes.

**Phase to address:**
Phase 1 (pytest unit tests). Fixtures must be established before normalization tests are written.

---

### Pitfall 3: Pre-Push Hook That Blocks on Linting an Existing Codebase

**What goes wrong:**
Ruff is installed and run for the first time on 3,227 lines of existing Python. It returns 200+ warnings across 19 files. The pre-push hook runs `ruff check pipeline/` and exits non-zero. Every push fails until all 200+ warnings are fixed. Developer spends a day on linting cleanup instead of the actual milestone work. Or worse: `ruff check` is commented out of the hook "temporarily" and never restored.

**Why it happens:**
Ruff is strict by default. An existing codebase that has never been linted will have real issues (missing type annotations, unused imports, line length violations) mixed with stylistic preferences (`E501` line-too-long is frequently noisy on data pipelines with long URLs and pandas chains). Running `--select ALL` on an existing codebase produces noise that obscures real errors.

**Consequences:**
- The linter hook is neutered immediately because the signal-to-noise ratio is too low.
- OR: 3+ hours of mechanical linting changes create a large diff that makes the actual feature diff hard to review.
- OR: The existing code's intentional patterns (e.g., `logging.basicConfig()` at module level in scrapers, bare `except` in graceful-degradation paths) get "fixed" in ways that change runtime behavior.

**How to avoid:**
A two-step process:
1. **Baseline pass before writing any tests**: Run `ruff check pipeline/ --output-format=json | jq 'length'` to count violations. Create `pyproject.toml` (or `ruff.toml`) that selects only the rules that matter for correctness (E, F, W categories) and explicitly ignores line-length (`E501`) and stylistic rules (`ANN`, `D`). Fix the baseline violations. Commit this as a separate "chore: ruff baseline cleanup" commit.
2. **Hook runs this specific ruff config**: The hook only fails on the agreed-upon ruleset, not the full `--select ALL` ruleset.

Critical: The existing `except Exception: pass` patterns in scraper code (e.g., `csv_handler.py`, `nab_scraper.py`) are intentional. Ruff `BLE001` (blind exception) should be in the ignore list — do not refactor graceful-degradation patterns based on linter suggestions without understanding why they exist.

**Warning signs:**
- First `ruff check` run exits with code 1 and 50+ violations.
- Any ruff rule in the `ANN` (type annotations) or `D` (docstrings) category is enabled for a codebase that has no type annotations or docstrings.
- The ruff config enables `--fix` in the hook — this auto-modifies files on push, which surprises developers.

**Phase to address:**
Phase 3 (linting). Run the baseline audit before enabling the hook.

---

### Pitfall 4: The Pre-Push Hook Corrupts the Git Staging Area

**What goes wrong:**
The pre-push hook runs `python -m pytest tests/unit/` and then runs `ruff check`. Both commands succeed. But during the test run, `conftest.py` inadvertently wrote a file to `data/` (because `DATA_DIR` was not properly patched). Git now shows a modified `data/abs_cpi.csv`. The developer's `git push` succeeds but they've just committed unexpected test artifacts to the repo.

Variant: the hook runs `ruff --fix` automatically, modifying staged files. The push goes through but the committed code is different from what the developer reviewed before pushing.

**Why it happens:**
- Tests that use real `DATA_DIR` without isolation will write to committed data files as side effects.
- `ruff --fix` in hooks is tempting but dangerous: it modifies files, and the developer hasn't reviewed the fixes.
- Hook scripts that `cd` to different directories can leave the shell in an unexpected state if they exit early.

**Consequences:**
- Committed test artifacts pollute the data history.
- Developers lose trust in the hook — it "does things" they didn't intend.
- In the worst case, a test run calls `append_to_csv()` with fixture data and appends garbage rows to a committed CSV.

**How to avoid:**
- Unit tests must NEVER write to `data/`. The `DATA_DIR` patch in conftest.py must redirect all writes to a `tmp_path` (pytest's temporary directory fixture) or `tests/fixtures/`.
- The hook must NEVER use `ruff --fix`. Check only, never auto-fix.
- The hook should `stash --include-untracked` before running if it needs to be safe, but more practically: ensure tests have no side effects by design, not by stashing.
- Verify with `git status` after the first hook run that no files are modified.

**Warning signs:**
- `data/*.csv` files appear in `git status` after running `pytest`.
- `public/data/status.json` is modified after running tests (normalization engine wrote to it during test).
- Any test that calls `generate_status()` without patching `STATUS_OUTPUT`.

**Phase to address:**
Phase 1 (pytest setup) and Phase 4 (pre-push hook). The DATA_DIR isolation must be verified before the hook is enabled.

---

### Pitfall 5: status.json Validation Tests That Break on Every Pipeline Run

**What goes wrong:**
A test validates `public/data/status.json` and asserts specific field values: `assert status['overall']['hawk_score'] == 34.2`. The pipeline runs Monday morning. The hawk score is now `31.1`. The test fails. This is treated as a pipeline failure when the pipeline actually succeeded.

**Why it happens:**
`status.json` is a live data file whose contents change every time the pipeline runs. It is also committed to the repo. Tests that assert on its exact values are testing the wrong thing: they're testing the current economic data, not the software that generates the file.

**Consequences:**
- Developers manually update the assertion after every pipeline run. After two months, nobody updates it. The test is permanently disabled.
- CI fails on Monday after every weekly run, creating a false alarm pattern.

**How to avoid:**
`status.json` validation tests must validate **schema and constraints**, not values:
- All required top-level keys exist (`generated_at`, `overall`, `gauges`, `metadata`).
- `overall.hawk_score` is a float in `[0, 100]`.
- `overall.zone` is one of `['cold', 'cool', 'neutral', 'warm', 'hot']`.
- Each gauge entry has `value`, `zone`, `z_score`, `raw_value`, `data_date`, `confidence`, `staleness_days`.
- `staleness_days` for critical indicators (inflation, employment) is `< 90`.
- No gauge `value` is `null` or `NaN`.
- `generated_at` is a valid ISO 8601 timestamp.

These constraints hold regardless of what the data is. They would catch: a missing indicator, a NaN z-score propagating through to the gauge, a timestamp field set to an empty string, a gauge value outside [0, 100].

**Warning signs:**
- Any assertion of the form `assert status['overall']['hawk_score'] == <specific_float>`.
- Tests that regenerate `status.json` using real CSVs and then validate the output value.
- Test file that was last updated before a pipeline run.

**Phase to address:**
Phase 2 (status.json validation).

---

### Pitfall 6: Over-Engineering the Test Infrastructure

**What goes wrong:**
The v2.0 milestone gets captured by building a test framework. By the end of the milestone, there are: a conftest with 15 fixtures, a custom pytest plugin for API mocking, a Makefile with 8 targets, a `scripts/run-tests.sh` with 4 environment modes, a `pyproject.toml` with 40 ruff rules and 8 ignore lists, and a coverage report uploaded to a coverage badge service. Zero of the 6 actual pipeline modules have meaningful test coverage. The developer wrote more test infrastructure code than production code.

**Why it happens:**
Testing is an engineering domain. Engineers apply engineering instincts: abstractions, reusability, configurability. The first test reveals the need for a fixture. The fixture reveals the need for a factory. The factory reveals the need for a base class. This pattern compounds quickly when starting from zero.

**Consequences:**
- The milestone is consumed by framework work that doesn't test the actual pipeline.
- Subsequent phases inherit a test framework with assumptions that don't fit their needs.
- The "framework" becomes a maintenance burden that developers work around rather than with.

**How to avoid:**
Apply the "simplest thing that works" constraint aggressively:
- `conftest.py` starts with 3 fixtures: `mock_data_dir`, `sample_cpi_df`, `sample_config`.
- No custom pytest plugins in this milestone.
- `npm run test:fast` calls `pytest tests/unit/ -q`. That's the entire fast-test infrastructure.
- `npm run verify` calls `pytest tests/live/ -v -m live`. That's the entire live infrastructure.
- No coverage targets until coverage is a stated milestone goal.

The test count goal should be: all pure functions in `zscore.py`, `ratios.py`, `gauge.py`, `csv_handler.py` are tested. That is ~8-12 test functions. Not 50.

**Warning signs:**
- The conftest.py is longer than the module being tested.
- A test fixture abstracts over another test fixture.
- The PR for "Phase 1: unit tests" adds more lines to test infrastructure files than to actual test files.
- Any reference to `pytest-xdist`, `hypothesis`, or coverage badges in the v2.0 milestone scope.

**Phase to address:**
Phase 1 (pytest setup). Establish scope constraints in the plan before writing any code.

---

### Pitfall 7: Linting JS and Python in the Same Hook Without Isolation

**What goes wrong:**
The pre-push hook script calls `ruff check pipeline/` then `npx eslint public/js/`. `npx eslint` takes 8-12 seconds on first run (downloading ESLint on demand). The Python lint step passes in 0.3 seconds; the whole hook takes 15 seconds due to JS linting. Developers pushing a 2-line Python change wait 15 seconds for JS lint they didn't change.

Variant: ESLint is not installed (no `node_modules/`) because the developer only works on Python. The hook crashes with `npx: command not found` or `Cannot find module eslint`. The hook fails on a machine that only has Python set up.

**Why it happens:**
The hook is written as a single sequential script that always runs both linters. There is no check for whether the linter is available or whether relevant files have changed.

**Consequences:**
- Slow hook frustrates Python-only changes.
- Missing ESLint installation breaks the hook entirely on Python-focused machines.
- Developers disable the hook because it's unreliable.

**How to avoid:**
- The hook should check if a linter is available before running it: `if command -v npx &>/dev/null && [ -d node_modules ]; then npx eslint public/js/ --quiet; fi`.
- ESLint in the pre-push hook is optional for v2.0. The primary gate is Python linting and the Python test suite. JS linting can be a `npm run lint` command that developers run manually.
- If both linters are included, scope them to changed files only: `git diff --name-only HEAD | grep '\.py$'` to decide whether to run ruff.

**Warning signs:**
- The hook takes > 5 seconds on a warm machine.
- Hook fails on machines without Node.js installed.
- Hook runs ESLint even when only Python files changed.

**Phase to address:**
Phase 4 (pre-push hook). Define the hook's minimum viable scope: Python only. Add JS linting as optional.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Call real ABS API in unit tests | Tests "feel more real" | Flaky tests, slow suite, pre-push hook bypassed with `--no-verify` | Never — mock HTTP at the session level |
| Read from `data/*.csv` in unit tests without patching DATA_DIR | No fixture setup required | Tests break on every pipeline run; tests can corrupt committed data | Never — patch DATA_DIR in conftest.py |
| Assert specific float values from status.json | Easy to write | Breaks every Monday after pipeline run; test becomes meaningless boilerplate | Never — assert schema and range constraints only |
| Run `ruff --select ALL` on existing code | Maximally strict | 200+ violations, noise drowns signal, hook immediately bypassed | Never — baseline with E/F/W only, add rules incrementally |
| `ruff --fix` in the pre-push hook | Auto-fixes style | Modifies files the developer hasn't reviewed; corrupts staging area | Never — lint with check-only in hooks |
| Single `npm test` that runs Playwright + pytest + lint | One command simplicity | Playwright tests require a running server; confusing to run in isolation | Never — keep `npm run test:fast` (Python only) and `npm test` (Playwright) separate |
| Add pyfakefs or full filesystem mocking | Truly isolates filesystem | Significant setup complexity; harder to debug fixture issues | Only if `DATA_DIR` patching proves insufficient |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| pytest + existing Python pipeline | Tests run from wrong directory; relative paths in `config.py` (`DATA_DIR = Path("data")`) resolve to unexpected locations | Run pytest from repo root; verify `DATA_DIR` resolves correctly before writing first test; patch in conftest.py |
| pytest + Playwright | Running `npm test` (Playwright) after adding pytest; test commands overlap; `npm test` runs only Playwright | Keep commands separate: `npm test` stays Playwright, `npm run test:fast` runs pytest |
| ruff + existing code with intentional `bare except` | Ruff `BLE001` flags `except Exception: pass` in graceful-degradation scrapers | Add `# noqa: BLE001` inline or add BLE001 to ignore list in `ruff.toml`; do NOT refactor the error handling |
| ESLint + no `.eslintrc` | ESLint uses default flat config, applies wrong rules to Plotly/Tailwind browser JS | Configure `eslintrc` or `eslint.config.js` with `env: { browser: true }` before first run |
| pre-push hook + `git stash` | Hook stashes changes, runs tests, fails to unstash on error — developer loses changes | Do NOT stash in hooks; instead ensure tests have no side effects by design |
| pre-push hook + Python venv | Hook uses system Python, not venv Python; pytest not found; imports fail | Hook must activate venv or use explicit path: `.venv/bin/pytest` or `python -m pytest` |
| responses library + session retries | `responses` intercepts the `requests` library but the retry adapter in `create_session()` may interfere with mock interception | Use `responses` with `assert_all_requests_are_fired=False`; verify mock is hit by checking call count |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| pytest importing all pipeline modules at collection time triggers network calls | `pytest tests/unit/` hangs for 5 seconds before any test runs | Ensure module-level code in ingestors does not make network calls; `logging.basicConfig()` at module level in scrapers is fine; `session.get()` at module level is not | First run of pytest on this codebase |
| Live tests mixed with unit tests without markers | `pytest tests/` runs live tests on every invocation including pre-push hook | Use `@pytest.mark.live` and configure `addopts = -m "not live"` in `pyproject.toml` | When a developer runs `pytest` without `-m` flag |
| pdfplumber import in `nab_scraper.py` and `corelogic_scraper.py` at test time | Tests that import scrapers trigger pdfplumber C extension loading | pdfplumber is imported lazily (`import pdfplumber` inside functions) — this is already the case in the codebase; do not move the import to module level | Immediately if pdfplumber is imported at module level |
| Generating `status.json` in a test to validate it | Test takes 3-8 seconds to run the full normalization engine | Test schema validation against a pre-generated fixture `status.json`, not against a freshly-generated one | Immediately — normalization engine should not run in unit tests |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Live test hits ABS/RBA APIs from a developer machine with a project-identifiable User-Agent | API provider rate-limits or blocks the User-Agent string | Live tests use the same session as production; this is acceptable since live tests run infrequently. Do not add a test-specific User-Agent that would confuse production logs |
| Git hook script committed with wrong permissions | Hook never runs because it's not executable | `chmod +x .git/hooks/pre-push` in the hook installation step; document this in the setup guide |
| Hook script added to `.git/hooks/` (not version-controlled) | New team member clones the repo and has no hook | Commit the hook to a version-controlled location (e.g., `scripts/pre-push`) and document: `cp scripts/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push`; or use a hook manager like `pre-commit` |
| `npm run verify` accidentally runs in GitHub Actions | Full live API call from CI triggers rate-limiting on ABS/RBA | Ensure `verify` script is not called by any GitHub Actions workflow; tag it clearly as "local only" in package.json comments |

---

## "Looks Done But Isn't" Checklist

- [ ] **Unit test suite:** Tests pass with `DATA_DIR` pointing to `tests/fixtures/`, not `data/`. Run `git status` after `pytest tests/unit/` — zero files should be modified.
- [ ] **HTTP mocking:** Every test for an ingestor that would otherwise call a real URL has the HTTP call mocked. Verify by disconnecting from the network and running `pytest tests/unit/` — every test still passes.
- [ ] **status.json validation:** The validator is tested against a deliberately broken `status.json` (missing a required field, NaN gauge value, staleness > threshold) — the validator must catch each broken case.
- [ ] **ruff baseline:** Run `ruff check pipeline/ --statistics` before and after the baseline cleanup commit. No rules that would catch real bugs (F401 unused import, F821 undefined name, E711 comparison to None) should be in the ignore list.
- [ ] **Pre-push hook:** Push a commit that introduces a ruff violation (e.g., `import os` unused) — the hook must reject it. Push a passing commit — it goes through. Push without a venv activated — verify the error message is clear (not a Python traceback).
- [ ] **Two-tier separation:** Run `npm run test:fast` (must complete in < 10 seconds). Run `npm run verify` (may take 30-120 seconds, calls real APIs). The outputs are clearly distinct.
- [ ] **ESLint (JS linting):** Run `npx eslint public/js/` without errors on the existing codebase before enabling in any hook. Verify `env: { browser: true }` is set (Plotly, Decimal are browser globals, not Node.js globals).
- [ ] **Playwright isolation:** `npm test` (Playwright) still passes after adding pytest. The two test suites do not interfere with each other.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Hook bypassed with `--no-verify` due to slow/flaky tests | MEDIUM | Audit which tests are hitting real APIs; move them to `tests/live/`; add HTTP mocks for unit equivalents; re-enable hook |
| Committed data files modified by test run | LOW | `git restore data/*.csv public/data/status.json`; add DATA_DIR patch to conftest.py; re-run tests to confirm no side effects |
| Ruff baseline too strict — developers disable the hook | LOW | Loosen the ruleset to E/F/W categories; re-run baseline; get buy-in before re-enabling; document the agreed ruleset |
| status.json validation tests fail every Monday | LOW | Replace value assertions with range/schema assertions; delete the specific float assertions |
| Pre-push hook not installed on a new machine | LOW | Document the one-time setup: `cp scripts/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push` |
| ESLint fails on Plotly browser globals | LOW | Add `/* global Plotly, Decimal */` to JS files or add `env: { browser: true }` to ESLint config; do not add `eslint-disable` lines to the source code |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| External API calls in unit tests | Phase 1: pytest setup | Run `pytest tests/unit/` with network disconnected — all pass |
| Tests reading from `data/*.csv` | Phase 1: pytest setup | `git status` after `pytest tests/unit/` shows no modified files |
| status.json tests asserting specific values | Phase 2: status.json validation | Validator passes on `status.json` generated 3 months from now without modification |
| Ruff noise on existing codebase | Phase 3: linting | `ruff check pipeline/` exits 0 on existing code before new code is written |
| `ruff --fix` corrupting hook staging | Phase 4: pre-push hook | Hook uses `--check` flag only; verified with `ruff check --help` |
| Slow/broken hook due to JS linting | Phase 4: pre-push hook | Hook completes in < 5 seconds on a Python-only change |
| Over-engineering test infrastructure | Phase 1: pytest setup | conftest.py < 50 lines; test count for this phase is 8-15 functions |
| DATA_DIR patch not covering all module paths | Phase 1: pytest setup | Grep `pipeline/` for `DATA_DIR` usages; verify each is patched in conftest.py |
| Live tests mixed with unit tests | Phase 1 + Phase 5: live verification | `pytest -m "not live"` runs in < 10 seconds; `pytest -m live` calls real APIs |
| Hook not version-controlled | Phase 4: pre-push hook | Hook script committed to `scripts/pre-push`; README updated with setup step |

---

## Sources

- Direct codebase analysis: `pipeline/config.py` uses `DATA_DIR = Path("data")` (relative path — requires conftest.py patching strategy)
- Direct codebase analysis: `pipeline/utils/http_client.py` `create_session()` — injection point for HTTP mocking in tests
- Direct codebase analysis: `pipeline/ingest/nab_scraper.py` and `corelogic_scraper.py` — pdfplumber imported lazily inside functions (test-safe pattern)
- Direct codebase analysis: `pipeline/main.py` tiered failure handling — unit tests must not test against real API responses or test becomes an integration test of Australian government APIs
- pytest documentation — `pytest.mark` and `addopts` for test tier separation (HIGH confidence — official docs)
- ruff documentation — `--select` / `--ignore` for baseline configuration (HIGH confidence — official docs)
- Established pattern: pre-commit framework vs. manual `.git/hooks/` — manual hooks are simpler for a single-developer project; `pre-commit` framework adds complexity without benefit at this scale
- `responses` library — HTTP mocking for `requests`-based code (HIGH confidence — widely used, well-documented)
- ESLint flat config documentation — `env: { browser: true }` requirement for browser JS (HIGH confidence — official docs)

---
*Pitfalls research for: Adding local CI and test infrastructure (v2.0 milestone) — rba-hawko-meter*
*Researched: 2026-02-24*
