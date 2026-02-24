---
phase: 05-calculator-compliance
plan: 02
subsystem: compliance
tags: [asic, rg-244, disclaimer, accessibility, neutral-language]
dependency-graph:
  requires: [05-01, 04-01, 04-02]
  provides: [asic-compliance, accessibility-audit]
  affects: []
tech-stack:
  added: []
  patterns: [asic-rg-244-four-test-framework]
key-files:
  created: []
  modified:
    - public/index.html
decisions:
  - id: footer-disclaimer-rewrite
    title: "Footer disclaimer rewritten to ASIC RG 244 specification"
    rationale: "Original Phase 2 disclaimer lacked AFS Licence statement, non-endorsement note, and personal circumstances caveat"
  - id: rate-hike-cut-labels
    title: "ASX Futures 'Rate Hike'/'Rate Cut' labels kept as-is"
    rationale: "Standard financial terminology for factual outcome descriptions, consistent with ASX's own labeling"
metrics:
  duration: "3 minutes"
  completed: "2026-02-06"
---

# Phase 5 Plan 02: ASIC Compliance Audit Summary

**One-liner:** Full ASIC RG 244 compliance audit across HTML and JS -- footer disclaimer rewritten with all required elements, zero risky language found, accessibility verified.

## What Was Audited

### Task 1: HTML Content Audit
Applied ASIC RG 244 four-test framework (Data Not Opinion, Action Implication, Reasonable Person, Educational Framing) to every text element in index.html.

**Findings and fixes:**
- **Footer disclaimer rewritten** with all required elements:
  - "General Information Only" heading (was just a span label)
  - Not financial advice, recommendation, or forecast
  - Does not take into account personal objectives, financial situation, or needs (was missing)
  - Speak to a licensed financial adviser (was present)
  - Creators do not hold AFS Licence (was missing)
- **ASX data source attribution** clarified: "Market-implied probabilities derived from ASX 30 Day Interbank Cash Rate Futures"
- **Non-endorsement statement** added: "These organisations do not endorse this website" (was missing)

**Items verified as compliant (no changes needed):**
- Disclaimer banner: "General Information Only" visible at top
- Calculator heading: "Explore Rate Scenarios" (educational framing)
- Calculator intro: "typical Australian mortgage" (not "your mortgage")
- Calculator disclaimer: "Illustrative Estimates Only"
- Source citations: present on cash rate, chart, calculator
- No risky language patterns found (prediction, forecast, you should, etc.)

### Task 2: JavaScript Content Audit
Searched all 7 JS files for risky language patterns, innerHTML usage, and non-neutral text.

**Results: zero issues found.**
- No innerHTML in any JS file (all use createElement/textContent)
- No risky language patterns (prediction, forecast, you should, we recommend, your mortgage)
- Gauge labels use "HAWKISH"/"DOVISH"/"NEUTRAL" (not "Danger"/"Safe")
- ASX table uses "Rate Cut"/"Hold"/"Rate Hike" (standard factual terminology)
- Interpretation text is data-driven: "CPI at X% -- above/below target band" (factual, not advisory)

### Task 3: Accessibility Audit
Verified calculator and dashboard accessibility.

**Results: all checks pass.**
- 6 labels with matching `for` attributes (5 inputs + slider)
- 3 `aria-describedby` help text connections
- Slider: aria-valuenow, aria-valuetext, aria-valuemin, aria-valuemax
- Output element with aria-live="polite" paired to slider
- Results area with aria-live="polite"
- Comparison table: caption, thead, th scope="col"
- All focus:outline-none paired with focus:ring-2 (visible ring indicator)
- Color is not sole indicator (difference values show +$X/-$X text alongside colors)

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | fa566ef | feat(05-02): audit HTML content for ASIC RG 244 compliance |
| 2 | -- | No changes needed (all JS already compliant) |
| 3 | -- | No changes needed (all accessibility requirements met) |

## Decisions Made

1. **Footer disclaimer rewrite**: Restructured from single paragraph to three separate paragraphs matching ASIC RG 244 recommendations from the research document.

2. **ASX labels kept**: "Rate Hike" and "Rate Cut" are standard financial terminology describing factual market outcomes, consistent with ASX's own labeling on their RBA Rate Tracker.

## Deviations from Plan

None -- plan executed as written. Tasks 2 and 3 required no code changes (audit passed with zero issues).

## Self-Check: PASSED
