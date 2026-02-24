# Phase 4: Hawk-O-Meter Gauges - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Visual traffic-light gauge system rendered with Plotly.js. Overall Hawk Score gauge + 6 individual metric gauges + ASX Futures probability display + plain-English interpretations. Does NOT include the calculator (Phase 5) or the statistical engine (Phase 3).

</domain>

<decisions>
## Implementation Decisions

### Gauge Visual Design
- **Overall Hawk Score:** Semicircle speedometer gauge with needle. Large and prominent as the hero element
- **Individual metric gauges:** Different style from overall — compact format (Claude decides exact style, but visually distinct from the big hero gauge)
- Green/Amber/Red color zones on all gauges (as decided in Phase 2)

### Gauge Layout & Grouping
- **Short labels** on individual gauges — just the category name: "Housing", "Jobs", "Spending", "Capacity", "Inflation", "Wages"
- Claude decides exact layout arrangement for 6 individual gauges (grid, list, etc.)

### Interpretation Text
- **Dynamic from data** — generate plain-English text from actual data values. E.g., "Housing up 12% YoY vs wages up 3%" rather than static template phrases
- **Verdict format: Label + sentence** — e.g., "HAWKISH — Multiple indicators suggest upward rate pressure"
- 5 stance labels: STRONGLY DOVISH / DOVISH / NEUTRAL / HAWKISH / STRONGLY HAWKISH (maps to 5 zones from Phase 3)

### ASX Futures Display
- **Table of outcomes** showing probabilities: cut / hold / hike with percentages
- **Placement:** Next to the overall Hawk Score gauge — they're complementary data points

### Claude's Discretion
- Exact Plotly.js gauge configuration
- Individual gauge compact style (horizontal bars, mini-semicircles, etc.)
- Layout arrangement of 6 gauges
- Dynamic text generation logic and phrasing
- Responsive behavior of gauge grid on mobile

</decisions>

<specifics>
## Specific Ideas

- Hero: big semicircle speedometer for the overall Hawk Score — this is what users see first
- ASX Futures sits alongside the hero gauge, showing market-implied probabilities
- Individual gauges are compact and secondary — a supporting cast to the main gauge
- Interpretation is data-driven, not template-driven — actual numbers in the text

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-hawk-o-meter-gauges*
*Context gathered: 2026-02-04*
