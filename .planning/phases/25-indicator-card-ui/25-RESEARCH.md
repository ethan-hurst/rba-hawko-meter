# Phase 25: Indicator Card UI - Research

**Researched:** 2026-02-26
**Domain:** Canvas 2D sparklines + DOM delta badges (vanilla JS IIFE)
**Confidence:** HIGH

## Summary

Phase 25 adds two visual features to the existing indicator card UI: delta badges showing directional change magnitude, and Canvas 2D sparklines showing trend history. All implementation uses vanilla JS IIFE modules matching the project's existing architecture -- no build system, no npm, no ESM imports.

The codebase already provides all necessary data contracts. Phase 24 delivered `previous_value`, `delta`, and `delta_direction` fields per gauge, plus `previous_hawk_score` and `hawk_score_delta` in the overall block. The pre-existing `history[]` arrays provide sparkline data. The `GaugesModule.getZoneColor()` function provides zone-based hex colours via `element.style`.

**Primary recommendation:** Create a single new `sparklines.js` IIFE module for Canvas 2D rendering, add delta badge creation as a helper in `InterpretationsModule`, and integrate both into the existing `gauge-init.js` orchestration flow.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
1. **Delta badge placement: in the card header row** (5/5 consensus) -- 3-item flex: label (left), delta badge (center/right), importance badge (far right)
2. **Hero hawk score delta: below the score as a separate element** (5/5) -- new `div#hero-delta` between `#hawk-score-display` and `#scale-explainer`
3. **Sparkline module: new `sparklines.js` IIFE module** (4/5) -- single public function `SparklineModule.draw(canvasElement, historyArray, color)`, loads after gauges.js, before interpretations.js
4. **Sparkline visual design: stroke-only with end-dot** (5/5) -- 1.5px line, single zone colour, 3px end-dot, 40px max height, 2px padding, devicePixelRatio scaling
5. **Delta badge visual design: Unicode arrows with zone colour** (5/5) -- `\u25B2`/`\u25BC`, |delta| >= 5 threshold, absolute value display, zone colour via element.style
6. **"Building history..." placeholder** (5/5) -- gray italic text at 40px height when history.length < 3

### Claude's Discretion
- Canvas element insertion point: after gauge container, before interpretation text
- Delta badge construction: helper function `createDeltaBadge(metricData)` in InterpretationsModule
- Retina/HiDPI canvas scaling: multiply by devicePixelRatio, scale context, CSS logical size

### Deferred Ideas (OUT OF SCOPE)
- Sparkline hover/tap tooltip
- Multi-zone sparkline colouring (per-segment colours)
- Delta badge animation (scale-in/pulse)
- Configurable delta threshold (use constant, not user-configurable)
- Delta percentage display
- Sparkline fill gradient
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DELT-01 | Direction badge (up/down) with magnitude when |delta| >= 5 | Unicode arrows + `createDeltaBadge()` helper; threshold as named constant |
| DELT-02 | Hero section hawk score delta display | New `div#hero-delta` element; `renderHeroDelta()` function in gauge-init.js |
| DELT-03 | Zone colours via element.style hex (not Tailwind) | `getZoneColor()` already returns hex; apply via `.style.color` |
| DELT-04 | No badge for missing previous_value | Check delta field existence; return null from createDeltaBadge |
| SPRK-01 | Canvas 2D sparkline from history[] array | SparklineModule.draw() with normalization + stroke rendering |
| SPRK-02 | Sparkline colour from getZoneColor() | Pass `getZoneColor(metricData.value)` as color parameter |
| SPRK-03 | "Building history..." when < 3 history points | Placeholder check before SparklineModule.draw() call |
| SPRK-04 | 40px height, full card width, no axes/labels | Canvas height=40, width from offsetWidth, no axis rendering |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Vanilla JS (IIFE) | ES5+ | Module pattern | Existing architecture |
| Tailwind CDN | v3 | Utility classes | Existing, CDN-loaded |
| Plotly.js | 2.35.2 | Gauge charts (8 instances) | Existing, NOT for sparklines |
| Canvas 2D API | Native | Sparkline rendering | Browser-native, no library needed |

### No Additional Libraries
Phase 25 requires zero new dependencies. Canvas 2D is a browser-native API. All colour utilities exist in GaugesModule. All DOM construction patterns exist in InterpretationsModule.

**Why not @fnando/sparkline:** ESM-only, incompatible with IIFE architecture. Hand-rolling Canvas 2D is ~40 lines of code and gives full control.

**Why not Plotly for sparklines:** Page already has 8 Plotly chart instances. Research showed Firefox freezes above 15 instances. Adding 7 more sparklines (one per indicator card) would bring the total to 15+. Canvas 2D has negligible overhead.

