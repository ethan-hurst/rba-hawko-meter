/**
 * Gauge initialization orchestrator.
 * Fetches status.json and renders hero gauge, ASX table, verdict, and metric gauges.
 * Uses DataModule for fetch/cache/error, GaugesModule for rendering, InterpretationsModule for text.
 */
(function () {
  'use strict';

  var METRIC_ORDER = [
    'inflation', 'wages', 'employment', 'housing',
    'spending', 'building_approvals', 'business_confidence'
  ];

  var resizeTimer = null;
  var renderedMetricIds = [];

  /**
   * Render individual metric gauge cards into the grid.
   * @param {Object} gaugesData - data.gauges from status.json
   */
  function renderMetricGauges(gaugesData) {
    var container = document.getElementById('metric-gauges-grid');
    if (!container) return;
    container.textContent = '';

    if (!gaugesData || typeof gaugesData !== 'object') {
      var msg = document.createElement('p');
      msg.className = 'col-span-full text-center text-gray-500 py-8';
      msg.textContent = 'No metric data available';
      container.appendChild(msg);
      return;
    }

    // Build ordered list: METRIC_ORDER entries present in gaugesData, then extras
    var orderedIds = [];
    METRIC_ORDER.forEach(function (id) {
      if (gaugesData[id]) orderedIds.push(id);
    });
    Object.keys(gaugesData).forEach(function (id) {
      if (orderedIds.indexOf(id) === -1 && gaugesData[id]) {
        orderedIds.push(id);
      }
    });

    if (orderedIds.length === 0) {
      var noData = document.createElement('p');
      noData.className = 'col-span-full text-center text-gray-500 py-8';
      noData.textContent = 'No metric data available';
      container.appendChild(noData);
      return;
    }

    renderedMetricIds = [];

    orderedIds.forEach(function (metricId) {
      var metricData = gaugesData[metricId];
      if (!metricData) return;

      // Attach metricId for display label lookup inside createBulletGauge
      metricData._metricId = metricId;

      InterpretationsModule.renderMetricCard(
        'metric-gauges-grid', metricId, metricData, metricData.weight
      );

      renderedMetricIds.push(metricId);

      // Staggered rendering for bullet gauges
      requestAnimationFrame(function () {
        GaugesModule.createBulletGauge('gauge-' + metricId, metricData);
      });
    });
  }

  /**
   * Main initialization: fetch status.json and render all gauges.
   */
  function initGauges() {
    DataModule.showLoading('hero-gauge-plot', 'Loading Hawk Score...');

    DataModule.fetch('data/status.json')
      .then(function (data) {
        // Render hero gauge
        GaugesModule.createHeroGauge('hero-gauge-plot', data.overall.hawk_score);

        // Render verdict
        InterpretationsModule.renderVerdict('verdict-container', data.overall);

        // Render ASX table (currently missing from data, will show unavailable)
        InterpretationsModule.renderASXTable('asx-futures-container', data.asx_futures || null);

        // Render data freshness
        InterpretationsModule.renderStalenessWarning('data-freshness', data.generated_at);

        // Render individual metric gauges
        renderMetricGauges(data.gauges);
      })
      .catch(function (err) {
        console.error('Gauge initialization failed:', err);
        DataModule.showError('hero-gauge-plot', 'Unable to load economic data. Please refresh the page.');
      });
  }

  /**
   * Debounced resize handler for all Plotly gauges.
   */
  function setupResizeHandler() {
    window.addEventListener('resize', function () {
      if (resizeTimer) clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function () {
        var heroEl = document.getElementById('hero-gauge-plot');
        if (heroEl && heroEl.data) {
          Plotly.relayout('hero-gauge-plot', { autosize: true });
        }
        renderedMetricIds.forEach(function (id) {
          var el = document.getElementById('gauge-' + id);
          if (el && el.data) {
            Plotly.relayout(el, { autosize: true });
          }
        });
      }, 250);
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initGauges();
      setupResizeHandler();
    });
  } else {
    initGauges();
    setupResizeHandler();
  }
})();
