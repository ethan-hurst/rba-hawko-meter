# Pitfalls Research

**Domain:** Australian Economic Data Scraping — Adding real scrapers for CoreLogic (housing), NAB (capacity utilisation PDF), and ASX IB Futures to an existing GitHub Actions pipeline
**Researched:** 2026-02-24
**Confidence:** HIGH (CoreLogic legal risk verified via official ToS; ASX endpoint status verified live; NAB page structure verified via direct fetch)

---

## Critical Pitfalls

### Pitfall 1: Scraping Cotality (CoreLogic) Violates Their Website Terms of Service

**What goes wrong:**
The scraper hits `www.cotality.com` (formerly `www.corelogic.com.au`, which now 301-redirects) to extract housing price figures from news/research releases. The scraper may work technically while constituting a breach of Cotality's website terms.

**Why it happens:**
Cotality's Website Terms of Use (Clause 8.4d) explicitly prohibit:

> "use any manual process (such as keying-in), robot, spider, screen scraper, injection techniques, data aggregation tool or use any other device or automated process (Scraping Process) to data mine, scrape, crawl, email harvest, aggregate, copy or extract any Cotality Services, processes, information, content, or data accessible through this Website"

The prohibition covers "any content or data accessible through this Website" without carve-outs for public news pages. Cotality is currently involved in active Australian litigation against another company for data scraping (BCI Media v CoreLogic), signalling active enforcement posture.

**How to avoid:**
Use the ABS as the housing price data source instead of Cotality. Specifically:
- **ABS Total Value of Dwellings** (catalog 6432.0) is published quarterly and includes mean and median dwelling prices nationally. This dataset is compiled from CoreLogic sales data but is served by the ABS under their open data terms.
- **ABS House Price Indexes** (catalog 6416.0) — check whether ABS SDMX API dataflow `HPI` is available.
- Either source can be fetched via `https://data.api.abs.gov.au/data/` with the existing pattern already used in `abs_data.py`.

If the roadmap explicitly targets CoreLogic/Cotality public media releases despite the ToS risk, the plan must include a legal risk acknowledgement and a fallback to ABS data.

**Warning signs:**
- The domain `www.corelogic.com.au` now 301-redirects to `www.cotality.com` — any hardcoded `corelogic.com.au` URLs will silently follow the redirect, potentially hitting new page structures.
- HTTP 403 response or Cloudflare challenge page in CI logs.
- Scraper returns data locally but fails in GitHub Actions (different IP fingerprint triggers bot detection).

**Phase to address:**
CoreLogic scraper phase (PIPE-03). The plan must make a clear decision: ABS housing data as the compliant alternative, or explicit acknowledgement of Cotality ToS risk with justification (e.g., scraping is for non-commercial personal research, relying on fair dealing). Do NOT silently proceed with Cotality scraping.

---

### Pitfall 2: CoreLogic Has Rebranded to Cotality — All Existing URLs Are Wrong

**What goes wrong:**
The existing `corelogic_scraper.py` targets `https://www.corelogic.com.au/news-research/reports`. That URL now 301-redirects to `https://www.cotality.com/news-research/reports`, which returns a 404. The new Cotality website has a completely different URL structure.

**Why it happens:**
CoreLogic globally rebranded as Cotality in March 2025. The Australian domain changed from `corelogic.com.au` to `cotality.com`. Old paths that existed under CoreLogic do not exist on the Cotality site.

**Consequences:**
The scraper would follow the 301 redirect but then get a 404 from Cotality's new URL structure. Since `fetch_and_save()` catches all exceptions and returns `{'status': 'failed'}`, this failure is silent — the pipeline continues, the dashboard stays at "5 of 8 indicators."

**How to avoid:**
Before implementing any CoreLogic/Cotality scraper, manually verify the target URL is live and returns the expected content. The current correct domain for research releases is `www.cotality.com` but the `/news-research/reports` path does not exist. The reports section appears to have moved; use `https://www.cotality.com/au/research` or the media release index as the starting point (both require manual verification before coding).

**Warning signs:**
- Response `status_code == 404` on the `www.cotality.com` target URL.
- Page content < 500 characters (the existing guard catches this but only after following the redirect).
- Scraper logs show HTTP 200 but empty DataFrame — this means the redirect succeeded but the page structure is completely different.

