# Phase 15: Pre-Push Hook - Research

**Researched:** 2026-02-25
**Domain:** Git hook management with Lefthook, npm script composition, Python/JS linting integration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Hook mechanism
- Use **Lefthook** as the hook manager
- Install as npm devDependency (`@evilmartians/lefthook` — NOTE: see research finding below on package name)
- Auto-install hook via `postinstall` script in package.json
- Standard `--no-verify` bypass allowed for emergencies
- Config lives in `lefthook.yml` at project root

#### Fast gate composition
- Gate runs **lint + unit tests in parallel** (lefthook parallel commands)
- Lint: `ruff check pipeline/ tests/` + `eslint public/js/`
- Tests: `pytest tests/python/ -m "not live"` (non-live only)
- Full project scope (not incremental/changed-files-only)
- **30 second hard timeout** — gate killed and push rejected if exceeded

#### npm script design
- `npm run test:fast` — Same as pre-push gate: lint + unit tests (exact same commands, same exit codes)
- `npm run verify` — Full suite in sequence: fast gate + live pytest + Playwright
- **Replace** existing `verify` script entirely (old pipeline/verify commands can be run directly)
- Keep existing scripts (`lint`, `test`, `lint:py`, `lint:js`, `test:python:live`) as-is — minimal disruption
- Add `test:fast` as the new script; update `verify` to the full tiered suite

#### Failure experience
- **Show failing output only** — suppress passing check output
- **Clear failure banner** on blocked push (e.g., "Push blocked: lint errors found. Run npm run test:fast to see details.")
- **Silent on success** — no extra output, push just goes through
- **Show all failures together** — since lint and tests run in parallel, display both lint errors and test failures so developer can fix everything in one pass

### Claude's Discretion
- Exact lefthook.yml configuration syntax
- Banner formatting and exact wording
- How to compose parallel commands in lefthook
- Timeout implementation details

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HOOK-01 | Pre-push git hook automatically runs fast test suite before push | Lefthook `pre-push` hook with `parallel: true` + `commands` block; auto-installed via lefthook's npm postinstall |
| HOOK-02 | Fast test suite completes in under 10 seconds | Parallel execution of lint+tests; `timeout: "30s"` at command level as safety net; pyenv-managed tools avoid venv activation overhead |
| HOOK-03 | Developer can run fast tests manually via `npm run test:fast` | New `test:fast` npm script runs identical commands to the hook (ruff + eslint + pytest -m "not live") using `&&` / concurrently |
| HOOK-04 | Developer can run full verification manually via `npm run verify` | Replace existing `verify` script with three-tier sequence: `npm run test:fast && pytest -m live && npx playwright test` |
</phase_requirements>

---

## Summary

Phase 15 implements a pre-push quality gate using Lefthook — a Go-based Git hooks manager installed as an npm devDependency. Lefthook's `parallel: true` at the hook level runs ruff, ESLint, and pytest concurrently, blocking the push if any fail. The `output` global configuration suppresses passing-check noise and surfaces only failures. Two npm scripts complete the picture: `test:fast` reproduces the hook invocation exactly, and `verify` composes all three tiers (fast + live + Playwright) sequentially.

The critical path has no blocking unknowns. Lefthook's npm package auto-runs `lefthook install` via its own postinstall script — the CONTEXT.md decision to "add a postinstall script" may mean adding `"postinstall": "lefthook install"` to package.json as a belt-and-suspenders fallback, but the `lefthook` npm package already handles this automatically. Python tooling (ruff, pytest) is installed globally via pyenv — there is no `.venv` in this project, so no venv activation is needed in the hook commands.

The 30-second timeout is implemented at the command level using `timeout: "30s"` (string format, e.g. `"30s"`) in each command definition. Output control uses the global `output:` array — to achieve "show failures only, silent on success," set `output: [failure, execution_out]`.

