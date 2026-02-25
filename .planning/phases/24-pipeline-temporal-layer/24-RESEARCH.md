# Phase 24: Pipeline Temporal Layer - Research

**Researched:** 2026-02-26
**Domain:** Python pipeline snapshotting, JSON temporal diff, file-based archive management
**Confidence:** HIGH

## Summary

Phase 24 adds a temporal layer to the existing Python data pipeline. The core work is: (1) snapshot the current `status.json` before each pipeline run, (2) load the previous snapshot and compute deltas, (3) inject `previous_value`, `delta`, and `direction` fields into each gauge entry and the overall block, and (4) enforce a rolling 52-entry retention cap.

The implementation is straightforward because the existing pipeline already produces a well-structured `status.json` with all gauge values. The archive module simply copies this file to a dated snapshot, reads the prior snapshot for comparison, and enriches the output. No new external dependencies are needed — only `json`, `os`, `pathlib`, and `datetime` from the Python standard library.

**Primary recommendation:** Create a single `pipeline/normalize/archive.py` module with three pure functions: `save_snapshot()`, `read_previous_snapshot()`, and `inject_deltas()`. Integrate into `generate_status()` in engine.py after the status dict is built but before writing to disk.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SNAP-01 | Pipeline archives current status.json as snapshot before each weekly run | `save_snapshot()` copies status dict to `public/data/snapshots/YYYY-MM-DD.json` and updates `index.json` |
| SNAP-02 | Pipeline injects `previous_value` and `delta` fields into each gauge entry | `inject_deltas()` reads prior snapshot, computes gauge-level deltas, adds `previous_value`, `delta`, `direction` |
| SNAP-03 | Pipeline injects `previous_hawk_score` and `hawk_score_delta` into overall block | Same `inject_deltas()` function handles overall block enrichment |
| SNAP-04 | Snapshot storage enforces rolling retention cap (max 52 entries) | `save_snapshot()` prunes oldest entries from index.json and deletes stale files when count > 52 |
| SNAP-05 | Archive module has unit tests at 85%+ coverage | Tests in `tests/python/test_archive.py` using tmp_path fixtures, matching existing test patterns |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| json (stdlib) | N/A | Read/write snapshot JSON files | Already used throughout pipeline |
| pathlib (stdlib) | N/A | Path manipulation for snapshot directory | Already used in config.py |
| datetime (stdlib) | N/A | Date formatting for snapshot filenames | Already used in engine.py |
| shutil (stdlib) | N/A | File copy for snapshot archival | Standard library, no external dep |

### Supporting
No additional libraries needed. The entire feature uses Python standard library only.

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Per-file JSON snapshots | SQLite database | Overkill for 52 files; harder to inspect/debug; git-auto-commit can't track binary |
| Rolling file deletion | Log rotation library | Adds external dependency for trivial task |
| Manual JSON diff | deepdiff library | Only need shallow key comparison; deepdiff is heavy |

## Architecture Patterns

### Recommended Module Structure
```
pipeline/
├── normalize/
│   ├── archive.py          # NEW: snapshot save/load/delta injection
│   ├── engine.py           # MODIFIED: call archive functions
│   ├── gauge.py            # unchanged
│   ├── zscore.py           # unchanged
│   └── ratios.py           # unchanged
public/
├── data/
│   ├── status.json         # MODIFIED: now contains delta fields
│   └── snapshots/          # NEW directory
│       ├── index.json      # NEW: ordered list of snapshot dates
│       ├── 2026-02-26.json # snapshot files
│       └── ...
```

### Pattern 1: Snapshot-Before-Write
**What:** Save the current status dict as a dated snapshot before enriching it with deltas and writing to status.json.
**When to use:** Every pipeline run (weekly via GitHub Actions, or manual).
**Flow:**
```python
# In engine.py generate_status(), after building status dict:
# 1. Save snapshot of the CURRENT run's raw values
save_snapshot(status, snapshots_dir)
# 2. Read the PREVIOUS snapshot (not the one we just saved)
previous = read_previous_snapshot(snapshots_dir)
# 3. Inject deltas by comparing current vs previous
inject_deltas(status, previous)
# 4. Write enriched status.json (existing code)
```

### Pattern 2: min_age_days Guard
**What:** When reading the previous snapshot, skip any snapshot less than `min_age_days` old (default 5) to prevent same-week double-runs from treating the current run as the "previous".
**When to use:** `read_previous_snapshot()` — filter index.json entries by age.
**Why:** The pipeline can be triggered manually or re-run on failure. Without this guard, a re-run on Tuesday would see Monday's snapshot as "previous" and show zero deltas.