## Architecture Patterns

### Existing Module Structure
```
public/js/
  data.js           # DataModule — fetch/cache status.json
  gauges.js          # GaugesModule — Plotly gauge rendering + getZoneColor()
  sparklines.js      # SparklineModule — NEW: Canvas 2D sparkline rendering
  interpretations.js # InterpretationsModule — card/verdict DOM construction
  gauge-init.js      # Orchestrator — fetches data, calls modules in sequence
  chart.js           # Rate history chart
  calculator.js      # Mortgage calculator
  countdown.js       # RBA meeting countdown
  main.js            # App initializer
```

### Script Load Order in index.html
```html
<script src="js/data.js"></script>
<script src="js/gauges.js"></script>
<script src="js/sparklines.js"></script>      <!-- NEW -->
<script src="js/interpretations.js"></script>
<script src="js/gauge-init.js"></script>
```

sparklines.js MUST load after gauges.js (accesses `GaugesModule.getZoneColor()`) and before gauge-init.js (which orchestrates rendering).

### IIFE Module Pattern (Existing Convention)
```javascript
var SparklineModule = (function () {
  'use strict';

  // Private constants and functions
  var DELTA_DISPLAY_THRESHOLD = 5;

  function draw(canvasElement, historyArray, color, options) {
    // Implementation
  }

  return {
    draw: draw
  };
})();
```

### DOM Construction Pattern (Existing Convention)
```javascript
// CORRECT: createElement + textContent + appendChild
var badge = document.createElement('span');
badge.className = 'text-xs font-semibold';
badge.style.color = GaugesModule.getZoneColor(value);
badge.textContent = '\u25B2 ' + Math.abs(delta).toFixed(1);

// FORBIDDEN: innerHTML (ESLint enforces)
// badge.innerHTML = '&#x25B2; 8.3';  // NEVER
```

### Colour Application Pattern (Existing Convention)
```javascript
// CORRECT: element.style with hex from getZoneColor()
element.style.color = GaugesModule.getZoneColor(gaugeValue);

// FORBIDDEN: Tailwind class concatenation
// element.className = 'text-' + colorName;  // NEVER — CDN drops dynamic classes
```

### renderMetricCard Integration Points

Current DOM order in `InterpretationsModule.renderMetricCard()`:
1. Header (label + importance badge)
2. Low confidence badge (conditional)
3. Gauge container (`div#gauge-{id}`)
4. Interpretation text
5. "Why it matters" text
6. Source attribution (conditional)
7. Source date

**Modified DOM order:**
1. Header (label + **delta badge** + importance badge) -- MODIFIED
2. Low confidence badge (conditional)
3. Gauge container (`div#gauge-{id}`)
4. **Sparkline container (`div#sparkline-{id}`)** or **placeholder** -- NEW
5. Interpretation text
6. "Why it matters" text
7. Source attribution (conditional)
8. Source date

### Hero Card Integration Point

Current hero card DOM (from index.html):
```
#hero-card
  #verdict-container
  #hawk-score-display
  #scale-explainer          <-- INSERT hero-delta BEFORE this
  #hero-freshness
  #calculator-jump-link
```

New element `#hero-delta` inserted between `#hawk-score-display` and `#scale-explainer` by gauge-init.js at runtime.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Zone colour lookup | Colour map in sparklines.js | `GaugesModule.getZoneColor(value)` | Already exists, tested, single source of truth |
| Display labels | Label map in new code | `GaugesModule.getDisplayLabel(id)` | Already exists with all 7 indicators |
| Data fetching | New fetch call | `DataModule.fetch()` return value | Already cached in gauge-init.js flow |
| Reduced motion check | New matchMedia call | Shared `reducedMotion` variable in gauge-init.js | Already exists at top of initGauges() |

## Common Pitfalls

### Pitfall 1: Canvas Zero-Width on First Render
**What goes wrong:** Canvas `offsetWidth` is 0 when element is not yet in DOM or parent is hidden
**Why it happens:** Canvas width must be set from `offsetWidth` after the element is appended to a visible parent
**How to avoid:** Append canvas to card DOM first, THEN read offsetWidth, THEN call SparklineModule.draw(). Or use requestAnimationFrame to defer.
**Warning signs:** Sparkline not visible, canvas element has width=0 attribute

### Pitfall 2: Blurry Canvas on Retina Displays
**What goes wrong:** Canvas appears blurry on HiDPI screens (MacBook Retina, modern phones)
**Why it happens:** Canvas pixel buffer doesn't match device pixel ratio
**How to avoid:** Standard pattern:
```javascript
var dpr = window.devicePixelRatio || 1;
canvas.width = logicalWidth * dpr;
canvas.height = logicalHeight * dpr;
canvas.style.width = logicalWidth + 'px';
canvas.style.height = logicalHeight + 'px';
ctx.scale(dpr, dpr);
```
**Warning signs:** Lines appear fuzzy, end-dot appears soft