**Primary recommendation:** Use `lefthook` (not `@evilmartians/lefthook`) as it is now the recommended package name; configure `output: [failure, execution_out]` globally for silent-on-success behavior; use `timeout: "30s"` per command.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| lefthook | latest (^1.x) | Git hooks manager | Locked decision; Go binary, zero Node runtime dependency, parallel support built-in |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| ruff | >=0.15.2 (already installed) | Python linter | Already in project; pyenv-managed |
| eslint | ^10.0.2 (already installed) | JS linter | Already in project |
| pytest | >=9.0.2 (already installed) | Python test runner | Already in project; pyenv-managed |
| npx playwright | via @playwright/test ^1.50.0 | E2E tests (verify tier 3) | Already in project |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| lefthook | husky + lint-staged | Husky requires shell scripts, no built-in parallel; lint-staged is commit-only. Lefthook is locked. |
| lefthook | pre-commit (Python) | Pre-commit requires Python runtime to manage; lefthook is self-contained. Locked. |

**Installation:**
```bash
npm install lefthook --save-dev
```

Note: The CONTEXT.md references `@evilmartians/lefthook` (the legacy package) but the current recommendation from the official docs is `lefthook` (the recommended package). Both work. `lefthook` installs only the binary for the current OS; `@evilmartians/lefthook` installs binaries for all OSes. For this single-developer project on macOS, `lefthook` is cleaner. Either is fine — flag this choice to the planner.

---

## Architecture Patterns

### Recommended Project Structure
```
project-root/
├── lefthook.yml          # Hook configuration (committed to git)
├── package.json          # devDependencies + scripts
├── pyproject.toml        # Existing pytest/ruff config (unchanged)
└── .git/hooks/
    └── pre-push          # Auto-installed by lefthook postinstall
```

### Pattern 1: Parallel Pre-Push with Timeout and Output Suppression

**What:** A `pre-push` hook that runs two parallel command groups, each with a 30s timeout. Global `output` is restricted to failures only so the terminal is silent on clean pushes.

**When to use:** When the gate has multiple independent checks (lint vs. tests) that can run concurrently.

**Example:**
```yaml
# lefthook.yml
# Source: https://lefthook.dev/configuration/ + schema.json verified

output:
  - failure
  - execution_out

pre-push:
  parallel: true
  commands:
    lint-py:
      run: ruff check pipeline/ tests/
      timeout: "30s"
      fail_text: "Push blocked: Python lint errors found. Run: npm run test:fast"
    lint-js:
      run: eslint public/js/
      timeout: "30s"
      fail_text: "Push blocked: JS lint errors found. Run: npm run test:fast"
    unit-tests:
      run: pytest tests/python/ -m "not live"
      timeout: "30s"
      fail_text: "Push blocked: Unit tests failed. Run: npm run test:fast"
```

**Key insight:** `parallel: true` at the hook level makes ALL commands run concurrently. All failures are collected and shown together before the push is rejected — satisfying the "show all failures together" requirement.

### Pattern 2: npm Script Composition

**What:** `test:fast` reproduces the hook's gate invocation for manual use. `verify` chains all three tiers sequentially.

**When to use:** `test:fast` before pushing manually; `verify` for release validation.

**Example:**
```json
{
  "scripts": {
    "test:fast": "npm run lint && pytest tests/python/ -m \"not live\"",
    "verify": "npm run test:fast && pytest tests/python/ -m live -v && npx playwright test"
  }
}
```

**Important:** `test:fast` runs lint serially (via `npm run lint` which chains `lint:py && lint:js`) then pytest. This is slightly different from the hook (which parallelizes) but produces identical exit codes and output. The success criteria requires "same result" and "same exit code" — not identical execution order.

Alternative using `concurrently` if true parallel in `test:fast` is desired:
```bash
concurrently "ruff check pipeline/ tests/" "eslint public/js/" && pytest tests/python/ -m "not live"
```
But `concurrently` is not currently in the project. The serial approach via `npm run lint && pytest ...` is simpler and meets the success criteria.

