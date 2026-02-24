# Phase 2: Core Dashboard - Context

**Gathered:** 2026-02-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Static HTML/JS dashboard on Netlify displaying current RBA cash rate, historical chart, next meeting date, source citations, and legal disclaimer. Does NOT include gauges, calculator, or the Hawk-O-Meter visualization (those are later phases).

</domain>

<decisions>
## Implementation Decisions

### Visual Style
- **Dark mode** (finance feel) — dark background, bright data. Like Bloomberg/TradingView aesthetic
- **Green/Amber/Red** color palette for gauge zones (when gauges arrive in Phase 4)
- Green = low rate pressure (dovish, safer for variable rate). Red = high rate pressure (hawkish)
- Color meaning is from a borrower's perspective — green is "less likely to rise"

### Page Structure
- **Single scroll page** — everything on one page: hero gauge area -> countdown -> chart -> (future: gauges -> calculator)
- **Hero element:** The Hawk-O-Meter gauge is front and center (Phase 4 will populate it; Phase 2 builds the layout with placeholder)
- Cash rate displayed prominently but secondary to the gauge

### Historical Rate Chart
- **Timeframe toggles:** 1Y / 5Y / 10Y / All
- **RBA annotations:** Vertical lines or dots on rate change dates. Hover shows +/- change amount
- No specific style preference — whatever works best for the data with dark theme
- Built with Plotly.js

### Meeting Countdown
- **Live countdown** — "Next meeting in 14 days, 3 hours" ticking in real time
- **Placement:** Near the top, below the hero gauge area, above the chart
- **Meeting day highlight:** Banner: "RBA meeting TODAY — decision expected 2:30pm AEST"

### Claude's Discretion
- Mobile responsive behavior (layout adaptation, chart interactivity on small screens)
- Exact Tailwind classes and spacing
- Chart color scheme within dark theme
- Loading states and error handling

</decisions>

<specifics>
## Specific Ideas

- Single-page dashboard that scrolls: hero -> countdown -> chart -> (future sections)
- Dark theme throughout — finance/data dashboard feel
- Live countdown that ticks, not just a static date
- RBA rate change events marked directly on the historical chart

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-core-dashboard*
*Context gathered: 2026-02-04*