### Pattern 3: Graceful First-Run
**What:** On the very first pipeline run (no prior snapshot exists), `read_previous_snapshot()` returns `None`. `inject_deltas()` receives `None` and simply skips adding delta fields.
**When to use:** Always — the function must be None-safe.
**Why:** SNAP-04 requirement: "all delta fields are absent and the frontend handles this gracefully."

### Anti-Patterns to Avoid
- **Reading status.json from disk as "previous":** The file on disk is the LAST written output, which may be from the same run if the pipeline crashed and restarted. Always read from the snapshots directory.
- **Using history[-2] as proxy for previous_value:** The history array contains z-score-derived gauge values at mixed cadences (quarterly ABS, monthly NAB). It does NOT represent weekly pipeline runs. This is explicitly out of scope per REQUIREMENTS.md.
- **Storing snapshots in data/ directory:** Snapshots go in `public/data/snapshots/` so they're accessible to the frontend for Phase 27 (Historical Chart). The git-auto-commit-action file_pattern must be updated.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date formatting | Custom date string parsing | `datetime.strptime`/`strftime` with `%Y-%m-%d` | ISO format, no ambiguity |
| JSON schema validation | Custom validator for snapshot format | Simple key existence checks | Snapshot format matches status.json exactly; overkill to validate schema |
| File locking | flock/lockfile for concurrent access | Pipeline runs are serialized by GitHub Actions concurrency group | `concurrency.cancel-in-progress: false` already prevents parallel runs |

**Key insight:** The entire temporal layer is file I/O + arithmetic. No external libraries needed.

## Common Pitfalls

### Pitfall 1: Snapshot Directory Not Committed
**What goes wrong:** `public/data/snapshots/` is created locally but the git-auto-commit-action doesn't include it in the commit pattern.
**Why it happens:** The current `file_pattern` in weekly-pipeline.yml is `'data/*.csv public/data/status.json'` — doesn't match `public/data/snapshots/*.json`.
**How to avoid:** Update `file_pattern` to `'data/*.csv public/data/status.json public/data/snapshots/*.json public/data/snapshots/index.json'`.
**Warning signs:** Snapshots exist locally but not in the git history after a pipeline run.

### Pitfall 2: Race Between Save and Read
**What goes wrong:** `save_snapshot()` writes today's snapshot, then `read_previous_snapshot()` reads today's snapshot as "previous", yielding zero deltas.
**Why it happens:** The index.json is updated before filtering by min_age_days.
**How to avoid:** `read_previous_snapshot()` must exclude the current date (today) from candidates. The min_age_days=5 guard handles this, but also explicitly exclude today's date as a belt-and-suspenders approach.

### Pitfall 3: Floating Point Delta Noise
**What goes wrong:** Delta shows as 0.0999999999 instead of 0.1 due to IEEE 754.
**Why it happens:** Subtracting two rounded floats can produce long decimals.
**How to avoid:** Round deltas to 1 decimal place (matching gauge value precision). `round(current - previous, 1)`.

### Pitfall 4: Missing Gauge in Previous Snapshot
**What goes wrong:** A new indicator was added between snapshots. Previous snapshot has 6 gauges, current has 7.
**Why it happens:** Optional indicators (housing, business_confidence) may appear/disappear.
**How to avoid:** `inject_deltas()` iterates over current gauges and uses `.get()` on previous — if gauge doesn't exist in previous, skip delta for that gauge.

## Code Examples

### save_snapshot()
```python
def save_snapshot(status_dict, snapshots_dir, max_entries=52):
    """Save dated snapshot and maintain rolling index."""
    snapshots_dir = Path(snapshots_dir)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.utcnow().strftime('%Y-%m-%d')
    snapshot_path = snapshots_dir / f"{today}.json"

    # Write snapshot
    with open(snapshot_path, 'w') as f:
        json.dump(status_dict, f, indent=2)

    # Update index
    index_path = snapshots_dir / "index.json"
    if index_path.exists():
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {"snapshots": []}

    # Add today if not already present (idempotent)
    if today not in index["snapshots"]:
        index["snapshots"].append(today)
        index["snapshots"].sort()

    # Enforce rolling cap
    while len(index["snapshots"]) > max_entries:
        oldest = index["snapshots"].pop(0)
        oldest_path = snapshots_dir / f"{oldest}.json"
        if oldest_path.exists():
            oldest_path.unlink()

    with open(index_path, 'w') as f:
        json.dump(index, f, indent=2)
```

