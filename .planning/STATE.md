# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** "Data, not opinion." Empowers laypeople to understand interest rate drivers without relying on media sensationalism or biased advice.
**Current focus:** Phase 9 complete — moving to Phase 10 NAB Capacity Utilisation Gauge (v1.1 in progress)

## Current Position

Phase: 9 of 10 (Housing Prices Gauge — COMPLETE)
Plan: 2 of 2 in phase 09 (09-01 ABS RPPI, 09-02 Cotality HVI scraper — both complete)
Status: In progress (Phase 9 done, Phase 10 pending)
Last activity: 2026-02-24 — 09-02 complete: Cotality HVI PDF scraper, hybrid normalization, 26/26 Playwright tests, HOUS-03+HOUS-04 satisfied

Progress: [████████░░] 75% (7.5 of 10 phases complete — v1.0 shipped, v1.1 in progress)

## Performance Metrics

**Velocity (v1.0):**
- Total plans completed: 19
- v1.0 timeline: 20 days (2026-02-04 → 2026-02-24)
- Commits: 81

**v1.1 (in progress):**

| Phase | Plans | Status |
|-------|-------|--------|
| 8. ASX Futures Live Data | 2 | Complete (08-01 pipeline, 08-02 frontend table) |
| 9. Housing Prices Gauge | 2 | Complete (09-01 ABS RPPI + frontend, 09-02 Cotality HVI scraper) |
| 10. NAB Capacity Utilisation Gauge | TBD | Not started |

## Accumulated Context

### Decisions

- [v1.0] ABS is primary housing source — Cotality ToS (Clause 8.4d) prohibits automated scraping; ABS RPPI activates gauge even with stale Dec 2021 data
- [v1.0] ASX futures excluded from hawk score — market-derived, not economic indicator; displayed separately in "What Markets Expect"
- [v1.1] NAB HTML extraction first — capacity utilisation figure is inline in HTML body; PDF is fallback only, not primary approach
- [v1.1] URL discovery required for NAB — never construct NAB URLs from date templates; always discover via tag archive page
- [08-01] CI freshness step uses continue-on-error: true — intermittent ASX outages must not block data commits
- [08-01] meetings[] contract extension is additive — all existing single-meeting fields preserved for backward compatibility
- [08-01] Cross-platform day formatting via str(dt.day) — %-d strftime is Linux/macOS only, crashes on Windows CI
- [08-02] ASX section always visible — container.style.display='' unconditionally; placeholder shown when meetings[] null/empty
- [08-02] Traffic light colors replace old blue/gray/red — green (#10b981) cut, amber (#f59e0b) hold, red (#ef4444) hike
- [09-01] Neutral zone threshold is +/-1% YoY for housing STEADY label — conservative range, RISING in practice with ABS data at +23.67%
- [09-01] data_source read from raw CSV in build_gauge_entry() — z-score pipeline strips source column; raw CSV read is the correct pattern
- [09-01] stale_display: 'quarter_only' controls amber border suppression — only set for housing; toQuarterLabel() in JS doubles as staleness signal
- [Phase 09]: Cotality PDF scraper wired into automated pipeline (project owner approved: 'publicly available information')
- [Phase 09]: Hybrid normalization in ratios.py separates ABS index rows from Cotality pre-computed YoY rows to prevent double-normalization
- [Phase 09]: 4-candidate URL try-list for Cotality PDFs handles URL pattern inconsistency across monthly releases

### Research Flags (check before implementing)

- Phase 9 (resolved): ABS RPPI SDMX key confirmed as `1.3.100.Q` (not `3.2.100.Q`) — 74 rows fetched successfully
- Phase 9 (resolved): HOUS-03/HOUS-04 (Cotality PDF) — project owner approved, scraper implemented, 9.4% YoY Feb 2026 data live
- Phase 10: Manually verify NAB HTML regex matches the current month's page before committing Phase 10 implementation

### Blockers/Concerns

None active — Cotality ToS blocker resolved (project owner approved, HOUS-03/HOUS-04 complete).

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 09-02-PLAN.md — Cotality HVI PDF scraper, hybrid normalization fix, HOUS-03+HOUS-04 satisfied, 26/26 Playwright tests passing. Phase 9 complete.
Resume file: None