**Phase to address:**
PIPE-03 implementation. Verify the target URL live before writing any parsing code. Add a specific URL validation step to the plan.

---

### Pitfall 3: ASX MarkitDigital Endpoint Returns 404 Intermittently — Not Reliably Down, Not Reliably Up

**What goes wrong:**
Phase 7 verification documented that the ASX endpoints returned 404 as of February 2026. However, live verification during this research (2026-02-24) shows the MarkitDigital endpoint `https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures?days=365&height=1&width=1` is currently responding HTTP 200 with valid JSON containing 17 IB futures contract items.

**Why it happens:**
The ASX/MarkitDigital backend appears to have intermittent availability — it was down when Phase 7 was implemented (Feb 7, 2026) but is up as of Feb 24, 2026. This makes the endpoint unreliable: it may work during development but fail in production CI, or vice versa.

**Consequences:**
If the scraper is tested locally when the endpoint is up, it appears to work. Then in GitHub Actions, it hits a 404. With the existing graceful degradation pattern (`exit code 2`), the dashboard continues showing stale ASX data rather than raising an alert.

**How to avoid:**
- The existing `asx_futures_scraper.py` already handles this correctly with `response.raise_for_status()` + graceful degradation.
- The actual issue for HAWK-04 is: the scraper code is complete and correct — the only work is to verify the endpoint is back up, check the JSON schema matches `data.items[]` expectations, and confirm the pipeline runs end-to-end in CI.
- Do NOT assume the endpoint status observed at implementation time will persist. Add a staleness check: if `asx_futures.csv` has no data newer than 14 days, log a prominent warning in the GitHub Actions step output.

**Warning signs:**
- `HTTP 404` or `HTTP 403` in the GitHub Actions step log for the ASX scraper.
- `asx_futures.csv` file exists but last row `date` is more than 14 days old.
- Dashboard shows "What Markets Expect" section hidden despite recent runs (frontend hides section when `asx_futures` key absent from `status.json`).

**Phase to address:**
HAWK-04. The implementation is done. The phase should focus on: (1) confirming the endpoint is live at implementation time via a manual curl, (2) running the existing scraper end-to-end in CI, (3) setting up staleness monitoring.

---

### Pitfall 4: NAB Survey Capacity Utilisation Is in the HTML — PDF Parsing Is Unnecessary Complexity

**What goes wrong:**
The placeholder `nab_scraper.py` assumes the capacity utilisation figure is only in the PDF and notes "NAB data is in PDF format - scraper needs PDF parsing capability." This assumption is incorrect and would lead to adding unnecessary PDF parsing dependencies (pdfplumber, pypdf) when a simpler solution exists.

**Why it happens:**
The placeholder scraper looks for PDF links on the page and concludes data is PDF-only. But the NAB monthly survey pages (e.g., `https://business.nab.com.au/nab-monthly-business-survey-august-2025`) include the capacity utilisation figure directly in the HTML article body: "Capacity utilisation rose to 83.1%". BeautifulSoup can extract this without any PDF library.

**Consequences:**
Adds pdfplumber/pypdf to `requirements.txt` unnecessarily, increasing dependency surface and potential CI failures (pdfplumber has C dependencies via pdfminer.six). PDF layout parsing is brittle — NAB may change which page of the PDF the figure appears on.

**How to avoid:**
Parse the HTML page body using BeautifulSoup and a regex pattern: `r'[Cc]apacity utilisation (?:rose|fell|remained|was) (?:to |at )?(\d+\.?\d*)%'`. This pattern matches the phrasing NAB has used consistently across 2024-2025 survey releases. Only fall back to PDF parsing if the HTML pattern fails two consecutive months.

**Warning signs:**
- The regex returns no match on the HTML page — this may mean NAB changed their phrasing (e.g., "capacity utilisation: 83.1%").
- `len(soup.get_text(strip=True)) < 500` — page might be JavaScript-rendered (unlikely; NAB pages render server-side).
- The PDF download link exists but the HTML text does not contain the figure (unlikely but possible if NAB moves to summary-only HTML).

