"""
RBA Hawk-O-Meter — Live Verification Summary.

Reads public/data/status.json (produced by pipeline/main.py) and prints an
ASCII table showing the status of all 7 indicators plus the overall hawk_score.

Exit codes:
  0  All 7 indicator keys present, hawk_score in [0, 100] (warnings OK)
  1  Missing indicator key(s), hawk_score out of range, or status.json missing

Usage:
  python scripts/verify_summary.py          (standalone)
  npm run verify                            (pipeline + summary)
"""

import json
import sys
from datetime import datetime
from pathlib import Path

STATUS_PATH = Path("public/data/status.json")

EXPECTED_GAUGES = [
    "inflation",
    "employment",
    "wages",
    "spending",
    "building_approvals",
    "housing",
    "business_confidence",
]

INDICATOR_LABELS = {
    "inflation": "ABS CPI",
    "employment": "ABS Employment",
    "wages": "ABS WPI",
    "spending": "ABS Household Spending",
    "building_approvals": "ABS Building Approvals",
    "housing": "Cotality HVI",
    "business_confidence": "NAB Capacity",
}

STALENESS_WARNING_DAYS = 90


def _format_date(date_str):
    """Format a date string as 'Mon YYYY'. Returns '—' on failure."""
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%b %Y")
    except (ValueError, TypeError, IndexError):
        return "\u2014"


def main():
    if not STATUS_PATH.exists():
        print(f"ERROR: {STATUS_PATH} not found. Run the pipeline first.")
        sys.exit(1)

    with open(STATUS_PATH) as f:
        data = json.load(f)

    gauges = data.get("gauges", {})
    overall = data.get("overall", {})
    hawk_score = overall.get("hawk_score")

    # ------------------------------------------------------------------
    # Build per-indicator rows
    # ------------------------------------------------------------------
    rows = []
    fail_count = 0
    warn_count = 0

    for key in EXPECTED_GAUGES:
        label = INDICATOR_LABELS[key]
        if key not in gauges:
            rows.append((label, "FAIL", "\u2014"))
            fail_count += 1
            continue

        gauge = gauges[key]
        staleness = gauge.get("staleness_days", 0)
        date_str = _format_date(gauge.get("data_date", ""))

        if staleness > STALENESS_WARNING_DAYS:
            status = "WARN"
            warn_count += 1
        else:
            status = "PASS"

        rows.append((label, status, date_str))

    # ------------------------------------------------------------------
    # hawk_score validation
    # ------------------------------------------------------------------
    score_ok = (
        hawk_score is not None
        and isinstance(hawk_score, (int, float))
        and 0 <= hawk_score <= 100
    )
    if not score_ok:
        fail_count += 1

    # ------------------------------------------------------------------
    # Print table
    # ------------------------------------------------------------------
    width = 48
    line = "\u2500" * width

    print(line)
    print("  RBA Hawk-O-Meter \u2014 Live Verification")
    print(line)
    print(f" {'Indicator':<23} {'Status':<9}{'Latest'}")
    print(line)

    for label, status, date_str in rows:
        print(f" {label:<23} {status:<9}{date_str}")

    print(line)

    if score_ok:
        print(f" Hawk Score: {int(hawk_score)} / 100")
    else:
        print(f" Hawk Score: INVALID ({hawk_score!r})")

    if fail_count > 0:
        result_label = f"FAIL ({fail_count} failure(s))"
    elif warn_count > 0:
        result_label = f"PASS ({warn_count} warning(s))"
    else:
        result_label = "PASS"

    print(f" Result: {result_label}")
    print(line)

    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
