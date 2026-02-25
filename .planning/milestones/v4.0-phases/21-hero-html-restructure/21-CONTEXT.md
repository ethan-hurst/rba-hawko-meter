# Phase 21: Hero HTML Restructure -- Implementation Context

**Generated:** 2026-02-26
**Method:** Synthetic discuss (5 agents: UX Designer, Engineer, Product Owner, QA/Edge Cases, Devil's Advocate)
**Phase Goal:** Users see the verdict and hawk score as the dominant above-the-fold experience with a stable, correctly-sized DOM ready for JS and CSS work

---

## Phase Boundary

**In scope (HERO-01 through HERO-06):**
- New `#hero-card` wrapper element with zone-coloured accent border
- Verdict label as dominant above-the-fold text (largest on page)
- Hawk score as prominent DOM number ("38/100") inside hero card
- Scale explainer text adjacent to verdict inside hero card
- Data freshness badge inside hero card
- fadeSlideIn CSS keyframe animation triggered on data load
- Inter font via Google Fonts CDN (preconnect + link tag)
- Tailwind config extension for hero-specific design tokens
- `requestAnimationFrame` wrapper for `createHeroGauge()` after DOM restructure

**Out of scope (deferred to Phase 22/23):**
- Verdict explanation section (Phase 22: EXPL-01 through EXPL-04)
- CountUp.js score animation (Phase 23: ANIM-01)
- Plotly gauge sweep animation (Phase 23: ANIM-02)
- Typography audit and spacing standardisation (Phase 23: POLX-01 through POLX-04)
- Any changes to metric gauge cards, calculator, methodology, or footer sections

---

## Implementation Decisions

### 1. Hero Card DOM Structure
**Decision:** LOCKED (5/5 consensus)
**Position:** Create a new `#hero-card` div that wraps the verdict label, hawk score number, scale explainer, and data freshness badge. Do NOT move the Plotly gauge container (`#hero-gauge-plot`). The hero card sits alongside the gauge in the existing grid, not around it.

**Rationale:** All 5 agents agreed on the core principle: the Plotly gauge must stay in its current DOM position to avoid zero-width rendering bugs (critical pitfall from MEMORY.md). The hero card is a new visual wrapper for text content only. The `#verdict-container` element gets absorbed into the hero card as a child (keeping its ID for Playwright test compatibility). The `#scale-explainer` and `#calculator-jump-link` elements also move inside the hero card.

**Concrete structure:**
```
#hawk-o-meter-section
  #data-freshness (REMOVE -- content moves into hero card)
  .grid.grid-cols-1.lg:grid-cols-5
    .lg:col-span-3
      #hero-gauge-plot (UNCHANGED -- Plotly stays here)
    .lg:col-span-2
      #hero-card (NEW -- replaces the current space-y-4 wrapper)
        #verdict-container (MOVED INSIDE -- keep ID)
        #hawk-score-display (NEW -- "38/100" DOM element)
        #scale-explainer (MOVED INSIDE -- keep ID)
        #hero-freshness (NEW -- freshness badge)
        #calculator-jump-link (MOVED INSIDE -- keep ID)
      #asx-futures-container (STAYS -- below hero card)
      Cash Rate card (STAYS -- below ASX)
```

### 2. Mobile (375px) vs Desktop (1440px) Layout
**Decision:** LOCKED (4/5 majority)
**Position:** On mobile, stack vertically: hero card (verdict + score) ABOVE the Plotly gauge. On desktop (lg+), use the existing 3+2 grid with gauge left and hero card in the right column.

**Rationale:** 4 agents (UX, Engineer, PO, QA) agreed that on 375px screens, the verdict label and hawk score must be visible without scrolling (success criterion #1). The Plotly gauge at `min-height: 280px` consumes too much vertical space to fit both. Solution: on mobile, the hero card content appears first (verdict label + score), then the gauge appears below. On desktop, the side-by-side layout works naturally.

**Dissent (Devil's Advocate):** Argued the gauge should be smaller on mobile rather than pushed below the fold. Overruled because reducing gauge height below ~200px makes it unreadable.

**Implementation:** Use `order-first lg:order-none` on the hero card wrapper in the right column so it renders first on mobile (stacked) but stays in the right column on desktop (grid).

### 3. Hawk Score as Separate DOM Element
**Decision:** LOCKED (5/5 consensus)
**Position:** Add a new `#hawk-score-display` DOM element inside the hero card that shows the hawk score as "38/100". Keep Plotly's built-in number display on the gauge as well.

**Rationale:** HERO-02 requires the score as a "prominent number alongside the verdict inside the hero card." The Plotly gauge number is embedded inside the SVG chart and cannot be independently styled for typography hierarchy. All 5 agents agreed a separate DOM element is needed. The value is set in `gauge-init.js` after data loads: `element.textContent = Math.round(hawkScore) + '/100'`.

**Edge case (QA):** Use `Math.round()` to ensure the DOM number matches Plotly's `.0f` format. Handle `hawkScore` of 0 and 100 as valid values.

### 4. Zone-Coloured Accent Border
**Decision:** LOCKED (4/5 majority)
**Position:** Use `element.style.borderTopColor` with `GaugesModule.getZoneColor(hawkScore)` for a 4px top border accent on the hero card. Static Tailwind class: `border-t-4` (full literal string). Color set via JS after data loads.

**Rationale:** 3 agents (Engineer, PO, QA) favoured left border, but Devil's Advocate raised a valid point: `border-l-4` with `rounded-xl` creates an uneven visual where the left border edge is not rounded. `border-t-4` works cleanly with `rounded-xl` because the top border flows into the border-radius. UX Designer then switched to top border, creating 4/5 majority.

**Implementation:**
- Static class on hero card: `border-t-4 border-transparent` (Tailwind literal, no concatenation)
- JS in `gauge-init.js` `.then()`: `heroCard.style.borderTopColor = GaugesModule.getZoneColor(data.overall.hawk_score);`
- Never concatenate Tailwind color classes dynamically (pitfall #2 from MEMORY.md)

### 5. Data Freshness Badge Inside Hero Card
**Decision:** LOCKED (4/5 majority)
**Position:** Create a new `#hero-freshness` element inside the hero card at the bottom. Remove or hide the existing `#data-freshness` element above the grid. Render freshness content into the new element using existing `InterpretationsModule.renderStalenessWarning()` logic.

**Rationale:** HERO-04 requires the freshness badge "inside the hero card." The current `#data-freshness` is above the grid and outside any card. Moving the content inside the hero card satisfies the requirement. 4 agents agreed to create a new target element inside the hero card rather than moving the existing `#data-freshness` div (which would break the semantic relationship to the grid section).

**Dissent (Devil's Advocate):** Wanted to keep `#data-freshness` in its current position and add a duplicate inside the hero. Overruled as unnecessary duplication.

**Edge case (QA):** If `generated_at` is null, `renderStalenessWarning` returns early -- hero card must render correctly without the badge (no empty element visible). Use the same function but target `hero-freshness` instead of `data-freshness`.

### 6. fadeSlideIn Animation Trigger
**Decision:** Claude's Discretion (3/2 split)
**Position A (3 votes: UX, PO, QA):** Trigger fadeSlideIn AFTER data loads, in the `.then()` callback of `initGauges()`. User sees a loading skeleton first, then the hero card animates in with real data.
**Position B (2 votes: Engineer, Devil's Advocate):** Keep animation simple -- a gentle 200-300ms opacity fade, not a dramatic slide. Apply via adding a CSS class after data loads.

**Resolution:** Both positions are compatible. Apply a CSS class `hero-animate-in` to the hero card after data loads (Position A timing). The animation itself is a gentle `fadeSlideIn` keyframe: `opacity 0->1 + translateY 8px->0` over 300ms ease-out (merging Position B's restraint with HERO-06's requirement). Respect `prefers-reduced-motion` via `window.matchMedia('(prefers-reduced-motion: reduce)')` check before adding the class.

**Edge case (QA):** Do NOT animate on data fetch failure. Only add animation class in the success path.

---

## Specific Ideas

### Hero Card Rendering Flow in gauge-init.js
After `DataModule.fetch('data/status.json')` resolves:
1. Get or create `#hero-card` element
2. Set `#hawk-score-display` textContent to `Math.round(hawkScore) + '/100'`
3. Set hero card `borderTopColor` via `element.style.borderTopColor = GaugesModule.getZoneColor(hawkScore)`
4. Call `InterpretationsModule.renderVerdict('verdict-container', data.overall)` (unchanged)
5. Call `InterpretationsModule.renderStalenessWarning('hero-freshness', data.generated_at)`
6. Remove or hide `#data-freshness` above the grid
7. Wrap `GaugesModule.createHeroGauge('hero-gauge-plot', hawkScore)` in `requestAnimationFrame()`
8. Check `prefers-reduced-motion` and add `hero-animate-in` class if permitted
9. Call `Plotly.Plots.resize('hero-gauge-plot')` in a second `requestAnimationFrame()`

### CSS Additions (in `<style>` block)
```css
/* Hero card entry animation */
@keyframes fadeSlideIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
.hero-animate-in {
  animation: fadeSlideIn 300ms ease-out both;
}
@media (prefers-reduced-motion: reduce) {
  .hero-animate-in { animation: none; }
}
```

### Inter Font Loading
Add to `<head>` before Tailwind CDN:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
```
The font is already in Plotly's font stack (`Inter, system-ui, sans-serif` in `getDarkLayout()`) but was never loaded. This activates it.

### Playwright Test Compatibility
- Keep `#verdict-container` as an element ID inside the hero card
- Keep `#hero-gauge-plot` in its current DOM position
- Keep `#metric-gauges-grid` structurally separate from the hero section
- Run all 28 Playwright tests after every structural HTML change

### Tailwind Config Extension
Add to existing `tailwind.config.theme.extend`:
```javascript
fontFamily: {
  'sans': ['Inter', 'system-ui', 'sans-serif']
},
keyframes: {
  fadeSlideIn: {
    '0%': { opacity: '0', transform: 'translateY(8px)' },
    '100%': { opacity: '1', transform: 'translateY(0)' }
  }
},
animation: {
  'fade-slide-in': 'fadeSlideIn 300ms ease-out both'
}
```
Note: The CSS keyframe approach is preferred over Tailwind config for the animation since the `prefers-reduced-motion` guard needs a media query wrapper. Keep keyframes in `<style>` block.

---

## Deferred Ideas

| Idea | Source Agent | Reason Deferred |
|------|-------------|-----------------|
| Reduce Plotly gauge size on mobile instead of reordering | Devil's Advocate | Gauge below ~200px is unreadable; reorder approach is cleaner |
| Loading skeleton placeholder for hero card | UX Designer | Nice-to-have but adds complexity; simple "Loading..." text suffices for Phase 21 |
| Score change indicator (delta badge) | Product Owner | Requires `previous_value` in status.json (DELT-01, future requirement) |
| Animated gradient border instead of solid colour | UX Designer | Visual polish item, belongs in Phase 23 (POLX-02) |
| Separate hero card JS module | Engineer | Over-engineering for 6 requirements; keep in gauge-init.js for now |
| Duplicate freshness badge in both hero and grid header | Devil's Advocate | Unnecessary duplication; single badge inside hero satisfies HERO-04 |