### read_previous_snapshot()
```python
def read_previous_snapshot(snapshots_dir, min_age_days=5):
    """Read the most recent snapshot that is at least min_age_days old."""
    snapshots_dir = Path(snapshots_dir)
    index_path = snapshots_dir / "index.json"

    if not index_path.exists():
        return None

    with open(index_path) as f:
        index = json.load(f)

    today = datetime.utcnow().date()

    # Walk backwards through sorted dates
    for date_str in reversed(index["snapshots"]):
        snap_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        age = (today - snap_date).days
        if age >= min_age_days:
            snap_path = snapshots_dir / f"{date_str}.json"
            if snap_path.exists():
                with open(snap_path) as f:
                    return json.load(f)

    return None
```

### inject_deltas()
```python
def inject_deltas(status_dict, previous_snapshot):
    """Inject delta fields into status dict by comparing with previous snapshot."""
    if previous_snapshot is None:
        return  # First run — no deltas to inject

    # Overall block
    prev_score = previous_snapshot.get('overall', {}).get('hawk_score')
    if prev_score is not None:
        curr_score = status_dict['overall']['hawk_score']
        status_dict['overall']['previous_hawk_score'] = prev_score
        status_dict['overall']['hawk_score_delta'] = round(curr_score - prev_score, 1)

    # Per-gauge deltas
    prev_gauges = previous_snapshot.get('gauges', {})
    for name, gauge in status_dict.get('gauges', {}).items():
        prev_gauge = prev_gauges.get(name)
        if prev_gauge is None:
            continue  # New indicator — no previous value

        prev_value = prev_gauge.get('value')
        if prev_value is not None:
            curr_value = gauge['value']
            delta = round(curr_value - prev_value, 1)
            gauge['previous_value'] = prev_value
            gauge['delta'] = delta

            # Direction
            if delta > 0:
                gauge['direction'] = 'up'
            elif delta < 0:
                gauge['direction'] = 'down'
            else:
                gauge['direction'] = 'unchanged'
```

### Integration in engine.py
```python
# At top of engine.py, add import:
from pipeline.normalize.archive import (
    save_snapshot, read_previous_snapshot, inject_deltas
)

# In generate_status(), after building status dict but BEFORE writing:
SNAPSHOTS_DIR = Path("public") / "data" / "snapshots"
save_snapshot(status, SNAPSHOTS_DIR)
previous = read_previous_snapshot(SNAPSHOTS_DIR)
inject_deltas(status, previous)

# Existing write code follows unchanged
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No temporal data | Point-in-time status.json only | Current state | Frontend shows current values only |
| After Phase 24 | Snapshot archive + delta injection | This phase | Frontend can show direction of change |

## Open Questions

1. **Snapshot timing relative to normalization**
   - What we know: `generate_status()` builds the status dict, then writes it
   - What's unclear: Should we snapshot BEFORE or AFTER the current run's normalization?
   - Recommendation: Snapshot the current run's output (post-normalization). The "previous" is always a prior week's post-normalization output. This means the first run saves a snapshot but has no deltas. Second run reads the first snapshot as "previous" and computes deltas.

2. **Daily ASX futures pipeline interaction**
   - What we know: `daily-asx-futures.yml` runs separately and updates `data/asx_futures.csv` + `public/data/status.json`
   - What's unclear: Should the daily pipeline also snapshot?
   - Recommendation: NO. Only the weekly pipeline snapshots. The daily pipeline only updates ASX futures data and does NOT run the full normalization engine. Snapshots represent weekly full-pipeline state.

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `pipeline/main.py`, `pipeline/normalize/engine.py`, `pipeline/config.py` — direct file reads
- Codebase analysis: `.github/workflows/weekly-pipeline.yml` — GitHub Actions configuration
- Codebase analysis: `public/data/status.json` — current output format with all gauge fields

### Secondary (MEDIUM confidence)
- Project MEMORY.md: Established constraints (min_age_days=5, 52-entry cap, per-file storage in public/data/snapshots/)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Python stdlib only, no external dependencies
- Architecture: HIGH - Direct codebase analysis, clear integration point in engine.py
- Pitfalls: HIGH - Well-understood file I/O patterns; git-auto-commit pattern already proven

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable domain, no external API dependencies)
