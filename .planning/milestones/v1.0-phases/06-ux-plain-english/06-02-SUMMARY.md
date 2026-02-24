---
phase: 06-ux-plain-english
plan: 02
subsystem: frontend-ux
tags: [plain-english, ux, accessibility, asic-rg-244, data-quality]

dependency-graph:
  requires: [06-01-plain-labels]
  provides:
    - plain-english-metric-cards
    - data-quality-guard
    - importance-badges
    - contextual-helpers
    - australian-date-format
    - plain-verdict
    - coverage-notice
  affects: []

tech-stack:
  added: []
  patterns:
    - plain-english-interpretations
    - data-quality-guards
    - contextual-help-text
    - asic-compliant-language

key-files:
  created: []
  modified:
    - public/js/interpretations.js
    - public/js/gauge-init.js
    - public/index.html

decisions:
  - title: "Data quality guard for building approvals"
    context: "Building approvals raw_value of -99.91% is bogus (mixed ABS series data)"
    decision: "Guard function isDataSuspect filters values < -90 or > 500, shows 'data is currently being updated'"
    rationale: "Prevents users from seeing misleading -99.9% YoY statistic"
    alternatives: ["Show asterisk with footnote", "Hide card entirely"]

  - title: "Importance labels instead of percentages"
    context: "Weight badges showed '25% weight' - jargon for layperson users"
    decision: "Map to High/Medium/Lower importance labels, show percentage on hover"
    rationale: "Users care about relative importance, not mathematical weight values"
    alternatives: ["Stars (1-3)", "Low/Medium/High only"]

  - title: "Australian date format throughout"
    context: "ISO dates (2025-12-01) are less readable for Australian users"
    decision: "Use Intl.DateTimeFormat with en-AU locale (1 Dec 2025)"
    rationale: "Matches Australian conventions, improves readability"
    alternatives: ["US format (Dec 1, 2025)", "Keep ISO"]

  - title: "Plain verdict based on score ranges"
    context: "Pipeline verdict 'Economic indicators are broadly balanced' is vague"
    decision: "Map hawk_score to 5 plain English verdicts with ASIC-compliant language"
    rationale: "Users get actionable context without financial advice trigger language"
    alternatives: ["Keep pipeline verdict", "Add emoji indicators"]

metrics:
  duration: 226s
  tasks: 3
  commits: 3
  files-modified: 3
  completed: 2026-02-06
---

# Phase 06 Plan 02: Plain English Rewrite Summary

**One-liner:** All metric cards and verdict rewritten in plain Australian English with data quality guards, importance labels, and contextual helpers for layperson understanding.

## What Was Built

### Core Deliverables

1. **Data Quality Guard System**
   - `isDataSuspect()` function filters bogus building approvals data
   - Prevents -99.9% YoY from showing to users
   - Shows "Building approvals data is currently being updated" instead
   - Guards check raw_value < -90 or > 500 for building approvals

2. **Plain English Metric Interpretations**
   - Inflation: "Prices up 1.4% over the past year — within the RBA's 2–3% target"
   - Wages: "Wages up 1.6% over the past year — moderate growth"
   - Employment: "The job market is steady — balanced conditions"
   - Housing: "House prices are growing at a moderate pace"
   - Spending: "Consumer spending is at moderate levels"
   - Building approvals: Qualitative descriptions only (no bogus raw values)
   - Business confidence: "Business confidence is around average levels"

3. **Contextual Helpers**
   - `getWhyItMatters()`: One-liner explaining rate relevance per indicator
   - Example: "When prices rise too fast, the RBA tends to raise interest rates to slow things down."
   - Appears below each metric interpretation in italic gray text

4. **Weight Badges as Importance Labels**
   - High importance: 20%+ weight (inflation at 25%)
   - Medium importance: 10–19% weight (wages, employment, housing at 15%)
   - Lower importance: <10% weight (building approvals, business confidence at 5%)
   - Hover shows actual percentage: "25% of overall score"

5. **Stale Data Age Display**
   - Replaces "(stale)" with descriptive age
   - Example: "(7 months old — newer data not yet available)"
   - Calculates months from staleness_days (220 days / 30 = 7 months)

6. **Australian Date Format**
   - `formatAusDate()` helper using Intl.DateTimeFormat
   - "Data as of 1 Dec 2025" instead of "Data as of 2025-12-01"
   - Applied to all source citations

