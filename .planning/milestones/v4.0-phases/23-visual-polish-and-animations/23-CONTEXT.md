# Phase 23: Visual Polish and Animations -- Implementation Context

**Generated:** 2026-02-26
**Method:** Synthetic discuss (5 agents: UX Designer, Engineer, Product Owner, QA/Edge Cases, Devil's Advocate)
**Phase Goal:** Users experience a visually cohesive dashboard with consistent typography, spacing, and colour hierarchy, plus animated entry effects on the hero score and gauge

---

## Phase Boundary

**In scope (POLX-01 through POLX-04, ANIM-01, ANIM-02):**
- CSS typography audit: establish and enforce a clear type hierarchy across all dashboard sections
- Spacing standardisation: consistent gaps, padding, and margins across all cards and sections
- Zone colour audit: verify zone colour appears on exactly 3 element types (verdict label, hero card border, explanation section headings) and nowhere else
- Mobile 375px above-fold verification: no congestion, no clipping, consistent spacing
- CountUp.js 2.9.0 from jsDelivr CDN: animated score count-up from 0 to live value on page load
- Plotly hero gauge sweep animation: gauge bar sweeps from 0 to live score on page load
- `prefers-reduced-motion` guards on both CountUp.js and gauge sweep (REQUIRED, not optional)

**Out of scope (not in this phase):**
- Any changes to the verdict explanation content or ranking logic (Phase 22, shipped)
- Any changes to the hero card DOM structure (Phase 21, shipped)
- Dark/light theme toggle (out of scope per REQUIREMENTS.md)
- Tailwind v4 or Plotly v3 upgrades (out of scope per REQUIREMENTS.md)
- Indicator delta badges (future: DELT-01)
- New sections or layout restructuring

---

## Implementation Decisions

### 1. Typography Hierarchy: Specific Size Tiers
**Decision:** LOCKED (5/5 consensus)
**Position:** Establish 5 tiers of typography, all using Inter (already loaded via Google Fonts CDN). Each tier maps to specific Tailwind utility classes. Do NOT introduce custom CSS font sizes -- use Tailwind's existing scale.

**Tiers:**

| Tier | Role | Tailwind Classes | Effective Size |
|------|------|-----------------|----------------|
| T1 - Hero Verdict | Verdict label in `#verdict-container` | `text-2xl sm:text-3xl font-bold` | 24px / 30px |
| T2 - Hero Score | `#hawk-score-display` number | `text-5xl sm:text-6xl font-bold` (unchanged) | 48px / 60px |
| T3 - Section Headings | `h2` elements for major sections | `text-xl font-semibold` (unchanged) | 20px |
| T4 - Card Headings / Labels | `h3`, `h4`, card labels | `text-base font-semibold` or `text-lg font-semibold` | 16px / 18px |
| T5 - Body / Metadata | Interpretation text, dates, sources | `text-sm` or `text-xs` | 14px / 12px |

**Rationale:** All 5 agents agreed that the current sizes are already close to correct after Phase 21's restructure. The verdict label in `#verdict-container` is currently `text-lg` (18px) which is SMALLER than section headings at `text-xl` (20px). This violates POLX-01 which requires the verdict to be the "largest above-the-fold text element" (excluding the score number). Bumping the verdict label to `text-2xl sm:text-3xl` (24px/30px) fixes this hierarchy inversion while keeping the hawk score number at T2 (`text-5xl sm:text-6xl`) as the largest numeral.

**Specific change:** In `#verdict-container`, change from `text-center text-lg` to `text-center text-2xl sm:text-3xl`. The JS-rendered `labelSpan` already has `font-bold` from `renderVerdict()`. No JS change needed -- only the HTML container class.

**Edge case (QA):** The verdict text wraps at 375px with `text-2xl`. At current typical verdict lengths ("RATES LIKELY FALLING -- The economy is..."), this wraps to 2 lines which is acceptable. Test that the longest possible verdict ("RATES LIKELY RISING -- The economy is running hot. Interest rates are more likely to go up.") does not push the score below the fold at 375px.

### 2. Spacing System: Consistent Section Gaps
**Decision:** LOCKED (4/5 majority)
**Position:** Standardise all section gaps to use `space-y-10` on the `<main>` element (already present, 2.5rem/40px gap). Within cards, standardise to `p-5` or `p-6` (consistent with Phase 21/22 patterns). Between elements inside cards, use `mt-2` to `mt-4` depending on visual grouping.

**Specific audit findings and fixes:**

| Element | Current | Target | Change |
|---------|---------|--------|--------|
| `<main>` container | `space-y-10` | `space-y-10` | No change |
| Hero card | `p-6` | `p-6` | No change |
| ASX futures card | `p-5` | `p-5` | No change |
| Cash rate card | `p-5` | `p-5` | No change |
| Countdown section | `px-6 py-5` | `px-6 py-5` | No change |
| Verdict explanation section | `px-6 py-5` | `px-6 py-5` | No change (Phase 22) |
| Metric gauge cards | `p-4` | `p-4` | No change |
| `#hawk-o-meter-section` | `mb-8` | Remove `mb-8` | `space-y-10` on main already handles gap |

**Rationale:** 4 agents (UX, Engineer, PO, QA) agreed the spacing is already quite consistent after Phase 21/22 work. The main issue is a redundant `mb-8` on `#hawk-o-meter-section` which creates an inconsistent 32px gap (vs the 40px from `space-y-10`). Removing it lets the parent `space-y-10` provide uniform 40px gaps.

**Dissent (Devil's Advocate):** Wanted to reduce `space-y-10` to `space-y-8` globally for tighter feel. Overruled -- 40px gap is appropriate for a data-dense dashboard with dark background; tighter spacing would make sections feel cramped.

### 3. Zone Colour Audit: Exactly 3 Element Types
**Decision:** LOCKED (5/5 consensus)
**Position:** Audit all colour application points and verify zone colour (`GaugesModule.getZoneColor()`) appears on exactly: (1) verdict label text in `renderVerdict()`, (2) hero card `borderTopColor`, and (3) explanation section headings in `renderVerdictExplanation()`. Remove any other zone colour applications found.

**Current zone colour inventory:**

| Location | Element | Application Method | Status |
|----------|---------|-------------------|--------|
| `interpretations.js:renderVerdict()` | Verdict `labelSpan` | `element.style.color = getZoneColor(score)` | KEEP (type 1) |
| `gauge-init.js:initGauges()` | Hero card border | `heroCard.style.borderTopColor = getZoneColor(score)` | KEEP (type 2) |
| `interpretations.js:renderVerdictExplanation()` | Hawkish heading | `element.style.color = getZoneColor(75)` | KEEP (type 3) |
| `interpretations.js:renderVerdictExplanation()` | Dovish heading | `element.style.color = getZoneColor(25)` | KEEP (type 3) |
| `gauges.js:createHeroGauge()` | Plotly title text | `font.color: getZoneColor(score)` | REVIEW |
| `gauges.js:createHeroGauge()` | Plotly gauge bar | `bar.color: getZoneColor(score)` | REVIEW |

**Resolution on Plotly gauge colours:** The Plotly gauge's internal zone colours (the 5-zone steps array) and the needle/bar colour are INTRINSIC to the gauge visualization -- they are part of the chart, not dashboard UI elements. The constraint "zone colour on exactly 3 element types" refers to TEXT and BORDER elements on the dashboard DOM, not Plotly's internal chart rendering. The Plotly title text duplicates the zone colour on the verdict label (both show the stance label with zone colour). Since the hero card now has a separate `#verdict-container` with the zone-coloured label, the Plotly title is redundant coloured text.

**Action:** Remove the zone-coloured title from the Plotly hero gauge trace. Set `title.text: ''` (empty string) on the hero gauge trace, since the verdict is displayed in the hero card now (Phase 21). This eliminates the redundant 4th zone colour application and simplifies the gauge visual.

### 4. CountUp.js Integration and Configuration
**Decision:** LOCKED (4/5 majority)
**Position:** Add CountUp.js 2.9.0 via jsDelivr CDN. Animate `#hawk-score-display` from 0 to live value on page load. Configuration: duration 1.5s, no decimals, easeOutExpo easing, separator off, suffix '/100'.

**CDN tag (add to `<head>` after Plotly):**
```html
<script src="https://cdn.jsdelivr.net/npm/countup.js@2.9.0/dist/countUp.umd.min.js"></script>
```

**Configuration:**
```javascript
var countUp = new countUp.CountUp('hawk-score-display', Math.round(hawkScore), {
  startVal: 0,
  duration: 1.5,
  useEasing: true,
  useGrouping: false,
  separator: '',
  suffix: '/100'
});
```

**Rationale:** 4 agents (UX, Engineer, PO, QA) agreed on 1.5s duration. UX argued for 2.0s ("feels more premium"), but Engineer and PO both flagged that users should see the actual number within 2 seconds of page load for usability. 1.5s is the sweet spot: noticeable animation but data is readable quickly. `easeOutExpo` (CountUp's default easing) decelerates naturally so the final digits resolve slowly, creating a "landing" feel.

**Dissent (Devil's Advocate):** Argued against CountUp.js entirely -- see Decision #6 below.

**prefers-reduced-motion guard (REQUIRED):**
```javascript
var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
if (reducedMotion) {
  scoreDisplay.textContent = Math.round(hawkScore) + '/100';
} else {
  var countUp = new countUp.CountUp(/* ... */);
  if (!countUp.error) countUp.start();
}
```

**Edge cases (QA):**
- Score of 0: CountUp handles `startVal === endVal === 0`; animation runs but shows "0/100"
- Score of 100: Valid; animation runs to 100 showing "100/100"
- CountUp CDN load failure: Check `typeof countUp !== 'undefined'` before instantiating. Fall back to static `textContent` assignment.
- Score changes mid-animation (impossible in current architecture since data is fetched once): not a concern

### 5. Plotly Hero Gauge Sweep Animation
**Decision:** LOCKED (5/5 consensus)
**Position:** Use `Plotly.animate()` to sweep the hero gauge from 0 to the live score. Do NOT use manual `requestAnimationFrame` frame stepping. Plotly's built-in animate API handles smooth transitions natively.

**Implementation approach:**
1. Create the hero gauge initially with `value: 0` (needle at zero)
2. After a 100ms delay (to let the initial render paint), call `Plotly.animate()` to transition to the live value
3. Animation duration: 1500ms (matching CountUp.js duration for synchronized feel)
4. Easing: `'cubic-out'` (Plotly's closest match to easeOutExpo)

**Code pattern:**
```javascript
function createHeroGaugeAnimated(containerId, hawkScore) {
  // Initial render at 0
  var trace0 = buildHeroTrace(0);
  Plotly.newPlot(containerId, [trace0], layout, config);

  // Animate to live value
  setTimeout(function () {
    var trace1 = buildHeroTrace(hawkScore);
    Plotly.animate(containerId, {
      data: [trace1]
    }, {
      transition: { duration: 1500, easing: 'cubic-out' },
      frame: { duration: 1500, redraw: true }
    });
  }, 100);
}
```

**Rationale:** All 5 agents agreed that `Plotly.animate()` is the correct API for smooth gauge transitions. Manual `requestAnimationFrame` stepping would require interpolating the trace value 60 times per second and calling `Plotly.react()` on each frame -- extremely expensive and jittery compared to Plotly's internal WebGL/SVG animation path. The 100ms initial delay ensures the zero-state gauge has rendered before the animation begins.

**prefers-reduced-motion guard (REQUIRED):**
```javascript
if (reducedMotion) {
  // Render directly at final value, no animation
  createHeroGauge(containerId, hawkScore);
} else {
  createHeroGaugeAnimated(containerId, hawkScore);
}
```

**Gauge bar colour during animation:** The gauge bar colour should transition from the zone colour at 0 (deep blue, `#1e40af`) to the zone colour at the final score. However, Plotly.animate() transitions the VALUE but not the bar.color property smoothly. Solution: set `bar.color` to the FINAL zone colour in both trace0 and trace1. The bar starts at 0 width with the final colour and sweeps to full -- visually coherent and avoids colour-during-animation complexity.

**Edge case (QA):** If the container is not visible (e.g., user scrolled away), `Plotly.animate()` still runs correctly and the gauge will show the final state when scrolled into view.

### 6. CountUp.js vs CSS-Only Alternative
**Decision:** Claude's Discretion (3/2 split)
**Position A (3 votes: UX, Engineer, PO):** Use CountUp.js 2.9.0. It's 4KB gzipped, mature, handles edge cases (0, 100, decimals), and provides `useEasing` with smooth deceleration that CSS cannot replicate for number counting. The dependency is justified by the quality of the animation.
**Position B (2 votes: QA, Devil's Advocate):** Use a CSS `@property` counter animation with `counter-reset` and `@keyframes`. Zero dependencies, ~20 lines of CSS.

**Analysis of Position B:**
```css
@property --score {
  syntax: '<integer>';
  initial-value: 0;
  inherits: false;
}
#hawk-score-display {
  transition: --score 1.5s ease-out;
  counter-reset: score var(--score);
}
#hawk-score-display::after {
  content: counter(score) '/100';
}
```
Problems: (1) `@property` has no Safari support before 15.4 (2022) -- acceptable but risky for older iOS devices common in AU mortgage-holder demographic. (2) Cannot use `textContent` for accessibility/screen readers -- `::after` pseudo-content is not consistently announced. (3) Requires managing the score display in both CSS and JS, creating a dual-source-of-truth bug risk.

**Resolution:** Use CountUp.js 2.9.0. The 4KB cost is negligible against Plotly.js (3.6MB) and Decimal.js already in the bundle. The library's error handling, easing, and cross-browser consistency justify the dependency. Add a CDN load failure guard to fall back to static text.

**Guard against CDN failure:**
```javascript
if (typeof countUp === 'undefined' || typeof countUp.CountUp !== 'function') {
  scoreDisplay.textContent = Math.round(hawkScore) + '/100';
} else {
  // Proceed with CountUp animation
}
```

---

## Specific Ideas

### Updated gauge-init.js initGauges() Flow

After `DataModule.fetch('data/status.json')` resolves:

```javascript
var reducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches;

// 1. Render hero gauge (with or without sweep animation)
requestAnimationFrame(function () {
  if (reducedMotion) {
    GaugesModule.createHeroGauge('hero-gauge-plot', data.overall.hawk_score);
  } else {
    GaugesModule.createHeroGaugeAnimated('hero-gauge-plot', data.overall.hawk_score);
  }
  requestAnimationFrame(function () {
    var heroEl = document.getElementById('hero-gauge-plot');
    if (heroEl && heroEl.data) {
      Plotly.Plots.resize('hero-gauge-plot');
    }
  });
});

// 2. Render verdict (unchanged)
InterpretationsModule.renderVerdict('verdict-container', data.overall);

// 3. Render hawk score with CountUp animation
var scoreDisplay = document.getElementById('hawk-score-display');
if (scoreDisplay) {
  var hawkScore = data.overall.hawk_score;
  if (reducedMotion || typeof countUp === 'undefined'
      || typeof countUp.CountUp !== 'function') {
    scoreDisplay.textContent = Math.round(hawkScore) + '/100';
  } else {
    scoreDisplay.textContent = '';
    var counter = new countUp.CountUp('hawk-score-display',
      Math.round(hawkScore), {
        startVal: 0,
        duration: 1.5,
        useEasing: true,
        useGrouping: false,
        separator: '',
        suffix: '/100'
      }
    );
    if (!counter.error) {
      counter.start();
    } else {
      scoreDisplay.textContent = Math.round(hawkScore) + '/100';
    }
  }
}

// 4-9. Rest of rendering (hero card border, jump link, ASX, freshness,
//    explanation section, metric gauges, missing cards, calculator bridge)
// ... unchanged ...

// 10. Hero card fadeSlideIn animation (only on success, already guarded)
if (heroCard && !reducedMotion) {
  heroCard.classList.add('hero-animate-in');
}
```

### New GaugesModule Function: createHeroGaugeAnimated()

Add alongside existing `createHeroGauge()`:

```javascript
function createHeroGaugeAnimated(containerId, hawkScore) {
  var container = document.getElementById(containerId);
  if (container) {
    while (container.firstChild) {
      container.removeChild(container.firstChild);
    }
  }

  // Build trace at value 0 but with final zone colour
  var trace0 = {
    type: 'indicator',
    mode: 'gauge+number',
    value: 0,
    title: { text: '' },
    number: {
      font: { size: 52, color: '#f3f4f6' },
      valueformat: '.0f',
      suffix: '/100'
    },
    gauge: {
      shape: 'angular',
      axis: {
        range: [0, 100],
        tickwidth: 1,
        tickcolor: '#4a4a4a',
        tickfont: { size: 12, color: '#9ca3af' }
      },
      bar: { color: getZoneColor(hawkScore), thickness: 0.6 },
      bgcolor: '#1f2937',
      borderwidth: 0,
      steps: getGaugeSteps(),
      threshold: {
        line: { color: '#fbbf24', width: 3 },
        thickness: 0.75,
        value: 50
      }
    },
    domain: { x: [0, 1], y: [0, 1] }
  };

  var layout = getDarkLayout();
  var config = { responsive: true, displayModeBar: false };

  Plotly.newPlot(containerId, [trace0], layout, config);

  // Animate to live value after initial paint
  setTimeout(function () {
    var trace1 = Object.assign({}, trace0, { value: hawkScore });
    Plotly.animate(containerId, {
      data: [trace1]
    }, {
      transition: { duration: 1500, easing: 'cubic-out' },
      frame: { duration: 1500, redraw: true }
    });
  }, 100);
}
```

**Export:** Add `createHeroGaugeAnimated` to the GaugesModule return object.

### Hero Gauge Title Removal

In both `createHeroGauge()` and `createHeroGaugeAnimated()`, change the title from:
```javascript
title: {
  text: getStanceLabel(hawkScore),
  font: { size: 20, color: getZoneColor(hawkScore) }
}
```
to:
```javascript
title: { text: '' }
```

Also remove the zone-coloured title from `updateHeroGauge()`.

**Rationale:** The verdict is now displayed in the hero card's `#verdict-container` (Phase 21). The Plotly gauge title was a redundant 4th zone colour application. Removing it satisfies POLX-02 (exactly 3 zone colour element types) and reduces visual clutter on the gauge.

### CSS Changes Summary

Minimal CSS additions needed:

1. **Verdict container class change** (in `index.html`):
   - From: `class="text-center text-lg"`
   - To: `class="text-center text-2xl sm:text-3xl"`

2. **Remove redundant margin** (in `index.html`):
   - On `#hawk-o-meter-section`: remove `mb-8` from class list (parent `space-y-10` provides uniform gaps)

3. **No new CSS keyframes needed** -- the `fadeSlideIn` from Phase 21 is sufficient

4. **No new `<style>` rules needed** -- all typography and spacing uses existing Tailwind utilities

### CountUp.js CDN Script Tag

Add to `<head>` after the Plotly script tag:
```html
<!-- CountUp.js for score animation (Phase 23: ANIM-01) -->
<script src="https://cdn.jsdelivr.net/npm/countup.js@2.9.0/dist/countUp.umd.min.js"></script>
```

### Playwright Test Compatibility

- No DOM structure changes -- all existing element IDs preserved
- The verdict container class change (`text-lg` to `text-2xl sm:text-3xl`) is CSS-only, no semantic impact
- The hero gauge title text removal may affect any test that checks for stance label text inside the Plotly SVG -- verify with `npx playwright test`
- CountUp.js animation will show the score counting up during test execution; Playwright's default timeout (30s) is well above the 1.5s animation duration
- Run all 28 Playwright tests after implementation

### Mobile 375px Verification Checklist (POLX-04)

1. Verdict label at `text-2xl` (24px) wraps cleanly inside hero card on 375px
2. Hawk score at `text-5xl` (48px) fits within hero card padding on 375px
3. Hero card + Plotly gauge stack vertically (hero first, gauge second) on mobile
4. No horizontal overflow or clipping on any section
5. `space-y-10` (40px) gap between sections is consistent
6. Verdict explanation section does not push metric gauges below second scroll

---

## Edge Cases (QA Agent Contributions)

### CountUp.js CDN Failure
- If the script fails to load (network error, CDN down), `countUp` global will be undefined
- Guard: check `typeof countUp !== 'undefined'` before instantiating
- Fallback: set `textContent` to static value

### Score of 0
- CountUp animates from 0 to 0: shows "0/100" immediately (no visible animation, which is correct)
- Plotly gauge bar stays at 0 width (correct for score of 0)

### Score of 100
- CountUp animates from 0 to 100: shows "100/100" after 1.5s
- Plotly gauge bar sweeps full width
- Verify "100/100" fits within `#hawk-score-display` at 375px (it does -- 7 characters at `text-5xl`)

### Slow Device Performance
- CountUp.js uses `requestAnimationFrame` internally and is CPU-light
- Plotly.animate() uses its own internal animation loop
- Both running simultaneously: tested pattern, Plotly's animation is independent of CountUp
- On very slow devices, animations may stutter but will always complete to final values

### prefers-reduced-motion: reduce
- Both animations skip entirely
- Static values displayed immediately
- Hero card `fadeSlideIn` already has CSS `@media (prefers-reduced-motion: reduce)` guard from Phase 21
- JS guard in gauge-init.js covers CountUp and Plotly animate

### Data Fetch Failure
- No animations run (they are all in the `.then()` success path)
- Error state shows "Unable to load economic data" (unchanged from current behaviour)

---

## Deferred Ideas

| Idea | Source Agent | Reason Deferred |
|------|-------------|-----------------|
| Staggered fade-in for individual metric gauge cards | UX Designer | Nice visual effect but not in POLX/ANIM requirements; scope creep |
| Animated gradient border on hero card (shimmering zone colour) | UX Designer | Visual complexity, potential performance cost, not in requirements |
| CountUp.js `onComplete` callback to trigger confetti/sparkle | Devil's Advocate | Unprofessional for a financial tool; violates "Data, not opinion" ethos |
| CSS custom properties for all spacing values (design tokens) | Engineer | Over-engineering for a static dashboard; Tailwind utilities are sufficient |
| Intersection Observer for scroll-triggered metric card animations | Engineer | Not in requirements; would add complexity for cards already visible on desktop |
| Dark/light theme preparation via CSS custom properties | Devil's Advocate | Explicitly out of scope per REQUIREMENTS.md |
| Reduce Plotly gauge number font size to avoid competing with CountUp score | QA/Edge Cases | The Plotly number is inside the SVG gauge and serves a different purpose (visual reference while interacting with gauge); keep both |

---

*Generated by synthetic multi-agent discuss. 5 agents, 6 gray areas, 6 decisions (5 locked, 1 discretion, 7 deferred).*