### Pitfall 3: Tailwind CDN Drops Dynamic Classes
**What goes wrong:** Dynamically constructed Tailwind class strings don't render
**Why it happens:** Tailwind CDN JIT compiler only processes classes it finds in the HTML at compile time
**How to avoid:** Use `element.style` with hex values from `getZoneColor()`. Never concatenate class strings like `'text-' + color`.
**Warning signs:** Element appears but colour is wrong or missing

### Pitfall 4: Flat Sparkline for Identical Values
**What goes wrong:** Division by zero when normalizing identical values (min === max)
**Why it happens:** Normalization formula `(v - min) / (max - min)` divides by zero
**How to avoid:** Check `if (max === min)` and render as horizontal line at vertical center (height / 2)
**Warning signs:** NaN values in canvas drawing, sparkline disappears

### Pitfall 5: History Array Contains Non-Numeric Values
**What goes wrong:** Canvas drawing methods receive NaN, causing invisible or broken lines
**Why it happens:** status.json history may contain null or undefined values
**How to avoid:** Filter history array: `history.filter(function(v) { return typeof v === 'number' && !isNaN(v); })`
**Warning signs:** Sparkline has gaps, broken path, or doesn't render

### Pitfall 6: Resize Handler Doesn't Redraw Sparklines
**What goes wrong:** After window resize, sparklines have wrong width (stretched or clipped)
**Why it happens:** Canvas width is set once at render time; CSS width:100% doesn't resize the canvas buffer
**How to avoid:** Extend existing `setupResizeHandler()` in gauge-init.js to redraw sparklines on resize. Store references to rendered canvases and their data.
**Warning signs:** Sparklines look distorted after browser resize

### Pitfall 7: delta_direction Field Name Collision
**What goes wrong:** Using `metricData.direction` instead of `metricData.delta_direction`
**Why it happens:** business_confidence already has a `direction` field (from engine.py). Phase 24 deliberately named the delta field `delta_direction` to avoid collision.
**How to avoid:** Always use `metricData.delta_direction` for the delta direction. The field name is `delta_direction`, NOT `direction`.
**Warning signs:** business_confidence delta badge shows wrong direction or uses the existing direction field

## Code Examples

### SparklineModule.draw() Implementation Pattern
```javascript
var SparklineModule = (function () {
  'use strict';

  var DEFAULTS = { lineWidth: 1.5, dotRadius: 3, padding: 2 };

  function draw(canvas, history, color, opts) {
    if (!canvas || !canvas.getContext) return false;

    // Filter valid numeric values
    var data = [];
    for (var i = 0; i < history.length; i++) {
      if (typeof history[i] === 'number' && !isNaN(history[i])) {
        data.push(history[i]);
      }
    }
    if (data.length < 3) return false;

    var o = {};
    var k;
    for (k in DEFAULTS) { o[k] = DEFAULTS[k]; }
    if (opts) { for (k in opts) { o[k] = opts[k]; } }

    var dpr = window.devicePixelRatio || 1;
    var logicalWidth = canvas.offsetWidth;
    var logicalHeight = 40;

    canvas.width = logicalWidth * dpr;
    canvas.height = logicalHeight * dpr;
    canvas.style.width = logicalWidth + 'px';
    canvas.style.height = logicalHeight + 'px';

    var ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);

    var min = data[0], max = data[0];
    for (var j = 1; j < data.length; j++) {
      if (data[j] < min) min = data[j];
      if (data[j] > max) max = data[j];
    }

    var pad = o.padding;
    var drawH = logicalHeight - pad * 2;
    var range = max - min;

    function yPos(val) {
      if (range === 0) return logicalHeight / 2;
      return pad + drawH - ((val - min) / range) * drawH;
    }

    var step = (logicalWidth - 1) / (data.length - 1);

    ctx.beginPath();
    ctx.moveTo(0, yPos(data[0]));
    for (var p = 1; p < data.length; p++) {
      ctx.lineTo(p * step, yPos(data[p]));
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = o.lineWidth;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';
    ctx.stroke();

    // End-dot
    var lastX = (data.length - 1) * step;
    var lastY = yPos(data[data.length - 1]);
    ctx.beginPath();
    ctx.arc(lastX, lastY, o.dotRadius, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();

    return true;
  }

  return { draw: draw };
})();
```

