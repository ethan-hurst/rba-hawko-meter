# Project Research Summary

**Project:** RBA Hawk-O-Meter v1.1 — Data Source Integration
**Domain:** Australian economic data scraping (PDF, HTML, JSON API)
**Researched:** 2026-02-24
**Confidence:** HIGH (all three data sources verified live against real endpoints)

## Executive Summary

The v1.1 milestone is a focused scraper-completion effort against an already operational pipeline. The v1.0 architecture is fully built: orchestrator, normalization engine, Z-score pipeline, and status.json contract are all live. Three placeholder scrapers (`corelogic_scraper.py`, `nab_scraper.py`, `asx_futures_scraper.py`) are stubbed and correctly wired into the pipeline — they just lack data-extraction logic. Completing these three scrapers will close the dashboard from "5 of 8 indicators" to "8 of 8 indicators" without requiring any new architectural work.

The recommended approach is: (1) fix ASX futures first (the scraper code already works — only endpoint verification needed), (2) implement NAB capacity utilisation via HTML extraction (not PDF — the value is directly in the article body), and (3) implement the housing price indicator via the ABS RPPI API (stale but compliant) with Cotality HVI PDF scraping deferred to v1.1.x if staleness degrades credibility. The only new dependency required is `pdfplumber>=0.11,<1.0` — and only if Cotality PDF scraping is pursued. NAB's headline figure is extractable from HTML, making PDF parsing an unnecessary complexity for the core MVP.

The primary risk is legal, not technical: Cotality's Website Terms of Use (Clause 8.4d) explicitly prohibit automated scraping of their site, and they have active enforcement history (BCI Media litigation). Using the ABS as the housing price source completely eliminates this risk. Secondary risks are reliability-related: the ASX MarkitDigital endpoint has intermittent availability history, and the NAB URL structure is inconsistent across months — both mitigated by discovery-pattern scraping and staleness monitoring rather than hardcoded URL construction.

## Key Findings

### Recommended Stack

The existing stack (`pandas>=2.0`, `requests>=2.28`, `beautifulsoup4>=4.12`, `lxml>=4.9`, `python-dateutil>=2.8`) covers the majority of v1.1 work. The only justified addition is `pdfplumber>=0.11,<1.0` — and only if the Cotality HVI PDF route is pursued (deferred to v1.1.x). All tested PDF library alternatives (camelot-py, tabula-py, pypdf) have disqualifying system-level dependencies (Ghostscript, JVM) or layout-handling deficiencies that make them unsuitable for GitHub Actions free tier.

**Core technologies:**
- `pdfplumber 0.11.9`: PDF text and table extraction — only addition needed; pure Python, no system deps; verified on both NAB and Cotality PDFs
- `requests>=2.28`: Already installed; downloads NAB/Cotality PDFs and calls ASX API
- `beautifulsoup4>=4.12`: Already installed; scrapes Cotality insights listing and NAB tag pages to find PDF/article URLs
- `re` (stdlib): Regex extraction from page HTML and PDF text — no install needed

**What NOT to use:**
- `Selenium`/`Playwright`: Both target sites render server-side HTML; browser automation is unnecessary overhead (~200MB+ CI image, 30s+ startup)
- `camelot-py`: Requires system Ghostscript — blocks GitHub Actions free tier
- `tabula-py`: Requires JVM at runtime — blocks GitHub Actions free tier
- ABS RPPI for current housing data: Series discontinued December 2021; data ends Q4 2021

### Expected Features

**Must have (table stakes):**
- ASX futures implied rate and cut/hold/hike probability — core "What Markets Expect" display; MarkitDigital API confirmed live; algorithm already implemented in `_derive_probabilities()`
- NAB capacity utilisation percentage — activates `business_confidence` gauge; value is inline in HTML body, not PDF-only; January 2026 value confirmed at 82.9%
- Housing price YoY % change — activates `housing` gauge; ABS RPPI API (stale, data to Dec 2021) satisfies gauge activation for v1.1
- Graceful degradation for all optional sources — already implemented via `fetch_and_save()` pattern; returns status dict, never raises
- Source citation and staleness metadata — already supported by `SOURCE_METADATA` and `data_date` fields in status.json schema

**Should have (competitive):**
- Cotality HVI PDF scraping for current dwelling price data — addresses ABS RPPI staleness; full workflow verified on Jan and Feb 2026 reports; requires `pdfplumber` and explicit ToS risk decision; deferred to v1.1.x
- Multi-meeting ASX futures probability curve — show 3-4 upcoming meetings; MarkitDigital returns 18 contracts covering 12+ months
- Capacity utilisation trend label ("ABOVE/BELOW long-run average of ~81%") — NAB consistently quotes this benchmark; low-effort additive context

