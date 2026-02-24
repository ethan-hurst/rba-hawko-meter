# Feature Research

**Domain:** Economic dashboard — Australian dwelling prices, business capacity utilisation, ASX rate futures
**Researched:** 2026-02-24
**Confidence:** HIGH (all three data sources verified against live APIs/endpoints)

---

## Context: v1.1 Milestone Scope

This research is scoped to the three remaining placeholder data sources in the v1.1 milestone:

| Placeholder | Target Source | Status as of Research |
|-------------|---------------|----------------------|
| CoreLogic dwelling prices | ABS RPPI (API) / Cotality HVI (PDF scrape) | ABS RPPI confirmed alive but **data last updated Dec 2021** — stale |
| NAB capacity utilisation | NAB Monthly Business Survey page (HTML) / PDF | HTML inline value confirmed for most months; PDF publicly accessible |
| ASX rate futures | MarkitDigital API | **Confirmed live and returning data** (HTTP 200, 18 contracts) |

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that are required for each data source to contribute meaningfully to the dashboard. Missing these makes the indicator feel broken or incomplete.

#### CoreLogic / Dwelling Prices

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **National dwelling price YoY % change** | The single metric that feeds the Z-score gauge. Without it the "housing" bullet gauge remains grey. | MEDIUM | ABS RPPI API confirmed working (dataflow: `RPPI`, key `3.2.100.Q` = YoY % change, established houses, 8-capital weighted avg). **Caveat: last ABS RPPI release was December 2021** — 3+ years stale. Must use Cotality HVI PDF or media-release scrape for current data. |
| **Quarterly update cadence** | Dwelling prices are reported quarterly; pipeline must handle quarterly-frequency normalization | LOW | Already supported — `INDICATOR_CONFIG` has `yoy_periods: 4` for quarterly. `_parse_abs_date()` already handles `YYYY-QN` format. |
| **Graceful degradation if source unavailable** | Pattern already established for all optional sources | LOW | `fetch_and_save()` never raises; returns `{'status': 'failed', 'error': ...}`. Already implemented as stub. |
| **Source citation in dashboard** | Trust and transparency ("Data, not opinion") | LOW | Already handled by `SOURCE_METADATA` in config.py; just needs new entry. |

#### NAB Capacity Utilisation

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Single capacity utilisation percentage** | The metric that feeds the Z-score. NAB reports a clean single number (e.g., "82.9%") monthly. | MEDIUM | Value is published inline in HTML body of the survey page (`business.nab.com.au/nab-monthly-business-survey-[month]-[year]/`). No PDF parsing required for the headline number. Confirmed for April 2025 and August 2025. |
| **Latest month discovery** | Scraper must find the most recent survey page without hardcoding URLs | MEDIUM | The survey pages follow a consistent slug pattern: `/nab-monthly-business-survey-[month-name]-[year]`. The Jan 2026 survey was on `nab.com.au`, not `business.nab.com.au`, suggesting the most-recent URL may vary. Must probe recent months by trying slugs backwards in time. |
| **Monthly update cadence** | NAB publishes monthly, so coverage will be denser than quarterly | LOW | Already handled — `normalize: "direct"` in `OPTIONAL_INDICATOR_CONFIG` (uses raw value, no YoY). Historical long-run average is ~81% (confirmed from survey text). |
| **Graceful degradation** | Same pattern as other optional sources | LOW | Already stubbed. |