### Pattern 3: Postinstall Auto-Install

**What:** The `lefthook` npm package includes a postinstall script that runs `lefthook install` automatically. For belt-and-suspenders, also add it explicitly in package.json.

**When to use:** Always — ensures new developers who `npm install` have hooks set up.

```json
{
  "scripts": {
    "postinstall": "lefthook install"
  }
}
```

The `lefthook` npm package runs `lefthook install` in its own postinstall. Adding it to project `package.json` scripts is redundant but harmless and makes the intent explicit. Recommended.

### Anti-Patterns to Avoid

- **Running `pytest tests/python/` without `-m "not live"`:** Live tests hit network; will exceed 30s timeout and cause false failures in the pre-push hook. Always use `-m "not live"` in the hook.
- **Using `@evilmartians/lefthook` without awareness:** It's the legacy package that installs all-platform binaries (~60MB). `lefthook` installs only the current OS binary. Both work but `lefthook` is cleaner for a single-developer setup.
- **Assuming `output: false` is enough:** `output: false` suppresses everything including errors. Use `output: [failure, execution_out]` to keep failure details visible.
- **Putting lint and tests in a `piped:` group:** `piped: true` runs commands sequentially and stops on first failure. This is the opposite of what we want — we want parallel execution with all failures shown at once.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Git hook installation | Manual `.git/hooks/pre-push` shell script | lefthook | `.git/` is not committed; every developer would need to manually install. lefthook auto-installs via postinstall |
| Parallel command execution in hook | Shell `&` backgrounding + `wait` + exit code tracking | lefthook `parallel: true` | Exit code aggregation across parallel processes is error-prone; lefthook handles it correctly |
| Timeout enforcement | `timeout 30 command` shell wrapper | lefthook `timeout: "30s"` | Lefthook's per-command timeout is cross-platform and properly kills the process group |
| Output filtering | Redirect stdout/stderr conditionally | lefthook `output:` global config | Lefthook buffers all output and selectively displays based on pass/fail; manual redirection loses output or shows it in wrong order |

**Key insight:** The biggest trap here is the git hooks directory (`.git/hooks/`) being outside version control. Any hand-rolled approach requires every developer to manually run a setup step. Lefthook's postinstall eliminates this.

---

## Common Pitfalls

### Pitfall 1: Python Tool Path Resolution
**What goes wrong:** Lefthook runs commands in a subprocess. If Python tools (ruff, pytest) are managed by pyenv shims, they must be on PATH in the non-interactive shell that lefthook uses.
**Why it happens:** Git hooks execute in a minimal shell environment that may not source `~/.zshrc` or `~/.bash_profile`, which is where pyenv initializes.
**How to avoid:** This project uses pyenv shims at `/Users/annon/.pyenv/shims/`. Lefthook inherits the environment from the shell that calls `git push` — since pyenv is initialized in the interactive shell, shims will be on PATH. Test with `lefthook run pre-push` from the terminal to verify. If it fails, use explicit paths in lefthook.yml: `run: /Users/annon/.pyenv/shims/ruff check pipeline/ tests/` (not recommended — hardcodes path). Better: document the pyenv prerequisite.
**Warning signs:** Hook runs fine interactively but fails with "command not found: ruff" when run in a different terminal context.

### Pitfall 2: `test:fast` vs Hook Parity
**What goes wrong:** `test:fast` and the pre-push hook diverge — one passes, the other fails — misleading the developer.
**Why it happens:** Using different commands, different pytest markers, or different scope in the two contexts.
**How to avoid:** Use the exact same command strings. If `test:fast` runs `npm run lint && pytest tests/python/ -m "not live"` then the hook must run `ruff check pipeline/ tests/` (which `lint:py` calls), `eslint public/js/` (which `lint:js` calls), and `pytest tests/python/ -m "not live"` — same scope, same marker.
**Warning signs:** Success criteria #3 fails — running `npm run test:fast` gives green but `git push` is blocked (or vice versa).

