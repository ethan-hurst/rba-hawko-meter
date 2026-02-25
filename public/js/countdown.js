/**
 * CountdownModule - Live countdown timer to next RBA Board meeting.
 * Handles meeting-day detection, AEST timezone display, and interval cleanup.
 * Uses safe DOM methods (createElement/textContent) throughout.
 */
var CountdownModule = (function () {
  'use strict';

  var intervalId = null;

  /**
   * Check if a date is today in Australia/Sydney timezone.
   * @param {Date} targetDate
   * @returns {boolean}
   */
  function isTodaySydney(targetDate) {
    var formatter = new Intl.DateTimeFormat('en-AU', {
      timeZone: 'Australia/Sydney',
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
    var nowParts = formatter.format(new Date());
    var targetParts = formatter.format(targetDate);
    return nowParts === targetParts;
  }

  /**
   * Calculate time remaining until target date.
   * @param {Date} targetDate
   * @returns {{days: number, hours: number,
   *   minutes: number, seconds: number,
   *   isPast: boolean, isToday: boolean}}
   */
  function calculateTimeRemaining(targetDate) {
    var now = new Date();
    var diff = targetDate.getTime() - now.getTime();

    var totalSeconds = Math.floor(Math.abs(diff) / 1000);
    var days = Math.floor(totalSeconds / 86400);
    var hours = Math.floor((totalSeconds % 86400) / 3600);
    var minutes = Math.floor((totalSeconds % 3600) / 60);
    var seconds = totalSeconds % 60;

    return {
      days: days,
      hours: hours,
      minutes: minutes,
      seconds: seconds,
      isPast: diff <= 0,
      isToday: isTodaySydney(targetDate)
    };
  }

  /**
   * Create a time unit display element (number + label).
   * @param {number} value
   * @param {string} label
   * @returns {HTMLElement}
   */
  function createTimeUnit(value, label) {
    var unitDiv = document.createElement('div');
    unitDiv.className = 'text-center';

    var numberEl = document.createElement('span');
    numberEl.className = 'text-2xl sm:text-3xl font-bold text-white tabular-nums';
    numberEl.textContent = String(value).padStart(2, '0');

    var labelEl = document.createElement('span');
    labelEl.className = 'block text-xs text-gray-500 uppercase tracking-widest mt-1';
    labelEl.textContent = label;

    unitDiv.appendChild(numberEl);
    unitDiv.appendChild(labelEl);
    return unitDiv;
  }

  /**
   * Create a colon separator between time units.
   * @returns {HTMLElement}
   */
  function createSeparator() {
    var sep = document.createElement('span');
    sep.className = 'text-2xl sm:text-3xl font-bold text-gray-600 self-start';
    sep.textContent = ':';
    return sep;
  }

  /**
   * Update the countdown display using safe DOM methods.
   * @param {HTMLElement} containerEl
   * @param {Object} time - Time remaining object
   * @param {Object} meetingData
   */
  function updateDisplay(containerEl, time, meetingData) {
    while (containerEl.firstChild) {
      containerEl.removeChild(containerEl.firstChild);
    }

    if (time.isToday) {
      // Meeting day banner
      var bannerDiv = document.createElement('div');
      bannerDiv.className =
        'bg-gauge-amber/10 border '
        + 'border-gauge-amber/30 rounded-lg '
        + 'px-6 py-4 text-center';

      var bannerText = document.createElement('p');
      bannerText.className = 'text-gauge-amber font-bold text-lg';
      bannerText.textContent =
        'RBA Board meeting TODAY \u2014 '
        + 'decision expected 2:30pm AEST';

      bannerDiv.appendChild(bannerText);
      containerEl.appendChild(bannerDiv);
      return;
    }

    if (time.isPast) {
      // Meeting has passed
      var passedDiv = document.createElement('div');
      passedDiv.className = 'text-center';

      var passedText = document.createElement('p');
      passedText.className = 'text-gray-400 text-sm';
      passedText.textContent = 'Next RBA Board meeting date will be updated shortly.';

      passedDiv.appendChild(passedText);
      containerEl.appendChild(passedDiv);
      return;
    }

    // Active countdown
    var wrapper = document.createElement('div');
    wrapper.className = 'text-center';

    var heading = document.createElement('p');
    heading.className = 'text-xs text-gray-500 uppercase tracking-widest mb-1';
    heading.textContent = 'Next RBA Board Meeting';

    var dateDisplay = document.createElement('p');
    dateDisplay.className = 'text-sm text-gray-400 mb-4';
    dateDisplay.textContent =
      meetingData.next_meeting.display_date
      + ', '
      + meetingData.next_meeting.display_time;

    var timerDiv = document.createElement('div');
    timerDiv.className = 'flex items-center justify-center gap-3 sm:gap-4';

    timerDiv.appendChild(createTimeUnit(time.days, 'Days'));
    timerDiv.appendChild(createSeparator());
    timerDiv.appendChild(createTimeUnit(time.hours, 'Hours'));
    timerDiv.appendChild(createSeparator());
    timerDiv.appendChild(createTimeUnit(time.minutes, 'Min'));
    timerDiv.appendChild(createSeparator());
    timerDiv.appendChild(createTimeUnit(time.seconds, 'Sec'));

    wrapper.appendChild(heading);
    wrapper.appendChild(dateDisplay);
    wrapper.appendChild(timerDiv);
    containerEl.appendChild(wrapper);
  }

  /**
   * Start the live countdown.
   * @param {HTMLElement} containerEl - Container element for countdown display
   * @param {Object} meetingData - Meeting data from meetings.json
   */
  function start(containerEl, meetingData) {
    // Clear any existing interval to prevent memory leaks
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }

    var targetDate = new Date(meetingData.next_meeting.date);

    // Immediate first render
    var time = calculateTimeRemaining(targetDate);
    updateDisplay(containerEl, time, meetingData);

    // Start ticking
    intervalId = setInterval(function () {
      var t = calculateTimeRemaining(targetDate);
      updateDisplay(containerEl, t, meetingData);

      if (t.isPast && !t.isToday) {
        clearInterval(intervalId);
        intervalId = null;
      }
    }, 1000);
  }

  /**
   * Stop the countdown and clean up.
   */
  function stop() {
    if (intervalId) {
      clearInterval(intervalId);
      intervalId = null;
    }
  }

  // Clean up on page unload
  window.addEventListener('beforeunload', stop);

  return {
    start: start,
    stop: stop
  };
})();
