# Milestones

## v1.0 MVP (Shipped: 2026-02-24)

**Phases completed:** 7 phases, 19 plans, 8 tasks

**Key accomplishments:**
- Automated data pipeline ingesting 5 ABS indicators + RBA cash rate via weekly GitHub Actions
- Interactive dark-theme dashboard with Plotly.js rate chart (1Y/5Y/10Y), live RBA meeting countdown, deployed on Netlify
- Z-score normalization engine (median/MAD) transforming diverse economic metrics into 0-100 gauge scale
- Hawk-O-Meter with hero semicircle gauge + 6 individual bullet gauges (Blue/Grey/Red colorblind-accessible scheme)
- Mortgage impact calculator with Decimal.js precision, scenario slider, ASIC RG 244 compliance
- Plain English UX overhaul — layperson-friendly labels, data quality guards, neutral verdict language
- ASX Futures integration with daily CI/CD automation and graceful degradation

**Known Gaps:**
- PIPE-03: CoreLogic scraper placeholder (graceful degradation)
- PIPE-04: NAB capacity survey placeholder (graceful degradation)
- HAWK-04: ASX endpoints 404 (external API change, implemented with graceful degradation)

**Stats:**
- Timeline: 2026-02-04 → 2026-02-24 (20 days)
- Commits: 81
- LOC: ~5,900 (2,683 Python + 2,750 JS + 468 HTML)
- Tests: 24 Playwright tests (100% pass)

---