**Defer (v2+):**
- NAB PDF historical table parsing for full backseries — HTML approach starts fresh and accumulates data over time; sufficient for current purposes
- Alternative dwelling price sources (PropTrack, Domain) — only if ABS staleness or Cotality compliance proves unacceptable after v1.1 validation
- Real-time (sub-daily) ASX futures updates — incompatible with static site design; daily cadence sufficient for macro indicator

### Architecture Approach

The v1.1 work is entirely within the existing 3-tier pipeline architecture (CRITICAL / IMPORTANT / OPTIONAL scrapers → normalize engine → status.json → Netlify CDN). All three target scrapers are already registered in the OPTIONAL tier with the correct `fetch_and_save()` contract. The normalization paths are already wired in `OPTIONAL_INDICATOR_CONFIG`. The only activation step after scrapers produce data is setting `csv_file` from `None` to the actual filename in `config.py`. No new architectural layers or patterns are required.

**Major components (all existing):**
1. `pipeline/main.py` (Orchestrator) — runs scrapers in 3 tiers; calls normalize engine in Phase 4; never fails on OPTIONAL scraper exceptions
2. `pipeline/ingest/[scraper].py` (Ingest layer) — stub scrapers awaiting data extraction logic; integration contracts already correct
3. `pipeline/normalize/engine.py` (Normalize engine) — reads CSVs, computes Z-scores, builds gauges, writes status.json; ASX futures takes a special bypass path (stored as top-level `asx_futures` key, not Z-scored)
4. `pipeline/utils/csv_handler.py` (CSV persistence) — append-with-dedup keyed on `date` column for standard indicators
5. `public/data/status.json` (Frontend contract) — consumed by Plotly.js gauges; `gauges[]` for Z-scored indicators, `asx_futures` top-level for market expectations

**Key patterns:**
- All optional scrapers must return a status dict and never raise; outer try-except in `fetch_and_save()` is mandatory
- Standard indicator CSVs use `[date, value]` schema; `date` is last day of reporting period
- ASX futures uses a bespoke 7-column schema with composite-key dedup on `[date, meeting_date]` — do not alter
- Normalization path for housing is `yoy_pct_change`; for NAB it is `direct` (capacity utilisation is already a ratio)

### Critical Pitfalls

1. **Cotality ToS violation** — Clause 8.4d explicitly prohibits automated scraping of any Cotality website content, including public news pages; BCI Media v CoreLogic litigation signals active enforcement posture. How to avoid: use ABS Total Value of Dwellings (catalog 6432.0) or ABS RPPI via existing SDMX API pattern; document the compliance decision explicitly in the plan before any implementation.

2. **CoreLogic → Cotality URL breakage** — `corelogic.com.au` now 301-redirects to `cotality.com` with a completely different URL structure; the stub `corelogic_scraper.py` targets a URL path that no longer exists on the new domain. How to avoid: verify any target URL with a live curl before writing any parsing code; prefer ABS as primary source to sidestep the domain entirely.

3. **NAB over-engineering with PDF parsing** — the capacity utilisation figure is inline in the HTML article body (`"Capacity utilisation rose to 83.1%"`), parseable with a single regex, but the stub incorrectly assumes PDF-only access. How to avoid: implement HTML extraction first; only introduce PDF fallback if the HTML pattern fails two consecutive months.

4. **NAB URL non-discovery** — NAB publishes across two domains (`business.nab.com.au` and `news.nab.com.au`) with at least three different PDF path formats; URL construction from date templates fails silently in CI. How to avoid: always discover the latest survey URL from the tag archive page (`/tag/economic-commentary/`); never construct URLs from date patterns.

5. **ASX endpoint intermittent availability** — endpoint was 404 on 2026-02-07 and HTTP 200 on 2026-02-24; treating either state as permanent leads to wrong implementation decisions or silent stale data. How to avoid: verify live before implementing; add staleness monitoring (warn if `asx_futures.csv` has no rows newer than 14 days).

## Implications for Roadmap

Based on combined research, the suggested phase structure follows dependency order and risk profile: quick win first (ASX — code complete, just verify), then ABS housing (low-risk, identical to existing ABS patterns), then NAB (highest complexity, URL discovery required). All three are independent and could parallelize, but sequential ordering reduces cognitive load and allows each verified phase to inform the next.

### Phase 1: ASX Futures Endpoint Fix (HAWK-04)

**Rationale:** The scraper code is complete and correct. This is a verification-and-CI task, not an implementation task. Quickest possible win, zero new dependencies, unblocks daily refresh accuracy immediately. Should take under half a day.
**Delivers:** `data/asx_futures.csv` populated with fresh rows; `status.json` shows current implied rate and cut/hold/hike probabilities; dashboard "What Markets Expect" section live with fresh data.
**Addresses:** ASX rate futures (P1 must-have); implied rate display, cut/hold/hike probability features
**Avoids:** Pitfall 5 (treating endpoint as permanently down); adds staleness monitoring to catch future intermittency
**Research flag:** None — standard pattern, endpoint already verified live 2026-02-24