### Pitfall 3: `output:` vs `skip_output:` Confusion
**What goes wrong:** Using `skip_output:` (an older/deprecated key) instead of `output:` (the current global config).
**Why it happens:** Older blog posts and issues reference `skip_output`. The current lefthook schema uses `output` as the global key.
**How to avoid:** Use the `output:` array at the top level of `lefthook.yml`. Verified via official schema.json.
**Warning signs:** The `skip_output` setting is silently ignored; all output appears.

### Pitfall 4: LEFTHOOK_SKIP in CI Environments
**What goes wrong:** If this project ever adds CI, the hooks run during `npm install` in CI unless disabled.
**Why it happens:** lefthook's postinstall runs `lefthook install` in CI unless `CI=true` is set (lefthook detects this and skips).
**How to avoid:** Most CI systems set `CI=true` automatically. Lefthook detects it and skips installation. No action needed for now, but document it.
**Warning signs:** CI npm install fails because lefthook tries to install hooks in a read-only git directory.

### Pitfall 5: Existing `verify` Script Override
**What goes wrong:** The current `verify` script (`python pipeline/main.py && python scripts/verify_summary.py`) is a live data script, not a test suite. Replacing it with the 3-tier test suite changes semantics.
**Why it happens:** CONTEXT.md mandates replacing `verify` with the tiered suite. The old behavior (run pipeline + check output) is removed.
**How to avoid:** Document the change clearly. Old behavior is still runnable directly: `python pipeline/main.py && python scripts/verify_summary.py`. The new `verify` script is now the test-oriented 3-tier command.
**Warning signs:** Developer expects `npm run verify` to refresh production data; it now runs tests instead.

---

## Code Examples

Verified patterns from official sources and schema:

### Complete lefthook.yml for This Project
```yaml
# lefthook.yml
# Source: https://lefthook.dev/configuration/ + schema.json

# Show only failure output — silent on success
output:
  - failure
  - execution_out

pre-push:
  parallel: true
  commands:
    lint-py:
      run: ruff check pipeline/ tests/
      timeout: "30s"
      fail_text: "Push blocked: Python lint errors found. Run npm run test:fast to see details."
    lint-js:
      run: eslint public/js/
      timeout: "30s"
      fail_text: "Push blocked: JS lint errors found. Run npm run test:fast to see details."
    unit-tests:
      run: pytest tests/python/ -m "not live"
      timeout: "30s"
      fail_text: "Push blocked: Unit tests failed. Run npm run test:fast to see details."
```

### Updated package.json scripts block
```json
{
  "scripts": {
    "postinstall": "lefthook install",
    "test": "npx playwright test",
    "test:headed": "npx playwright test --headed",
    "test:fast": "npm run lint && pytest tests/python/ -m \"not live\"",
    "lint:py": "ruff check pipeline/ tests/",
    "lint:js": "eslint public/js/",
    "lint": "npm run lint:py && npm run lint:js",
    "test:python:live": "python -m pytest tests/python/ -m live -v",
    "verify": "npm run test:fast && python -m pytest tests/python/ -m live -v && npx playwright test"
  }
}
```

### Verifying hook installation after npm install
```bash
# Confirm hook was installed
ls -la .git/hooks/pre-push

# Test hook manually without pushing
lefthook run pre-push

# Bypass hook for emergency push
git push --no-verify
```

### Output configuration — show only failures
```yaml
# Show failure summary + actual command output on failure
# Suppress: meta (version header), summary (pass/skip counts), success, execution_info (EXECUTE > lines), skips
output:
  - failure
  - execution_out
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@evilmartians/lefthook` | `lefthook` (recommended) | ~2023-2024 | Old package still works but installs all-platform binaries; new package is lighter |
| `skip_output:` key | `output:` global array | Recent schema update | `skip_output` no longer in schema; use `output:` with explicit list of what to show |
| Manual `"postinstall": "lefthook install"` in package.json | lefthook npm package auto-runs it | Always | Belt-and-suspenders approach still valid and recommended for explicitness |