### createDeltaBadge() Helper Pattern
```javascript
function createDeltaBadge(metricData) {
  var DELTA_DISPLAY_THRESHOLD = 5;

  // DELT-04: no badge if delta data absent
  if (metricData.delta == null || metricData.delta_direction == null) {
    return null;
  }

  // DELT-01: threshold check
  if (Math.abs(metricData.delta) < DELTA_DISPLAY_THRESHOLD) {
    return null;
  }

  var badge = document.createElement('span');
  badge.className = 'text-xs font-semibold';

  var arrow = metricData.delta_direction === 'up' ? '\u25B2' : '\u25BC';
  badge.textContent = arrow + ' ' + Math.abs(metricData.delta).toFixed(1);

  // DELT-03: zone colour via element.style
  badge.style.color = GaugesModule.getZoneColor(metricData.value);

  // Accessibility
  var direction = metricData.delta_direction === 'up' ? 'increased' : 'decreased';
  badge.setAttribute('aria-label',
    GaugesModule.getDisplayLabel(metricData._metricId)
    + ' gauge ' + direction + ' by '
    + Math.abs(metricData.delta).toFixed(1) + ' points'
  );

  return badge;
}
```

### Hero Delta Rendering Pattern
```javascript
function renderHeroDelta(overall) {
  var existing = document.getElementById('hero-delta');
  if (existing) existing.parentNode.removeChild(existing);

  // No delta data: don't render
  if (overall.hawk_score_delta == null) return;

  var container = document.createElement('div');
  container.id = 'hero-delta';
  container.className = 'text-base text-center mt-2';

  if (overall.hawk_score_delta === 0) {
    container.className += ' text-gray-500';
    container.textContent = 'No change since last update';
  } else {
    var arrow = overall.hawk_score_delta > 0 ? '\u25B2' : '\u25BC';
    var sign = overall.hawk_score_delta > 0 ? '+' : '';

    var arrowSpan = document.createElement('span');
    arrowSpan.style.color = GaugesModule.getZoneColor(overall.hawk_score);
    arrowSpan.textContent = arrow + ' ' + sign
      + overall.hawk_score_delta.toFixed(1);

    var textSpan = document.createElement('span');
    textSpan.className = 'text-gray-400';
    textSpan.textContent = ' since last update';

    container.appendChild(arrowSpan);
    container.appendChild(textSpan);
  }

  // Insert between hawk-score-display and scale-explainer
  var scoreEl = document.getElementById('hawk-score-display');
  var scaleEl = document.getElementById('scale-explainer');
  if (scoreEl && scaleEl && scaleEl.parentNode) {
    scaleEl.parentNode.insertBefore(container, scaleEl);
  }
}
```

## State of the Art

| Aspect | Current State | Phase 25 Approach |
|--------|--------------|-------------------|
| Sparkline libraries | ESM-only (@fnando/sparkline, sparkline-svg) | Hand-rolled Canvas 2D (IIFE-compatible) |
| Canvas 2D API | Stable, well-supported, no breaking changes | Straightforward stroke + arc rendering |
| devicePixelRatio | Standard practice for HiDPI | Scale backing store, CSS logical size |
| IIFE pattern | Project convention, all 8 JS modules use it | New sparklines.js follows same pattern |

## Open Questions

1. **Sparkline resize timing**
   - What we know: Existing resize handler debounces Plotly relayout at 250ms
   - What's unclear: Whether sparkline redraw should use same debounce or separate
   - Recommendation: Extend existing debounced handler -- add sparkline redraw after Plotly relayout in same timeout callback

2. **E2E test data**
   - What we know: Current status.json has no delta fields (no second pipeline run yet)
   - What's unclear: Whether Playwright tests should mock status.json or use a fixture
   - Recommendation: Use test fixture with injected delta fields for reliable E2E testing

## Sources

### Primary (HIGH confidence)
- Codebase analysis: `public/js/gauges.js` -- getZoneColor(), getDisplayLabel(), IIFE pattern
- Codebase analysis: `public/js/interpretations.js` -- renderMetricCard() DOM structure, createElement pattern
- Codebase analysis: `public/js/gauge-init.js` -- initGauges() orchestration, setupResizeHandler()
- Codebase analysis: `public/index.html` -- hero card DOM structure, script load order
- Phase 24 CONTEXT.md -- delta field names: `delta_direction` (not `direction`), `hawk_score_delta`

### Secondary (MEDIUM confidence)
- Canvas 2D API: MDN Web Docs -- devicePixelRatio scaling pattern
- Project memory: CLAUDE.md -- architectural constraints, Plotly limit, no innerHTML rule

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no external dependencies, all browser-native
- Architecture: HIGH -- extends existing patterns with full codebase visibility
- Pitfalls: HIGH -- identified from actual codebase patterns and Phase 24 decisions

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable browser APIs, no moving targets)