#### ASX Rate Futures

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Implied rate for next RBA meeting** | Core display in "What Markets Expect" dashboard section | LOW | MarkitDigital API confirmed live. Returns `priceContract` per contract symbol (e.g., `IBH2026`). Implied rate = `100 - priceContract`. Current data: IBH2026 (March 2026 expiry) = 96.135 → implied 3.865%. |
| **Cut/Hold/Hike probability** | Dashboard already has placeholder for this display | MEDIUM | Probability derivation algorithm already implemented in `_derive_probabilities()`. Maps implied vs current rate difference to cut/hold/hike with 5bp deadband and 25bp step scale. |
| **Daily update via existing CI** | The daily-asx-futures GitHub Action already runs but produces no data | LOW | Action exists. Scraper needs to use MarkitDigital URL (already in `config.py` as `ASX_FUTURES_URLS["ib_futures"]`). The old ASX DAM endpoints (which 404'd) should be removed; MarkitDigital is the correct endpoint. |
| **Normalization as benchmark (not hawk score)** | ASX futures is market-derived, excluded from hawk score per design decision | LOW | `exclude_benchmark=True` flag already in gauge.py. No change needed. |

---

### Differentiators (Competitive Advantage)

Features that would make the v1.1 integration stand out beyond the minimum viable scraper.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Multi-meeting ASX futures curve** | Show probability for 3-4 upcoming RBA meetings, not just the next one | MEDIUM | MarkitDigital returns 18 contracts (12+ months of expiry dates). Dashboard could show "markets expect cuts at Feb, Apr, Jun meetings". Requires frontend change to display curve. |
| **Capacity utilisation trend label** | Show "ABOVE AVERAGE" / "BELOW AVERAGE" relative to NAB's stated long-run average of ~81% | LOW | NAB articles consistently quote "long-run average" in text. A simple threshold rule (>81% = above, <81% = below) adds context without requiring historical series. |
| **ABS RPPI as authoritative fallback** | If Cotality scrape fails, show ABS data with age warning ("data as of Dec 2021") | LOW | Preserves Z-score calculation using stale but official data rather than showing nothing. Data integrity maintained by sourcing from an official government API. |
| **Indicator coverage counter update** | Dashboard currently says "Based on 5 of 8 indicators" — v1.1 should say "Based on 8 of 8" | LOW | Already in place — counter is driven by indicator availability in status.json. Completing the scrapers automatically fixes this display. |

---

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **CoreLogic/Cotality HVI via authenticated API** | More current, more granular data | Requires account, payment, or TOS violation; Cotality (formerly CoreLogic) explicitly states data is proprietary; scraping Cotality.com would violate terms | Use ABS RPPI (stale but official and free) for the Z-score; note staleness in source metadata |
| **NAB capacity utilisation PDF table parsing** | Full historical series is in the PDF | PDF layout inconsistency across months makes this brittle (multiple filename patterns observed); headline value is already in the HTML | Scrape the HTML body for the single number; if HTML fails, fall back to PDF parsing as phase 2 |
| **Real-time ASX futures updates (sub-daily)** | More accurate probability readings | ASX futures data changes continuously during trading hours; daily snapshots are sufficient for a macro indicator; real-time would require streaming infrastructure incompatible with static site design | Keep existing daily GitHub Action cadence (already implemented) |
| **Selenium/Playwright for ASX Rate Tracker page** | Would give access to the ASX React SPA | Adds Chromium dependency to CI (~200MB), slower, fragile to UI changes, requires headless browser setup | MarkitDigital API is confirmed live and returns identical underlying data without browser automation |
| **Cotality daily HVI** | Cotality publishes daily index values on their page | Daily scraping of a commercial data provider's website is likely to trigger bot detection, rate limiting, and constitutes questionable TOS compliance | Quarterly update from the monthly media release aligns with the ABS RPPI cadence and avoids compliance risk |
| **NAB Quarterly Business Survey for capacity utilisation** | Quarterly survey covers ~680 firms (larger sample) | The quarterly survey PDF has an inconsistent URL pattern (e.g., `NAB%20Quarterly%20Business%20Survey%20(Q3%202025).pdf`) and the monthly survey already covers capacity utilisation with the same metric | Use the monthly survey — more frequent updates, simpler HTML scraping, same metric |

---

## Feature Dependencies

```
[ABS RPPI API OR Cotality HVI PDF scrape]
    └──produces──> [housing_prices.csv]
                       └──requires──> [normalize/engine.py: yoy_pct_change, quarterly]
                                          └──requires──> [INDICATOR_CONFIG "housing" stub activated]
                                                             └──produces──> [status.json "housing" gauge]

[NAB business survey HTML scrape]
    └──produces──> [nab_capacity.csv]
                       └──requires──> [normalize/engine.py: direct normalization]
                                          └──requires──> [OPTIONAL_INDICATOR_CONFIG "business_confidence" activated]
                                                             └──produces──> [status.json "business_confidence" gauge]

[MarkitDigital API]
    └──produces──> [asx_futures.csv]
                       └──requires──> [normalize/engine.py: direct normalization (already implemented)]
                                          └──requires──> [OPTIONAL_INDICATOR_CONFIG "asx_futures" activated]
                                                             └──produces──> [status.json "asx_futures" section]

[status.json all 8 indicators populated]
    └──enables──> [Dashboard "Based on 8 of 8 indicators" display]
    └──enables──> [Hawk Score includes housing + business_confidence]
    └──note──> [asx_futures excluded from hawk score — benchmark only]
```

### Dependency Notes

- **Housing requires source decision first:** ABS RPPI is stale (Dec 2021) — if deemed too stale for Z-score, Cotality HVI PDF scraping must be implemented. This is the highest-complexity decision in v1.1.
- **NAB scraper requires URL discovery:** The most-recent survey page URL must be derived dynamically (probe recent months), not hardcoded. This is the main implementation complexity.
- **ASX futures requires config update:** MarkitDigital URL is already in `config.py`. The scraper just needs to use it (remove dead ASX DAM endpoints, map contract symbols to RBA meeting dates).
- **All three are independent:** CoreLogic, NAB, and ASX scrapers have no cross-dependencies and can be implemented in parallel.

---

## MVP Definition

### Launch With (v1.1)

Minimum needed to close the "8 of 8" gap and make all gauges active.

- [ ] **ASX futures via MarkitDigital** — Lowest risk; API is confirmed live, algorithm already written, config already has the URL. Essentially wire up existing code to working endpoint.
- [ ] **NAB capacity utilisation via HTML scrape** — Medium risk; value is inline in HTML body for recent months. Must handle URL discovery (probe backwards by month name) and fallback if month page is on `nab.com.au` vs `business.nab.com.au`.
- [ ] **Housing prices via ABS RPPI API** — Low implementation risk (API is the same pattern as all other ABS sources). However, data is stale (last release: Dec 2021). Include staleness warning in source metadata. Z-score will use 2014–2021 history only.

### Add After Validation (v1.1.x)

Features to add once all three scrapers are producing data.

- [ ] **Cotality HVI PDF scraping** — Only if ABS RPPI staleness degrades hawk score credibility after user feedback. Monthly media releases at `discover.cotality.com/hubfs/Article-Reports/COTALITY%20HVI%20[Mon]-[Year]%20FINAL.pdf` follow a predictable URL pattern. Requires `pdfplumber` to extract the percentage change from a PDF.
- [ ] **Multi-meeting futures curve** — Show 3 upcoming meetings' implied rates/probabilities in dashboard once the single-meeting display is validated.

### Future Consideration (v2+)

- [ ] **NAB PDF table parsing for historical series** — Only if monthly HTML scraping proves unreliable for historical backfill. Current approach starts fresh and accumulates data over time, which is sufficient.
- [ ] **Alternative dwelling price source** — PropTrack, Domain, or another commercial provider if data quality or coverage becomes an issue.

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| ASX futures (MarkitDigital) | HIGH — displays market rate cut probability | LOW — API confirmed, code exists | P1 |
| NAB capacity utilisation (HTML) | HIGH — activates business_confidence gauge | MEDIUM — URL discovery needed | P1 |
| ABS RPPI housing prices | MEDIUM — gauge activates but data is stale | LOW — identical pattern to existing ABS fetchers | P1 |
| Cotality HVI PDF scraping | HIGH — current dwelling price data | HIGH — PDF parsing, URL discovery, brittle | P2 |
| Multi-meeting futures curve | MEDIUM — richer market context | MEDIUM — frontend + data schema change | P2 |
| Capacity utilisation trend label | LOW — nice context | LOW | P3 |

**Priority key:**
- P1: Must have for v1.1 launch (closes "8 of 8" gap)
- P2: Should have, add after v1.1 validated
- P3: Nice to have, v2+

---

## Data Source Specifics

### CoreLogic / ABS RPPI

**Confirmed API:** `https://data.api.abs.gov.au/data/ABS,RPPI/{key}?detail=dataonly&startPeriod=2014`
- Key for YoY % change, established houses, 8-capital weighted average: `3.2.100.Q`
- MEASURE: `3` (Percentage Change from Corresponding Quarter of Previous Year)
- PROPERTY_TYPE: `2` (Established houses)
- REGION: `100` (Weighted average of eight capital cities)
- FREQ: `Q` (Quarterly)
- **Last data point: 2021-Q4** (series ceased Dec 2021)
- `_parse_abs_date()` already handles `YYYY-QN` format

**Alternative — Cotality HVI media releases:**
- URL pattern: `https://discover.cotality.com/hubfs/Article-Reports/COTALITY%20HVI%20[Mon]%20[Year]%20FINAL.pdf`
- Jan 2026 confirmed: `COTALITY%20HVI%20Jan%202026%20FINAL.pdf`
- Contains monthly national dwelling value % change
- Requires `pdfplumber` for extraction (HIGH complexity, deferred to P2)

### NAB Capacity Utilisation

**Confirmed HTML source:** `https://business.nab.com.au/nab-monthly-business-survey-[month-name]-[year]/`
- Capacity utilisation percentage appears inline in `<p>` tags (confirmed for April 2025 and August 2025)
- Pattern: `Capacity utilisation [rose/fell] to XX.X%`
- PDF is also publicly accessible at: `https://business.nab.com.au/content/dam/nab-business/document/NAB-Monthly-Business-Survey-[Month]-[Year].pdf`
- **January 2026 data (most recent):** 82.9% — confirmed from MarketScreener source
- Long-run average: ~81% (stated in survey text consistently)
- URL discovery strategy: try current month → probe backwards through last 6 months

### ASX Rate Futures

**Confirmed working API:** `https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures?days=365&height=1&width=1`
- Returns 18 IB futures contracts (12+ months of expiry)
- Key fields: `symbol` (e.g., `IBH2026`), `dateExpiry`, `priceContract`
- Implied rate = `100 - priceContract`
- Sample data (2026-02-24): IBG2026 expiry 2026-02-25 → 3.820%, IBH2026 expiry 2026-03-29 → 3.865%
- Current RBA rate: ~4.10% (implied from spread vs futures = strong cut expectation)
- Contract symbol format: `IB[A=Jan, B=Feb, ..., M=Jun, N=Jul, Q=Aug, U=Sep, V=Oct, X=Nov, Z=Dec][YYYY]`

---

## Competitor Feature Analysis

| Feature | ASX RBA Rate Tracker | RBA Isaac Gross | RBA Hawk-O-Meter |
|---------|---------------------|-----------------|-----------------|
| Futures probability display | Yes (interactive chart) | Yes (heatmap for all meetings) | Single next-meeting probability (planned) |
| Dwelling price indicator | No | No | Yes (planned via ABS RPPI / Cotality) |
| Business capacity utilisation | No | No | Yes (planned via NAB survey) |
| Combined hawk/dove score | No | No | Yes (Hawk-O-Meter) |
| Mortgage calculator | No | No | Yes |
| Plain English labels | No (jargon) | No | Yes |
| Free, no-account access | Yes | Yes | Yes |

---

## Sources

- ABS RPPI API confirmed working: `https://data.api.abs.gov.au/data/ABS,RPPI/all` (live test 2026-02-24, HTTP 200)
- ABS RPPI series ceased: https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/residential-property-price-indexes-eight-capital-cities (last release Dec 2021)
- MarkitDigital ASX futures API confirmed working: `https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures` (live test 2026-02-24, HTTP 200, 18 contracts)
- NAB Monthly Business Survey pages: https://business.nab.com.au/nab-monthly-business-survey-april-2025/ and https://business.nab.com.au/nab-monthly-business-survey-august-2025/ (capacity utilisation confirmed inline in HTML)
- NAB January 2026 survey: https://au.marketscreener.com/news/national-australia-bank-nab-business-survey-january-2026-a-confidence-edges-up-but-conditions-fa-ce7e5adcd18df122 (82.9% confirmed)
- NAB November 2025 PDF: https://business.nab.com.au/content/dam/nab-business/document/2025m11%20NAB%20Monthly%20Business%20Survey.pdf (HTTP 200)
- Cotality indices page: https://www.cotality.com/our-data/corelogic-indices (public daily HVI confirmed, backseries Excel available)
- ASX rate tracker calculation methodology: https://www.asx.com.au/data/trt/rate_tracker_calc.htm
- RBA Isaac Gross site: https://rba.isaacgross.net/
- pdfplumber for PDF table extraction: https://github.com/jsvine/pdfplumber

---
*Feature research for: Australian economic dashboard — v1.1 data source integration*
*Researched: 2026-02-24*
