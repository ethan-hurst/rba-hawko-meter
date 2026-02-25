# Plan 21-01 Summary: Hero HTML Restructure

**Status:** Complete
**Phase:** 21 - Hero HTML Restructure
**Completed:** 2026-02-26

## What Was Built

Hero section DOM restructure transforming the Hawk-O-Meter from a data-dense layout into a polished above-the-fold experience:

1. **Inter font loading (HERO-01):** Added Google Fonts preconnect and Inter 400/600/700 weights. Extended Tailwind fontFamily config with Inter as primary sans-serif.

2. **Hero card container (HERO-02, HERO-03, HERO-04, HERO-05):** Created `#hero-card` wrapper containing verdict label, hawk score display (`#hawk-score-display` with text-5xl sm:text-6xl), scale explainer, data freshness badge (`#hero-freshness`), and calculator jump link. Zone-coloured top border via `element.style.borderTopColor`.

3. **Plotly zero-width prevention (HERO-06):** Wrapped `createHeroGauge()` in double `requestAnimationFrame()` with `Plotly.Plots.resize()` to prevent zero-width render after DOM restructure.

4. **fadeSlideIn animation (HERO-06):** CSS keyframe animation with 300ms ease-out. `prefers-reduced-motion` media query disables animation for accessibility.

5. **Mobile-first ordering:** `order-first lg:order-none` ensures hero card renders above gauge on mobile viewports.

## Key Files

### Modified
- `public/index.html` — Inter font tags, Tailwind config, CSS keyframes, hero section restructure (+44/-10 lines)
- `public/js/gauge-init.js` — rAF gauge wrapper, score display, zone border, freshness target, animation trigger (+39/-4 lines)

## Commits
1. `1457224` — feat(21-01): hero HTML restructure with Inter font, zone border, and fadeSlideIn

## Test Results
- 28 Playwright E2E tests: PASSED
- All pytest unit tests: PASSED
- No zero-width Plotly render regression

## Requirements Addressed
- HERO-01: Verdict label as largest above-fold text element
- HERO-02: Hawk score displayed as "N/100" prominently
- HERO-03: Scale explainer inside hero card, adjacent to verdict
- HERO-04: Data freshness badge inside hero card
- HERO-05: Zone-coloured accent border on hero card
- HERO-06: fadeSlideIn animation with prefers-reduced-motion guard

## Self-Check: PASSED
