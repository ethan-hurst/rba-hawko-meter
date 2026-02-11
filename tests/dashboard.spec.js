// @ts-check
const { test, expect } = require('@playwright/test');
const fs = require('fs');
const path = require('path');

// Read hawk score from status.json so tests aren't coupled to specific pipeline output
const statusJson = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'public', 'data', 'status.json'), 'utf8'));
const hawkScore = Math.round(statusJson.overall.hawk_score);

// Derive the expected stance label from the score (mirrors gauges.js ZONE_COLORS logic)
function getExpectedStanceLabel(score) {
  if (score < 20) return 'RATES LIKELY FALLING';
  if (score < 40) return 'LEANING TOWARDS CUTS';
  if (score < 60) return 'HOLDING STEADY';
  if (score < 80) return 'LEANING TOWARDS RISES';
  return 'RATES LIKELY RISING';
}
const expectedStance = getExpectedStanceLabel(hawkScore);

test.describe('Phase 4 — Hawk-O-Meter Gauges', () => {

  test('1. Hero gauge renders with hawk score and stance label', async ({ page }) => {
    await page.goto('/');

    // Wait for Plotly to render inside the hero gauge container
    const heroPlot = page.locator('#hero-gauge-plot');
    await expect(heroPlot).toBeVisible();

    // Plotly renders SVG elements — wait for the gauge to appear
    const svg = heroPlot.locator('svg.main-svg');
    await expect(svg.first()).toBeVisible({ timeout: 15000 });

    // Hawk score should be visible as "<score>/100" (derived from status.json)
    await expect(heroPlot).toContainText(`${hawkScore}/100`);

    // Stance label should match the zone for the current score
    await expect(heroPlot).toContainText(expectedStance);
  });

  test('2. Individual metric cards render with interpretations', async ({ page }) => {
    await page.goto('/');

    const grid = page.locator('#metric-gauges-grid');
    await expect(grid).toBeVisible();

    // Wait for metric cards to render (replaces the "Loading..." placeholder)
    // 5 active cards (bg-finance-gray) + 2 placeholder cards (bg-finance-gray/50) = 7 total
    const allCards = grid.locator('[class*="bg-finance-gray"]');
    await expect(allCards).toHaveCount(7, { timeout: 15000 });

    // Each card should have interpretation text with real numbers
    const cards = allCards;

    // Inflation card: should show "Prices up" with a percentage
    await expect(cards.nth(0)).toContainText('Prices up');

    // Wages card: should show "Wages up" with a percentage
    await expect(cards.nth(1)).toContainText('Wages up');

    // Employment card (index 2): job market text
    await expect(cards.nth(2)).toContainText('job market');

    // Spending card (index 3): consumer spending text
    await expect(cards.nth(3)).toContainText('Consumer spending');

    // Building approvals card (index 4): interpretation text present
    await expect(cards.nth(4)).toContainText('Building Approvals');
  });

  test('3. Responsive layout — single column at mobile, 3 columns at desktop', async ({ page }) => {
    // Mobile viewport (375px)
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/');

    const grid = page.locator('#metric-gauges-grid');
    // 5 active + 2 placeholder = 7 total
    await expect(grid.locator('[class*="bg-finance-gray"]')).toHaveCount(7, { timeout: 15000 });

    // At 375px the grid should be single-column
    let columns = await grid.evaluate(el => {
      return window.getComputedStyle(el).getPropertyValue('grid-template-columns');
    });
    // Single column: one value (no space-separated multiple values)
    expect(columns.split(' ').length).toBe(1);

    // Desktop viewport (1024px)
    await page.setViewportSize({ width: 1024, height: 768 });
    // Allow Tailwind responsive classes to re-evaluate
    await page.waitForTimeout(500);

    columns = await grid.evaluate(el => {
      return window.getComputedStyle(el).getPropertyValue('grid-template-columns');
    });
    // 3 columns at lg breakpoint
    expect(columns.split(' ').length).toBe(3);
  });

  test('4. Error state when status.json unavailable', async ({ page }) => {
    // Intercept status.json fetch and return 404
    await page.route('**/data/status.json', route => {
      route.fulfill({ status: 404, body: 'Not Found' });
    });

    await page.goto('/');

    // The error message should appear in the hero gauge area
    const heroPlot = page.locator('#hero-gauge-plot');
    await expect(heroPlot).toContainText('Unable to load economic data', { timeout: 15000 });
  });

  test('5. Staleness indicator — wages card has amber border', async ({ page }) => {
    await page.goto('/');

    const grid = page.locator('#metric-gauges-grid');
    // 5 active + 2 placeholder = 7 total
    await expect(grid.locator('[class*="bg-finance-gray"]')).toHaveCount(7, { timeout: 15000 });

    // Wages is the second card (index 1) — staleness_days=220 > 90 threshold
    const wagesCard = grid.locator('[class*="bg-finance-gray"]').nth(1);

    // The card should have the amber border class applied by renderMetricCard
    const classAttr = await wagesCard.getAttribute('class');
    expect(classAttr).toContain('border-amber-500');

    // It should also show the "months old" text
    await expect(wagesCard).toContainText('months old');
  });

});

test.describe('Phase 7 — ASX Futures Section', () => {

  test('6. ASX futures section renders with probability table when data available', async ({ page }) => {
    // Intercept status.json and inject asx_futures data
    await page.route('**/data/status.json', async route => {
      const response = await route.fetch();
      const json = await response.json();
      // Inject test asx_futures data
      json.asx_futures = {
        current_rate: 4.35,
        implied_rate: 4.10,
        next_meeting: '2026-02-18',
        direction: 'cut',
        data_date: '2026-02-07',
        staleness_days: 0,
        probabilities: { cut: 85, hold: 15, hike: 0 }
      };
      await route.fulfill({ json });
    });

    await page.goto('/');

    // The ASX futures container should be visible
    const asxContainer = page.locator('#asx-futures-container');
    await expect(asxContainer).toBeVisible({ timeout: 15000 });

    // Should show "What Markets Expect" heading
    await expect(asxContainer).toContainText('What Markets Expect');

    // Should show the probability table with outcomes
    await expect(asxContainer).toContainText('Rate Cut');
    await expect(asxContainer).toContainText('85.0%');
    await expect(asxContainer).toContainText('Hold');
    await expect(asxContainer).toContainText('15.0%');
  });

  test('7. ASX futures section hidden when data unavailable', async ({ page }) => {
    // Intercept status.json and ensure asx_futures is null
    await page.route('**/data/status.json', async route => {
      const response = await route.fetch();
      const json = await response.json();
      // Ensure no asx_futures data
      json.asx_futures = null;
      await route.fulfill({ json });
    });

    await page.goto('/');

    // Wait for gauges to render (proves page loaded)
    const heroPlot = page.locator('#hero-gauge-plot');
    await expect(heroPlot).toBeVisible({ timeout: 15000 });

    // ASX futures container should be hidden (display: none)
    const asxContainer = page.locator('#asx-futures-container');
    await expect(asxContainer).toBeHidden();
  });

});