**Deprecated/outdated:**
- `@evilmartians/lefthook`: Still maintained, not discontinued, but `lefthook` is now recommended. Either works.
- `skip_output`: Not present in current schema.json. Use `output:` instead.

---

## Open Questions

1. **Package name: `lefthook` vs `@evilmartians/lefthook`**
   - What we know: CONTEXT.md says `@evilmartians/lefthook`; official docs say `lefthook` is now recommended
   - What's unclear: User locked `@evilmartians/lefthook` — should the planner honor the exact package name or use the newer recommended one?
   - Recommendation: Honor the user's exact locked decision (`@evilmartians/lefthook`). Flag in the plan that `lefthook` is the newer recommended package but proceed with what was decided.

2. **`test:fast` parity: serial vs parallel execution**
   - What we know: The hook runs lint+tests in parallel; `test:fast` using `npm run lint && pytest` runs them serially
   - What's unclear: The success criteria says "same gate, same exit code" — does "same" mean same parallelism or just same commands and exit behavior?
   - Recommendation: Serial is fine. "Same exit code" is the binding requirement. Both return exit 1 on any failure. Use the simpler serial approach in `test:fast` unless the user specifies otherwise.

3. **Timeout unit format**
   - What we know: The schema.json shows timeout as a string type with example `"15s"`; format is likely Go duration strings (e.g., `"30s"`, `"1m"`)
   - What's unclear: Whether seconds-only format `"30s"` is the only format or if integers (30) also work
   - Recommendation: Use `"30s"` string format — confirmed by schema type definition.

---

## Sources

### Primary (HIGH confidence)
- [lefthook schema.json](https://raw.githubusercontent.com/evilmartians/lefthook/master/schema.json) — Verified `timeout` is a string at command/job/script level; `output` is the global key (not `skip_output`); full option list for commands
- [lefthook.dev/configuration/output.html](https://lefthook.dev/configuration/output.html) — `output` values: meta, summary, empty_summary, success, failure, execution, execution_out, execution_info, skips; global-level; `output: false` disables all except errors
- [lefthook.dev/installation/node.html](https://lefthook.dev/installation/node.html) — Package names: `lefthook` (recommended), `@evilmartians/lefthook` (legacy maintained); postinstall auto-runs on npm; pnpm needs extra config
- [lefthook.dev/usage/env.html](https://lefthook.dev/usage/env.html) — LEFTHOOK=0 to skip; CI=true auto-detected to skip postinstall
- [lefthook.dev/configuration/jobs.html](https://lefthook.dev/configuration/jobs.html) — Job options list including fail_text, run, timeout, parallel, group

### Secondary (MEDIUM confidence)
- [WebSearch results — output control](https://github.com/evilmartians/lefthook/discussions/579) — Community confirmation that `output: [failure, execution_out]` suppresses passing output
- [WebSearch results — lefthook+pytest community patterns](https://dev.to/ajth-in/how-to-use-lefthooks-in-your-node-project-3i83) — Pattern of explicit Python binary path in hook commands when using venv

### Tertiary (LOW confidence)
- Community blog examples — parallel pre-push YAML patterns; not from official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — lefthook is the locked choice; npm package verified; existing tools (ruff, pytest, eslint) already installed
- Architecture: HIGH — lefthook.yml syntax verified via schema.json; output control verified via official docs; no unknowns
- Pitfalls: HIGH (Python path) / MEDIUM (test:fast parity) — pyenv path issue is a real gotcha but verifiable; parity issue is logic-level

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (lefthook is stable; schema unlikely to change)
