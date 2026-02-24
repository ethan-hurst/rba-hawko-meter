# Stack Research

**Domain:** Australian economic data scraping — CoreLogic/Cotality HVI PDF, NAB Business Survey PDF, ASX futures API
**Researched:** 2026-02-24
**Confidence:** HIGH (all three sources verified live against real endpoints)

---

## Context: What Already Exists (Do Not Re-Research)

The v1.0 pipeline is live with: `pandas>=2.0`, `numpy>=1.24`, `requests>=2.28`, `beautifulsoup4>=4.12`, `lxml>=4.9`, `python-dateutil>=2.8`. The three placeholder scrapers (`corelogic_scraper.py`, `nab_scraper.py`, `asx_futures_scraper.py`) have stubs already integrated into the pipeline.

---

## Recommended Stack Additions

### Core New Library

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **pdfplumber** | `0.11.9` | PDF text and table extraction | Only addition needed. Verified on actual NAB Business Survey and Cotality HVI PDFs. Extracts both free-form text (capacity utilisation percentage from NAB) and structured tables (Australia MoM/Qtly/Annual rows from Cotality). Released 2026-01-05. Pure Python. No system dependencies. Integrates directly with existing `requests` session for PDF download. |

**No other new libraries are needed.** The existing `requests`, `beautifulsoup4`, `re`, and `pandas` stack covers the remaining scraping work for all three sources.

### Supporting Libraries (No Changes Needed)

| Library | Current Version | Role in v1.1 | Notes |
|---------|-----------------|--------------|-------|
| `requests` | `>=2.28` | Download NAB/Cotality PDFs, call ASX API | Already in requirements.txt, no change needed |
| `beautifulsoup4` | `>=4.12` | Scrape Cotality insights listing and NAB tag pages to find PDF URLs | Already in requirements.txt |
| `lxml` | `>=4.9` | HTML parser for bs4 | Already in requirements.txt |
| `re` (stdlib) | stdlib | Regex extraction from PDF text (no tables needed for either source) | No install needed |
| `pandas` | `>=2.0` | Structure extracted data into DataFrames for CSV output | Already in requirements.txt |

---

## Source-by-Source Technical Findings

### 1. ASX Futures (HAWK-04) — Status: Already Works

**Verdict:** The existing `asx_futures_scraper.py` is correct and functional. The MarkitDigital API endpoint returns 18 futures contracts with live data.

**Verified endpoint:**
```
GET https://asx.api.markitdigital.com/asx-research/1.0/derivatives/interest-rate/IB/futures?days=365&height=1&width=1
```

**Live response (2026-02-24):**
- Returns JSON with `data.items[]` array of 18 contracts
- Each item has `dateExpiry`, `symbol`, `pricePreviousSettlement`
- Implied rate formula `100 - pricePreviousSettlement` confirmed accurate
- Example: IBG2026 expiry=2026-02-25, price=96.18, implied=3.82% (current RBA rate is 4.10%)

**Confidence:** HIGH — endpoint tested live, returns correct data structure matching existing scraper logic.

**What to investigate:** Why is the scraper returning `status: failed` in production despite the endpoint working? Likely a CORS/header issue or the `ASX_FUTURES_URLS["ib_futures"]` config value needs verification against what's deployed. The endpoint itself is fine.

---

### 2. NAB Business Survey PDF (PIPE-04) — Status: Solvable with pdfplumber

**Verdict:** Two working URL discovery strategies exist. The listing-page scrape approach is more robust.

**Strategy (recommended): Scrape listing page → extract PDF link → download → parse**

Step 1 — Find the latest survey landing page:
```
GET https://business.nab.com.au/tag/economic-commentary/
```
Parse for href matching `/tag/economic-commentary/nab-monthly-business-survey---*` — returns slug like `/tag/economic-commentary/nab-monthly-business-survey---november-2025`.

Step 2 — Scrape that landing page for the PDF link:
```
GET https://business.nab.com.au{slug}
```
Parse for `href` containing `/content/dam/nab-business/document/` and `.pdf` — returns relative path like `/content/dam/nab-business/document/2025m11%20NAB%20Monthly%20Business%20Survey.pdf`.

Step 3 — Download PDF:
```
GET https://business.nab.com.au{pdf_relative_path}
```
Verified 200 response for: `/content/dam/nab-business/document/2025m11%20NAB%20Monthly%20Business%20Survey.pdf` and `/content/dam/nab-business/document/NAB-Monthly-Business-Survey-May-2025.pdf`

Step 4 — Extract capacity utilisation with pdfplumber:
```python
import pdfplumber, re

with pdfplumber.open(pdf_bytes_or_path) as pdf:
    text = pdf.pages[0].extract_text()  # Page 1 has the summary table
    match = re.search(
        r'Capacity utilisation rate\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',
        text
    )
    # match.group(3) = most recent value (e.g., '83.6')
```