7. **Plain English Verdict**
   - `getPlainVerdict()` maps hawk_score to 5 ranges
   - <20: "The economy is showing significant signs of slowing. Interest rates are more likely to come down."
   - 20–40: "Interest rates may be more likely to fall than rise."
   - 40–60: "Interest rates are likely to stay where they are for now."
   - 60–80: "Interest rates may be more likely to rise than fall."
   - >80: "Interest rates are more likely to go up."
   - Uses careful ASIC-compliant language: "likely to", "may be more likely"

8. **Data Coverage Notice**
   - Shows "Based on 3 of 8 indicators (more data coming soon)"
   - Counts available indicators (orderedIds.length)
   - Total hardcoded as 8 (7 core + asx_futures excluded from count)
   - Only shown when available < total

### Files Modified

**public/js/interpretations.js** (125 lines changed)
- Added: `isDataSuspect()`, `formatAusDate()`, `getWhyItMatters()`, `getPlainVerdict()`
- Rewrote: `generateMetricInterpretation()` with plain English for all 7 indicators
- Updated: `renderMetricCard()` with importance labels, stale age, why-it-matters, Australian dates
- Updated: `renderVerdict()` to use `getPlainVerdict()` instead of pipeline verdict
- Exported: All new helper functions

**public/js/gauge-init.js** (11 lines added)
- Added: Data coverage notice rendering in `renderMetricGauges()`
- Calculates available vs total indicators
- Populates `data-coverage-notice` element

**public/index.html** (1 line added)
- Added: `<p id="data-coverage-notice">` container below Economic Indicators heading

## Task Breakdown

### Task 1: Data Quality Guard & Plain English Interpretations
**Commit:** `f570e53`
**Duration:** ~90 seconds

Added data quality guard system and rewrote all metric interpretations:

- `isDataSuspect()` checks building approvals for raw_value < -90 or > 500
- Returns "Building approvals data is currently being updated" when suspect
- Rewrote 7 indicator interpretations in plain English:
  - Removed jargon: "CPI", "YoY", "WPI", "labour market"
  - Added context: RBA target bands, explanations of what metrics mean
  - Building approvals: qualitative only (no raw values shown)
- Added `getWhyItMatters()` with 7 rate-relevance explanations
- Added `getPlainVerdict()` with 5 ASIC-compliant verdict ranges
- Added `formatAusDate()` for Australian date format
- Exported all new helpers

**Files:** interpretations.js

### Task 2: Metric Card Updates
**Commit:** `31a61b8`
**Duration:** ~80 seconds

Updated `renderMetricCard()` to use plain English labels and add context:

- Replaced weight percentage with importance labels
- Added hover title showing actual percentage
- Replaced "(stale)" with age in months + context message
- Changed source dates to Australian format via `formatAusDate()`
- Added why-it-matters one-liner below interpretation

**Files:** interpretations.js

### Task 3: Plain Verdict & Coverage Notice
**Commit:** `7378326`
**Duration:** ~56 seconds

Updated verdict and added data coverage notice:

- Modified `renderVerdict()` to use `getPlainVerdict()` helper
- Generates verdict from hawk_score instead of pipeline verdict field
- Added `data-coverage-notice` container to index.html
- Implemented coverage rendering in gauge-init.js
- Shows "Based on X of 8 indicators (more data coming soon)"

**Files:** interpretations.js, gauge-init.js, index.html

## Technical Patterns Established

### 1. Data Quality Guards
Pattern for filtering unreliable data before presentation:

```javascript
function isDataSuspect(metricId, metricData) {
  if (metricId === 'building_approvals') {
    var raw = parseFloat(metricData.raw_value);
    if (isNaN(raw) || raw < -90 || raw > 500) return true;
  }
  return false;
}
```

Extensible to other indicators with known data quality issues.

### 2. Contextual Help Text
Pattern for adding explanatory one-liners:

```javascript
var whyText = getWhyItMatters(metricId);
if (whyText) {
  var whyDiv = document.createElement('div');
  whyDiv.className = 'text-xs text-gray-500 mt-1 italic';
  whyDiv.textContent = whyText;
  card.appendChild(whyDiv);
}
```

Keeps cards scannable while providing context on demand.

### 3. ASIC-Compliant Language Mapping
Pattern for score ranges to compliant verdict text:

