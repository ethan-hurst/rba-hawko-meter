# Phase 11: Test Foundation - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver pyproject.toml as config hub, conftest.py with autouse fixtures (DATA_DIR isolation, network blocker), deterministic CSV fixture data, test tiering via `@pytest.mark.live`, and `requirements-dev.txt`. Developer can run `pytest tests/python/ -m "not live"` against isolated test infrastructure with zero risk of reading/writing production data or making network calls.

</domain>

<decisions>
## Implementation Decisions

### Fixture data strategy
- Use real historical data snapshots copied from production CSVs (not synthetic)
- Seed all 7 active indicators: CPI, employment, wages, retail trade, building approvals, housing (ABS RPPI), NAB capacity utilisation
- ~40 rows per fixture CSV — enough for 10-year rolling window Z-score calculations to actually compute
- Fixture CSVs live in `tests/python/fixtures/` directory

### Test directory layout
- Mirror `pipeline/` module structure: `tests/python/test_zscore.py`, `test_gauge.py`, `test_ratios.py`, `test_csv_handler.py`, etc.
- Single `conftest.py` at `tests/python/` with all shared fixtures (DATA_DIR patch, network blocker, CSV loaders)
- Test function naming: `test_<behavior>` — descriptive of what's being verified (e.g., `test_zscore_returns_zero_for_mean_value`, `test_gauge_clamps_at_100`)
- Include smoke tests in Phase 11 to prove infrastructure works end-to-end (DATA_DIR isolation, network blocking, tier separation)

### Network safety scope
- Block at socket level — monkeypatch `socket.socket` to catch ALL outbound connections (requests, urllib, httpx, anything)
- Block everything including localhost/127.0.0.1 — no exceptions for non-live tests
- On violation: raise `RuntimeError('Network access blocked in tests. Use @pytest.mark.live for tests requiring network.')`
- Auto-disable for `@pytest.mark.live` — autouse fixture checks markers and steps aside for live-marked tests

### Claude's Discretion
- Exact pyproject.toml structure and ruff rule selection
- conftest.py fixture implementation details
- How fixture CSVs are loaded (fixture functions vs pytest-datadir vs manual)
- Smoke test specifics beyond what success criteria require

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches. Key constraint from STATE.md: `DATA_DIR = Path("data")` in `pipeline/config.py` is a relative path — all tests must patch this via autouse fixture or they silently read/write live CSV files.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 11-test-foundation*
*Context gathered: 2026-02-25*