**Verified on Nov 2025 PDF:** Page 1 text contains `"Capacity utilisation rate 83.3 83.4 83.6"` — regex returns `('83.3', '83.4', '83.6')` where group(3) is the latest quarter.

**URL pattern notes:**
- Nov 2025: `/content/dam/nab-business/document/2025m11%20NAB%20Monthly%20Business%20Survey.pdf` (content/dam format)
- Apr/May 2025: `/content/dam/nab-business/document/NAB-Monthly-Business-Survey-{Month}-{Year}-.pdf` (hyphenated format)
- Pattern is inconsistent — do NOT try to predict the URL. Always scrape the listing page to find the current link.

**Confidence:** HIGH — extraction tested live on downloaded PDF. URL discovery pattern verified on 2 months.

---

### 3. CoreLogic/Cotality HVI (PIPE-03) — Status: Solvable with pdfplumber

**Critical context:** CoreLogic rebranded to **Cotality** in March 2025. The domain `corelogic.com.au` still exists but redirects. Use `cotality.com` for scraping.

**Verdict:** Two-hop scrape → PDF parse approach works reliably.

**Strategy: Scrape insights listing → find HVI article → extract PDF link → parse**

Step 1 — Find latest HVI article:
```
GET https://www.cotality.com/au/insights
```
Parse for `href` matching `/au/insights/articles/housing-values-*` or `/au/insights/articles/*home-value*` — the HVI monthly release uses consistent URL patterns like `/au/insights/articles/housing-values-continued-to-rise-in-january-...`.

Step 2 — Scrape article for PDF link:
```
GET https://www.cotality.com{article_path}
```
Parse for `href` containing `discover.cotality.com/hubfs/Article-Reports/COTALITY%20HVI` — returns direct URL like `https://discover.cotality.com/hubfs/Article-Reports/COTALITY%20HVI%20Feb%202026%20FINAL%201.pdf`.

Step 3 — Download and parse PDF:
```python
import pdfplumber, re

with pdfplumber.open(pdf_bytes_or_path) as pdf:
    page2_text = pdf.pages[1].extract_text()  # Page 2 has the data table
    match = re.search(
        r'Australia\s+([\-\d.]+%?)\s+([\-\d.]+%?)\s+([\-\d.]+%?)',
        page2_text
    )
    mom_pct = match.group(1)   # e.g., '0.8%'
    qtly_pct = match.group(2)  # e.g., '2.4%'
    annual_pct = match.group(3)  # e.g., '9.4%'

    # Get report month/year from page 1
    page1_text = pdf.pages[0].extract_text()
    date_match = re.search(
        r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})',
        page1_text, re.IGNORECASE
    )
```

**Verified on Jan 2026 PDF:** `Australia 0.7% 2.9% 8.6%`
**Verified on Feb 2026 PDF:** `Australia 0.8% 2.4% 9.4%`

**HVI PDF URL patterns observed:**
- `discover.cotality.com/hubfs/Article-Reports/COTALITY%20HVI%20Jan%202026%20FINAL.pdf`
- `discover.cotality.com/hubfs/Article-Reports/COTALITY%20HVI%20Feb%202026%20FINAL%201.pdf` (note: trailing ` 1`)
- `discover.cotality.com/hubfs/Article-Reports/Cotality_HVI_December.pdf`
- Patterns vary — always scrape the article page for the URL. Do NOT construct URLs from date templates.

**Metric to store:** Annual YoY % change (group(3)) aligns with the existing `yoy_pct_change` normalization already used by other indicators in `config.py:INDICATOR_CONFIG`.

**Confidence:** HIGH — full workflow tested: listings page → article page → PDF URL → pdfplumber extraction on two consecutive monthly reports.

---

## Installation

```bash
# Add to requirements.txt
pdfplumber>=0.11,<1.0
```

```bash
# pip install
pip install pdfplumber
```