**Phase to address:**
PIPE-04 implementation. Default to HTML extraction. Only introduce PDF parsing if HTML approach fails during manual verification before implementation.

---

### Pitfall 5: NAB Survey URL Slug Cannot Be Reliably Constructed Without Discovery

**What goes wrong:**
The implementation constructs the NAB URL as `https://business.nab.com.au/nab-monthly-business-survey-{month_name}-{year}` expecting a consistent slug pattern. In practice, some releases are on `business.nab.com.au`, others migrate to `news.nab.com.au`, and PDF links are hosted across multiple different path structures.

**Why it happens:**
NAB publishes across two domains:
- `business.nab.com.au` — primary research hub (most monthly surveys 2023-2025)
- `news.nab.com.au` — press release/news hub (some monthly surveys appear here too)

PDF links are hosted on:
- `business.nab.com.au/wp-content/uploads/{year}/{month}/NAB-Monthly-Business-Survey-{Month}-{Year}.pdf`
- `news.nab.com.au/content/dam/nab-news/documents/nab-monthly-business-survey-{mon}-{year}.pdf`
- `business.nab.com.au/content/dam/nab-business/document/NAB-Monthly-Business-Survey-{Month}-{Year}-.pdf` (note trailing dash before .pdf)

The trailing dash in the PDF filename (confirmed from April 2025: `NAB-Monthly-Business-Survey-April-2025-.pdf`) is inconsistent and cannot be assumed across months.

**Consequences:**
A hardcoded URL construction will fail silently in CI when NAB publishes a month using a different slug or domain. The `fetch_and_save()` graceful degradation means the failure goes unnoticed and the dashboard shows stale capacity utilisation data.

**How to avoid:**
Use a discovery approach rather than URL construction:
1. Fetch the NAB business survey tag page `https://business.nab.com.au/tag/economic-commentary/` or `https://business.nab.com.au/tag/business-survey/`.
2. Find the most recent survey link by looking for `<a>` elements matching the pattern `/nab-monthly-business-survey-` sorted by recency.
3. Fetch that URL and extract the capacity utilisation figure from the HTML body.
4. If not found on `business.nab.com.au`, try `news.nab.com.au`.

This avoids the slug construction problem entirely.

**Warning signs:**
- `requests.get(constructed_url)` returns 404.
- The scraped date matches a prior month (stale data silently accepted).
- Two or more consecutive weeks with no update to `nab_capacity.csv`.