### Phase 2: Housing Prices via ABS RPPI (PIPE-03)

**Rationale:** Low implementation risk (ABS SDMX API is the same pattern as all 5 existing ABS scrapers in production). Source decision (ABS vs Cotality) must be made explicitly before implementation to avoid ToS exposure. ABS approach is compliant, well-understood, and activates the `housing` gauge even if data is from Dec 2021. Staleness is a display problem (add "(data to Dec 2021)" label in source metadata), not an architecture problem.
**Delivers:** `data/corelogic_housing.csv` populated; `gauges['housing']` in status.json; indicator count moves from 5 to 6 of 8.
**Uses:** Existing ABS SDMX API pattern from `abs_data.py`; ABS dataflow `RPPI`, key `3.2.100.Q`; `yoy_pct_change` normalization already configured in `OPTIONAL_INDICATOR_CONFIG`
**Implements:** `corelogic_scraper.fetch_and_save()` body; sets `OPTIONAL_INDICATOR_CONFIG["housing"]["csv_file"]` to `"corelogic_housing.csv"`
**Avoids:** Pitfall 1 (Cotality ToS violation); Pitfall 2 (broken CoreLogic URL redirect)
**Research flag:** Verify ABS RPPI SDMX key `3.2.100.Q` returns expected data with a live API call before implementation; the SDMX API occasionally reorganizes dataflow IDs.

### Phase 3: NAB Capacity Utilisation (PIPE-04)

**Rationale:** Highest complexity of the three. Requires URL discovery logic (not URL construction), HTML regex extraction, and handling of dual-domain NAB publishing pattern. Must manually verify the HTML extraction regex matches the current month's page before implementation. Budget 2 days for implementation and testing against 3+ historical months.
**Delivers:** `data/nab_capacity.csv` populated; `gauges['business_confidence']` in status.json; indicator count moves to 7 of 8 (or 8 of 8 if housing is also live).
**Uses:** `requests` + `beautifulsoup4` (existing); tag archive discovery at `https://business.nab.com.au/tag/economic-commentary/`; regex `r'[Cc]apacity utilisation (?:rose|fell|remained|was) (?:to |at )?(\d+\.?\d*)%'`
**Implements:** `nab_scraper.fetch_and_save()` body; sets `OPTIONAL_INDICATOR_CONFIG["business_confidence"]["csv_file"]` to `"nab_capacity.csv"`
**Avoids:** Pitfall 3 (unnecessary PDF parsing); Pitfall 4 (URL construction without discovery)
**Research flag:** Manually verify the HTML regex matches the CURRENT month's page before committing implementation. If HTML fails, introduce `pdfplumber>=0.11,<1.0` and use the PDF extraction strategy documented in STACK.md (step-by-step workflow verified on Nov 2025 PDF).

### Phase 4: Cotality HVI PDF Scraping (v1.1.x — contingent)

**Rationale:** Only if ABS RPPI staleness (data ends Dec 2021) degrades user trust in the hawk score after v1.1 ships. The full PDF scraping workflow (listings page → article page → PDF URL → pdfplumber extraction) has been verified on two consecutive monthly reports (Jan and Feb 2026). This is deferred because the implementation cost is high, the ABS data activates the gauge, and the ToS decision requires explicit project-owner sign-off.
**Delivers:** `data/corelogic_housing.csv` updated with current monthly Cotality HVI data; housing gauge reflects current property market conditions with data less than 30 days old.
**Uses:** `pdfplumber>=0.11,<1.0` (new dependency, add to requirements.txt); `cotality.com/au/insights` listings page → article page scrape → `discover.cotality.com/hubfs/Article-Reports/COTALITY%20HVI%20*` PDF
**Avoids:** Pitfall 2 (use verified Cotality URL structure, not CoreLogic URLs)
**Research flag:** Before implementing, re-read Cotality ToS and document the legal risk decision. The ToS clearly prohibits scraping; only proceed with explicit project-owner sign-off. Do not begin Phase 4 implementation without that documented decision.

### Phase Ordering Rationale

- ASX first because the code is already complete — it is a CI verification task that delivers immediate visible value with no implementation risk
- Housing before NAB because ABS SDMX is identical to existing patterns (near-zero implementation risk) while NAB requires new URL discovery logic (medium risk)
- Both housing and NAB are fully independent — they can be parallelized if two developers are available
- Cotality PDF deferred: (1) ABS satisfies gauge activation, (2) ToS risk requires explicit decision, (3) implementation complexity is highest of all four phases
- The three core phases (ASX fix, ABS housing, NAB HTML) have no cross-dependencies and each delivers a measurable dashboard increment

### Research Flags