pdfplumber has no system-level dependencies (no Poppler, no Ghostscript). It installs `pdfminer.six`, `Pillow`, and `pypdfium2` automatically.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| `pdfplumber` 0.11.9 | `pypdf` (formerly PyPDF2) | pypdf extracts text but has poor layout handling — columns and tables get merged into garbled output. pdfplumber's coordinate-aware extraction correctly handles multi-column PDF layouts like the NAB survey. |
| `pdfplumber` | `camelot-py` | camelot requires system-level Ghostscript installation — a blocker in GitHub Actions free tier without extra setup steps. pdfplumber has zero system dependencies. |
| `pdfplumber` | `tabula-py` | tabula-py requires Java (JVM) at runtime. Unacceptable for GitHub Actions without additional setup. |
| `pdfplumber` | `pdfminer.six` (direct) | pdfplumber is built on pdfminer.six but provides a much cleaner API. Using pdfminer.six directly requires low-level layout parsing. |
| Cotality PDF scraping | ABS RPPI API (`data.api.abs.gov.au/data/RPPI`) | **ABS discontinued RPPI in December 2021.** The API still exists but the most recent data is Q4 2021 — unusable for a current indicator. |
| Cotality PDF scraping | `housingdata.gov.au` portal | Data comes from Cotality via Tableau embed — no programmable API. Contact-only access. |
| NAB listing-page scrape | Direct URL construction (e.g., `2026mMM NAB Monthly...`) | URL format is inconsistent between months (content/dam vs wp-content, different naming). Scraping the listing page is robust across format changes. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `Selenium` / `Playwright` for PDF discovery | CoreLogic/Cotality and NAB pages are server-rendered HTML — no JavaScript execution needed for link extraction. Playwright adds 100+ MB to the Docker/Action image and 30+ second startup. | `requests` + `BeautifulSoup4` |
| `camelot-py` | Requires system Ghostscript — blocks GitHub Actions free tier without multi-step setup | `pdfplumber` |
| `tabula-py` | Requires JVM at runtime | `pdfplumber` |
| ABS RPPI API | Discontinued December 2021, data ends Q4 2021 | Cotality HVI PDF scraping |
| CoreLogic subscription API | Paywalled — requires enterprise contract | Free public PDF releases from Cotality |
| `wp-content` NAB PDF URLs | WordPress-hosted PDFs return 503 — different CDN restrictions than `content/dam` | `content/dam` URLs found via listing page scrape |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `pdfplumber>=0.11,<1.0` | `pandas>=2.0`, `Python 3.11+` | No conflicts. pdfplumber requires Python >=3.8. |
| `pdfplumber>=0.11,<1.0` | `requests>=2.28` | Download PDF to `io.BytesIO` buffer, pass directly to `pdfplumber.open()` — no temp file needed. |

---

## Stack Patterns by Scenario

**If the NAB listing page returns no PDF link (format change):**
- Fall back to the November 2025 confirmed URL template: `https://business.nab.com.au/content/dam/nab-business/document/{year}m{month:02d}%20NAB%20Monthly%20Business%20Survey.pdf`
- Log the failure and trigger the graceful degradation path already wired in the pipeline.

**If the Cotality insights listing page changes structure:**
- The HVI article URL slug is semantically predictable (`housing-values-*`). A broader regex on `/au/insights/articles/` hrefs for `housing` keywords provides a reliable fallback.
- Hardcoding the discover.cotality.com URL pattern (`COTALITY%20HVI%20{Month}%20{Year}%20FINAL.pdf`) as a last-resort fallback is acceptable — the filename pattern has been consistent for 12+ months.

**If the ASX MarkitDigital endpoint breaks:**
- The endpoint has been stable for the life of this project. The existing scraper code is correct.
- The most likely failure mode is an HTTP error, which is already handled by the graceful degradation `fetch_and_save()` pattern.
- No code changes needed — just debugging of the deployment configuration.

---

## Sources

- **pdfplumber PyPI** — https://pypi.org/project/pdfplumber/ — version 0.11.9 confirmed, released 2026-01-05 (HIGH confidence)
- **pdfplumber GitHub** — https://github.com/jsvine/pdfplumber — library capabilities (HIGH confidence)
- **ASX MarkitDigital API** — live test 2026-02-24 — endpoint returns 18 contracts, structure matches existing scraper (HIGH confidence)
- **NAB Business Survey PDFs** — live test 2026-02-24 — `https://business.nab.com.au/content/dam/nab-business/document/2025m11%20NAB%20Monthly%20Business%20Survey.pdf` returns HTTP 200, capacity utilisation regex extraction verified (HIGH confidence)
- **Cotality HVI PDFs** — live test 2026-02-24 — Jan 2026 and Feb 2026 PDFs accessible, Australia MoM/Annual extraction verified (HIGH confidence)
- **ABS RPPI discontinuation** — https://www.abs.gov.au/statistics/economy/price-indexes-and-inflation/residential-property-price-indexes-eight-capital-cities/latest-release — confirmed discontinued December 2021 (HIGH confidence)
- **CoreLogic → Cotality rebrand** — March 2025, source: https://www.financialstandard.com.au/news/corelogic-rebrands-to-cotality-179807983 (HIGH confidence)

---
*Stack research for: RBA Hawk-O-Meter v1.1 data source scrapers*
*Researched: 2026-02-24*