**Phase to address:**
PIPE-04 implementation. Use discovery pattern from the start, not URL construction.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode the NAB URL slug pattern | Simpler code to write | Fails silently when NAB changes slug; stale data undetected for weeks | Never — discovery approach adds ~10 lines of code |
| Target `corelogic.com.au` URLs | Tests may pass locally (301 redirects) | Domain now 301s to Cotality, which has different URL structure; ToS breach risk | Never — update to `cotality.com` or switch to ABS |
| Add pdfplumber for NAB PDF parsing | Seems to match the problem | Adds C dependencies, CI failures, brittle page-number assumptions | Only if HTML approach fails after 2+ months |
| Assume ASX endpoint is reliably up or down | Simpler retry logic | Intermittent availability means build may pass locally and fail in CI, or vice versa | Never — add staleness monitoring regardless |
| Skip staleness monitoring for optional sources | Faster to ship | Silent data rot: dashboard claims "8 of 8 indicators" but shows 3-month-old NAB data | Never — staleness metadata already expected by the status.json schema |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Cotality (CoreLogic) | Scraping `corelogic.com.au` URLs that now 301-redirect to a broken Cotality path | Verify `cotality.com` URL structure before writing any parser; prefer ABS housing data instead |
| Cotality (CoreLogic) | Treating public news releases as freely scrapeable | Read ToS Clause 8.4d — automated scraping of website content is prohibited regardless of whether content is paywalled |
| NAB Business Survey | Constructing URL as `/nab-monthly-business-survey-{month}-{year}` | Discover the latest URL from the tag archive page; NAB uses two domains and inconsistent PDF paths |
| NAB Business Survey | Adding PDF parsing libraries before testing HTML extraction | Check HTML first — capacity utilisation figure is in the article body text, parseable with regex |
| ASX MarkitDigital | Concluding the endpoint is permanently down | Endpoint is intermittently available; test live before assuming it needs an alternative |
| ASX MarkitDigital | Not checking the response JSON schema | The API returns `data.items[]` with `dateExpiry` and `pricePreviousSettlement` fields — validate these keys exist before parsing |
| GitHub Actions (daily + weekly) | Two workflows writing to `data/*.csv` and `public/data/status.json` without concurrency controls | Already fixed in v1.0: both workflows share `concurrency: group: data-pipeline, cancel-in-progress: false` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Fetching NAB PDF when HTML suffices | 3-5 second download per run; PDF parsing CPU usage; CI timeout risk | Use HTML extraction as primary approach | Immediately, on every CI run |
| No timeout on requests to optional sources | CI job hangs if Cotality/NAB server is slow | `DEFAULT_TIMEOUT = 30` already set in config.py; verify all `session.get()` calls use it | On first encounter with a slow or unresponsive server |
| Re-fetching full NAB/Cotality pages to check staleness | Unnecessary HTTP requests even when data is fresh | Check CSV `date` column first; only fetch if last row is > 28 days old | Not a performance issue at current scale, but avoids unnecessary scraping exposure |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Hardcoding a browser User-Agent that identifies the project | Gets the specific User-Agent blocked site-wide on Cotality/NAB | Use a generic current Chrome UA; rotate UA strings if blocked |
| Committing ASX/NAB response data to the repo with sensitive fields | Unlikely for public macro data, but API responses may include internal metadata | Only commit the derived CSV (`asx_futures.csv`, `nab_capacity.csv`) not raw API responses |
| Using PAT instead of GITHUB_TOKEN for auto-commit | PAT tokens trigger workflow re-runs, creating infinite commit loops | Already using GITHUB_TOKEN via `stefanzweifel/git-auto-commit-action@v7`; do not change |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Dashboard shows "8 of 8 indicators" when ASX futures data is 30+ days stale | User believes market expectations are current when they reflect stale futures pricing | Show `data_date` on the "What Markets Expect" section and warn if > 14 days old |
| Capacity utilisation value from NAB labelled only as "NAB Survey" | User has no idea if this is current or 3 months old | Surface the survey month/year alongside the indicator value |
| Housing indicator sourced from ABS TVD (quarterly) but displayed alongside monthly indicators | User perceives all indicators as equally current | Add a "(Quarterly)" label to the housing gauge; the status.json `frequency` field already supports this |

---

## "Looks Done But Isn't" Checklist