Phases needing verification before implementation begins:
- **Phase 2 (ABS RPPI):** Confirm SDMX API dataflow `RPPI` key `3.2.100.Q` with a live curl; ABS occasionally reorganizes SDMX dataflows. Fallback: ABS Total Value of Dwellings (catalog 6432.0) is documented as alternative.
- **Phase 3 (NAB HTML):** Manually verify capacity utilisation regex matches the CURRENT month's page; last confirmed month was August 2025.
- **Phase 4 (Cotality PDF):** Requires documented ToS risk decision from project owner before any implementation begins.

Phases with standard patterns (skip additional research):
- **Phase 1 (ASX):** Endpoint verified live 2026-02-24; code complete; standard graceful degradation pattern already in production.
- **Phase 2 (ABS):** If RPPI dataflow key confirmed, implementation is identical to the 5 existing ABS scrapers.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified live; pdfplumber tested on actual NAB and Cotality PDFs; ASX endpoint tested live 2026-02-24; no version conflicts with existing requirements |
| Features | HIGH | All three data sources verified against live endpoints or pages; feature set maps directly to existing OPTIONAL_INDICATOR_CONFIG stubs already in production |
| Architecture | HIGH | All findings verified directly against actual source files in the codebase; no inferences from documentation alone |
| Pitfalls | HIGH | Cotality ToS fetched directly from official legal page; ASX endpoint status verified live; NAB HTML structure verified via direct page fetch; litigation source corroborated by multiple industry outlets |

**Overall confidence:** HIGH

### Gaps to Address

- **ABS RPPI SDMX key:** Key `3.2.100.Q` (MEASURE=3, PROPERTY_TYPE=2, REGION=100, FREQ=Q) was verified by researcher but should be confirmed with a live API call before Phase 2 implementation. If the key returns no data or the dataflow has been restructured, the documented fallback is ABS Total Value of Dwellings (catalog 6432.0).
- **NAB current-month regex:** The capacity utilisation regex was confirmed for April 2025 and August 2025 pages. Verify against the current month (Feb or March 2026) before implementing Phase 3 — NAB may have updated their survey page template.
- **Cotality ToS decision:** The legal risk of Phase 4 requires an explicit decision from the project owner. The research documents the prohibition clearly in PITFALLS.md. The implementation plan must not proceed with Phase 4 without that decision being documented.
- **ASX staleness monitoring:** The existing scraper code has no staleness warning. Add a log warning in Phase 1 if `asx_futures.csv` has no rows newer than 14 days.

## Sources

### Primary (HIGH confidence)

- ASX MarkitDigital API — live test 2026-02-24: `https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures` — 18 contracts, correct JSON schema confirmed
- pdfplumber PyPI — version 0.11.9 confirmed, released 2026-01-05: `https://pypi.org/project/pdfplumber/`
- NAB Monthly Business Survey pages — live test 2026-02-24 (April 2025 and August 2025): capacity utilisation confirmed inline in HTML article body
- NAB November 2025 PDF — live test 2026-02-24: HTTP 200, capacity utilisation regex extraction verified; `2025m11%20NAB%20Monthly%20Business%20Survey.pdf`
- Cotality HVI PDFs — live test 2026-02-24: Jan 2026 and Feb 2026 PDFs accessible; Australia YoY `% change extraction verified with pdfplumber
- Cotality Website Terms of Use Clause 8.4d — fetched directly: `https://www.cotality.com/legals/website-terms`
- ABS RPPI discontinuation — confirmed Dec 2021: `https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/residential-property-price-indexes-eight-capital-cities`
- Codebase verification — all architecture findings verified against actual source files: `pipeline/main.py`, `pipeline/config.py`, `pipeline/ingest/`, `pipeline/normalize/engine.py`, `pipeline/utils/csv_handler.py`, `.github/workflows/`

### Secondary (MEDIUM confidence)

- CoreLogic → Cotality rebrand (March 2025): `https://www.mi-3.com.au/25-03-2025/corelogic-rebrands-cotality-signalling-global-expansion-and-innovation` — multiple industry sources agree
- BCI Media v CoreLogic litigation: `https://www.lawyerly.com.au/bci-media-takes-corelogic-to-court-over-data-scraping/` — signals active enforcement posture
- ABS Total Value of Dwellings as fallback: `https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/total-value-dwellings` — SDMX API dataflow ID needs live verification before use
- NAB January 2026 capacity utilisation (82.9%): MarketScreener source — value confirmed; primary NAB page not directly accessible during research

### Tertiary (LOW confidence)

- NAB URL patterns: Inferred from observed months (April 2025, August 2025, November 2025) — December 2025 and January 2026 URL variants not directly verified; discovery approach mitigates this gap entirely

---
*Research completed: 2026-02-24*
*Ready for roadmap: yes*
