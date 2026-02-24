# Phase 3: Data Normalization & Z-Scores - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Python statistical engine that transforms raw economic metrics into normalized 0-100 gauge values via Z-scores. Covers normalization formulas, rolling window statistics, gauge mapping, and the status.json output contract. Does NOT include the frontend visualization (Phase 4) or data ingestion (Phase 1).

</domain>

<decisions>
## Implementation Decisions

### COVID Outlier Handling
- **Robust statistics** — use Median/IQR instead of Mean/StdDev for the rolling window. Naturally resistant to outliers without dropping data
- Future black swan events: **flag extreme values** (>3 IQR) but let them through. Manual review if needed — no auto-clipping

### Gauge Weighting
- **Configurable weights** in a `weights.json` file. Start with a defensible default, document reasoning, adjust over time
- Can A/B test equal vs weighted approaches against historical RBA decisions
- **Weights are transparent** — shown to users on the dashboard so they can see how each metric contributes to the overall Hawk Score

### Z-Score to Gauge Mapping
- **Linear mapping** — Z = -2 maps to 0, Z = +2 maps to 100. Clip anything beyond. Simple and transparent
- **5 zones:** Cold | Cool | Neutral | Warm | Hot (fills the gaps in the original 3-zone design)
  - Cold: 0-20 (Z < -1.5)
  - Cool: 20-40 (Z -1.5 to -0.5)
  - Neutral: 40-60 (Z -0.5 to +0.5)
  - Warm: 60-80 (Z +0.5 to +1.5)
  - Hot: 80-100 (Z > +1.5)

### status.json Contract
- **Rich metadata** — include raw values, Z-scores, data source timestamps, staleness flags, and confidence levels alongside the gauge scores
- **Include recent history** — last 12 data points in status.json for sparklines/mini-charts in the frontend
- Overall hawk score, per-gauge values, verdict text, and weights all included

### Claude's Discretion
- Exact IQR calculation implementation
- Rolling window edge cases (what happens with < 10 years of data)
- status.json schema field naming
- Confidence level calculation methodology

</decisions>

<specifics>
## Specific Ideas

- Normalization formulas from DESIGN.md: Housing = Median Price / Average Weekly Earnings, Jobs = Job Ads / Working Age Population * 1000, Spending = Turnover / (CPI/Base CPI), Capacity = already a ratio, Inflation = already % change
- weights.json approach enables backtesting against historical RBA decisions
- Transparency is core — users see the weights and can understand the methodology

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-data-normalization-z-scores*
*Context gathered: 2026-02-04*