```javascript
if (score < 20) return 'Interest rates are more likely to come down.';
if (score < 40) return 'Interest rates may be more likely to fall than rise.';
```

Uses "likely to", "may be more likely" — never "will", "should", "we recommend".

### 4. Importance Label Mapping
Pattern for mapping continuous weights to discrete labels:

```javascript
var pct = Math.round(weight * 100);
if (pct >= 20) importanceLabel = 'High importance';
else if (pct >= 10) importanceLabel = 'Medium importance';
else importanceLabel = 'Lower importance';
```

Thresholds: 20% = high, 10% = medium, <10% = lower.

## Deviations from Plan

None - plan executed exactly as written.

## Decisions Made

See frontmatter `decisions` section for full details.

Key decisions:
1. **Data quality guard** filters building approvals < -90 or > 500
2. **Importance labels** use 20%/10% thresholds for High/Medium/Lower
3. **Australian date format** via Intl.DateTimeFormat with en-AU locale
4. **Plain verdict** maps hawk_score to 5 ranges with ASIC-compliant language

## Integration Points

### Upstream Dependencies
- **06-01**: Zone labels already changed to plain English (RATES LIKELY FALLING/RISING)
- **GaugesModule**: Provides `getDisplayLabel()`, `getZoneColor()`, `getStanceLabel()`
- **status.json**: Provides gauge data structure with raw_value, staleness_days, weight

### Downstream Effects
- **Future plans**: Can use `getWhyItMatters()` for tooltips, help modals
- **ASIC compliance**: `getPlainVerdict()` pattern extends to other auto-generated text
- **Data quality**: `isDataSuspect()` pattern extends to other indicators with quality issues

## Verification Results

✅ All verification criteria met:

1. **Data quality guard**: isDataSuspect filters building approvals -99.91
2. **Plain English**: "Prices up 1.4% over the past year" not "CPI at 1.4% YoY"
3. **Why it matters**: 7 one-liners present for each indicator
4. **Weight badges**: High/Medium/Lower importance labels with hover showing percentage
5. **Stale labels**: "(7 months old — newer data not yet available)" not "(stale)"
6. **Verdict**: Uses getPlainVerdict with ASIC-compliant language
7. **Australian dates**: All source citations show "1 Dec 2025" format
8. **Coverage notice**: Container exists in HTML, rendering logic in gauge-init.js
9. **No innerHTML**: Only reference is in header comment
10. **ASIC compliance**: No "will", "should", "we recommend" in user-facing text

Grep checks passed:
- `isDataSuspect`: 3 matches (definition, usage, export)
- `getWhyItMatters`: 2 matches (definition, usage)
- `formatAusDate`: 2 matches (definition, usage)
- `getPlainVerdict`: 3 matches (definition, usage, export)
- `Prices up`: 3 matches (plain English inflation text)
- `CPI`: 0 matches in interpretation text
- `YoY`: 0 matches in interpretation text
- Prohibited language: 0 matches

## Next Phase Readiness

**Status:** Ready for next phase

**Blockers:** None

**Concerns:** None

**Notes:**
- All 8 must-have truths implemented
- Zero jargon remaining in metric card text
- ASIC RG 244 compliance maintained throughout
- Data quality guard prevents bogus building approvals from showing

## Performance

- **Total duration:** 226 seconds (~3.8 minutes)
- **Average per task:** 75 seconds
- **Commits:** 3 atomic commits (1 per task)
- **Lines changed:** ~137 across 3 files

**Velocity:** 1.32 tasks/minute

## Learnings

1. **Data quality guards are essential** when working with mixed-series data
2. **Plain English requires domain knowledge** of what metrics actually mean
3. **ASIC compliance needs careful language** - "likely to" not "will"
4. **Importance labels > percentages** for layperson UX
5. **Contextual help text** (why it matters) bridges technical metrics to user concerns

## Self-Check

### Created Files
- None (all modifications to existing files)

### Modified Files
✅ public/js/interpretations.js - exists and modified
✅ public/js/gauge-init.js - exists and modified
✅ public/index.html - exists and modified

### Commits
✅ f570e53 - feat(06-02): add data quality guard and plain English interpretations
✅ 31a61b8 - feat(06-02): update metric cards with plain English labels and context
✅ 7378326 - feat(06-02): add plain English verdict and data coverage notice

## Self-Check: PASSED

All files and commits verified present.