- [ ] **CoreLogic/Cotality scraper:** Check ToS decision is documented in plan — either "using ABS alternative" or "accepted ToS risk with justification." A scraper that runs successfully is NOT done if it violates Cotality's terms.
- [ ] **CoreLogic/Cotality URL:** Verify the target URL returns 200 with expected content — `corelogic.com.au` redirects are gone; `cotality.com` paths have changed.
- [ ] **NAB capacity utilisation:** Verify the regex matches the HTML text on the CURRENT month's page before committing the implementation. Run scraper locally and confirm the extracted value matches the published figure.
- [ ] **NAB discovery approach:** Confirm the tag archive page (`/tag/business-survey` or `/tag/economic-commentary`) returns the most recent survey link at the top of the listing.
- [ ] **ASX endpoint:** Run `curl https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures?days=365&height=1&width=1` before implementing. Confirm HTTP 200 and `data.items` array is present. Endpoint was 404 on 2026-02-07 but was 200 on 2026-02-24 — status is volatile.
- [ ] **ASX pipeline end-to-end:** The scraper code is already implemented. After confirming endpoint is live, the only remaining work is to verify CI runs succeed and `asx_futures.csv` is populated in the repo.
- [ ] **Status.json "8 of 8":** After all three scrapers succeed, verify the dashboard text changes from "Based on 5 of 8 indicators" to "Based on 8 of 8 indicators." This requires that all three optional INDICATOR_CONFIG stubs (`housing`, `business_confidence`, `asx_futures`) have `csv_file` set and the CSV files contain data.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| CoreLogic ToS violation discovered after scraper is live | MEDIUM | Swap to ABS Total Value of Dwellings data source; delete `corelogic_housing.csv` and rebuild with ABS data; update `INDICATOR_CONFIG["housing"]` csv_file pointer |
| Cotality URL structure changes and scraper breaks | LOW | The scraper already returns `{'status': 'failed'}` gracefully; update target URL in `config.py`; dashboard continues on stale data |
| NAB slug pattern breaks (new month uses different domain) | LOW | Add fallback to `news.nab.com.au` domain in scraper; discovery approach means only the tag archive URL needs updating |
| ASX endpoint goes 404 again | LOW | Scraper already handles this gracefully; no user-facing impact beyond hiding "What Markets Expect" section |
| PDF parsing added unnecessarily and breaks CI | MEDIUM | Remove pdfplumber/pypdf from requirements.txt; revert to HTML extraction approach |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Cotality ToS violation | PIPE-03 planning step (before implementation) | Plan explicitly states "using ABS alternative" or documents ToS risk decision |
| Cotality URL breakage (301 redirect to broken path) | PIPE-03 implementation | Manual `curl cotality.com/{target_path}` returns 200 with expected content |
| NAB PDF over-engineering | PIPE-04 planning step | Plan specifies HTML extraction as primary; PDF only as fallback |
| NAB URL slug non-discovery | PIPE-04 implementation | Scraper uses tag archive discovery, not hardcoded slug construction |
| ASX endpoint intermittent availability | HAWK-04 implementation | CI run produces populated `asx_futures.csv` with rows dated within 7 days |
| Silent stale data after source failure | All three phases | Status.json includes `data_date` for each optional indicator; dashboard shows staleness warning |

---

## Sources

- **Cotality Website Terms of Use** (Clause 8.4d): https://www.cotality.com/legals/website-terms — prohibits "any automated process (Scraping Process) to data mine, scrape, crawl... any Cotality Services, processes, information, content, or data accessible through this Website" (HIGH confidence — official legal document, fetched directly)
- **Cotality Product Terms and Conditions** (Clause A3.1g): https://www.cotality.com/au/legal/terms-conditions — extends prohibition to paid service customers (HIGH confidence — official legal document)
- **CoreLogic rebrand to Cotality (March 2025)**: https://www.mi-3.com.au/25-03-2025/corelogic-rebrands-cotality-signalling-global-expansion-and-innovation — confirmed domain migration (MEDIUM confidence — industry news, multiple sources agree)
- **CoreLogic data scraping litigation (BCI Media v CoreLogic)**: https://www.lawyerly.com.au/bci-media-takes-corelogic-to-court-over-data-scraping/ — signals active enforcement posture (MEDIUM confidence — Australian legal news)
- **NAB Monthly Business Survey page structure** (August 2025 and April 2025): Direct WebFetch verification — capacity utilisation is in HTML article body, not PDF-only (HIGH confidence — verified directly)
- **NAB URL patterns**: Confirmed consistent slug pattern `business.nab.com.au/nab-monthly-business-survey-{month}-{year}` with second domain `news.nab.com.au` for some releases; PDF paths vary across three different structures (HIGH confidence — verified via multiple direct URLs)
- **ASX MarkitDigital endpoint live status**: Direct WebFetch to `https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures?days=365&height=1&width=1` returned HTTP 200 with 17 contract items on 2026-02-24 (HIGH confidence — verified live)
- **Phase 7 verification (07-VERIFICATION.md)**: Endpoint was 404 as of 2026-02-07 — confirming intermittent availability pattern (HIGH confidence — project documentation)
- **ABS Total Value of Dwellings** as CoreLogic alternative: https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/total-value-dwellings — quarterly, compiled from CoreLogic sales data, open data terms (MEDIUM confidence — ABS official, but SDMX API dataflow ID needs verification before implementation)
- **GitHub Actions concurrency documentation**: https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency — already implemented in project (HIGH confidence — official docs)

---
*Pitfalls research for: Australian Economic Data Scraping (CoreLogic, NAB, ASX) — v1.1 milestone*
*Researched: 2026-02-24*
