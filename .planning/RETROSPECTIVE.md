# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v4.0 — Dashboard Visual Overhaul

**Shipped:** 2026-02-26
**Phases:** 3 | **Plans:** 3

### What Was Built
- Hero section DOM restructure with Inter font, zone-coloured border, hawk score display, and fadeSlideIn animation
- Verdict explanation component ranking top hawkish/dovish indicators with ASIC-compliant hedged language
- Typography hierarchy, zone colour audit, spacing standardisation across entire dashboard
- CountUp.js animated score and Plotly gauge sweep with prefers-reduced-motion guards

### What Worked
- Research phase (v4.0 pitfalls documented in MEMORY.md) prevented all 5 predicted issues: Plotly zero-width, Tailwind class drop, ASIC copy, Playwright selectors, mobile congestion
- Single-plan phases (1 plan per phase) kept scope tight and execution fast
- Zone colour constraint (exactly 3 element types) created a clear design rule that was easy to verify

### What Was Inefficient
- Phase 21 SUMMARY.md was never created during execution — had to be backfilled during milestone completion
- Phase 23 plan said "TBD" in roadmap but was actually planned and executed — roadmap wasn't updated to reflect the plan count

### Patterns Established
- `element.style` for dynamic colours (never Tailwind class concatenation with CDN)
- Double `requestAnimationFrame` for Plotly after DOM restructure
- Shared `reducedMotion` check at top of render callback for multiple animations
- CDN script tags with static fallback pattern (CountUp.js)

### Key Lessons
1. Always create SUMMARY.md immediately after plan execution — backfilling loses context
2. Research-driven pitfall lists are extremely valuable for frontend work with Plotly/Tailwind CDN constraints
3. Animation accessibility (prefers-reduced-motion) should be a first-class requirement, not an afterthought

### Cost Observations
- Model mix: ~70% opus, ~30% sonnet (research + planning in opus, execution mixed)
- Sessions: ~3 (one per phase)
- Notable: v4.0 was the fastest milestone (1 day, 3 phases) — pre-research eliminated all rework

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 7 | 19 | Initial project setup, learning workflow |
| v1.1 | 3 | 6 | Scraper patterns established |
| v2.0 | 7 | 11 | Test infrastructure from scratch |
| v3.0 | 3 | 6 | Coverage enforcement automated |
| v4.0 | 3 | 3 | Research-first eliminated rework |

### Cumulative Quality

| Milestone | Tests | Coverage | JS LOC |
|-----------|-------|----------|--------|
| v1.0 | 24 Playwright | — | ~2,750 |
| v1.1 | 28 Playwright | — | ~3,049 |
| v2.0 | 60+ pytest + 28 PW | Baseline | ~2,510 |
| v3.0 | 411 pytest + 28 PW | 85%+ all modules | ~2,510 |
| v4.0 | 421 pytest + 28 PW | 85%+ all modules | ~3,664 |

### Top Lessons (Verified Across Milestones)

1. Research before planning prevents the most expensive rework (verified v1.1, v4.0)
2. Per-module coverage enforcement catches regressions that global thresholds miss (verified v3.0, v4.0)
3. Scraper fragility is the primary maintenance risk — always build fallback hierarchies (verified v1.0, v1.1)
