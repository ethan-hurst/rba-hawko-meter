"""
Generate frontend-consumable JSON files from pipeline CSV data.

Transforms the pipeline's CSV output into JSON files for the static dashboard:
- public/data/rates.json: RBA cash rate history with rate change annotations
- public/data/meetings.json: RBA Board meeting schedule with next meeting date
"""

import csv
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"

SYDNEY_TZ = ZoneInfo("Australia/Sydney")


def generate_rates_json():
    """Transform data/rba_cash_rate.csv into public/data/rates.json."""
    csv_path = DATA_DIR / "rba_cash_rate.csv"

    if not csv_path.exists():
        print(f"WARNING: {csv_path} not found. Skipping rates.json generation.")
        print("  Run the pipeline first, or rates.json will not be available.")
        return None

    rows = []
    with open(csv_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({
                "date": row["date"],
                "value": float(row["value"]),
                "source": row["source"],
            })

    # Sort by date ascending
    rows.sort(key=lambda r: r["date"])

    if not rows:
        print("WARNING: rba_cash_rate.csv is empty. Skipping rates.json.")
        return None

    # Build history arrays
    dates = [r["date"] for r in rows]
    rates = [round(r["value"], 2) for r in rows]

    # Detect rate changes
    rate_changes = []
    for i in range(1, len(rows)):
        prev_rate = round(rows[i - 1]["value"], 2)
        curr_rate = round(rows[i]["value"], 2)
        if prev_rate != curr_rate:
            change = round(curr_rate - prev_rate, 2)
            rate_changes.append({
                "date": rows[i]["date"],
                "from": prev_rate,
                "to": curr_rate,
                "direction": "up" if change > 0 else "down",
                "amount": round(abs(change), 2),
            })

    current_rate = rates[-1]
    last_updated = dates[-1]

    result = {
        "last_updated": last_updated,
        "current_rate": current_rate,
        "source": "RBA",
        "history": {
            "dates": dates,
            "rates": rates,
        },
        "rate_changes": rate_changes,
    }

    output_path = PUBLIC_DATA_DIR / "rates.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Created {output_path}")
    print(f"  Current rate: {current_rate}%")
    print(f"  Data points: {len(dates)}")
    print(f"  Rate changes: {len(rate_changes)}")

    return result


def get_first_tuesday(year, month):
    """Return the first Tuesday of the given month/year."""
    d = date(year, month, 1)
    # Tuesday is weekday 1
    days_until_tuesday = (1 - d.weekday()) % 7
    return d + timedelta(days=days_until_tuesday)


def generate_meetings_json():
    """Generate RBA Board meeting schedule as public/data/meetings.json."""
    today = date.today()
    current_year = today.year
    next_year = current_year + 1

    # RBA Board meets first Tuesday of each month, except January
    meeting_months = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

    all_meetings = []
    for year in [current_year, next_year]:
        for month in meeting_months:
            meeting_date = get_first_tuesday(year, month)

            # Create timezone-aware datetime at 14:30 Sydney time
            meeting_dt = datetime(
                meeting_date.year, meeting_date.month, meeting_date.day,
                14, 30, 0,
                tzinfo=SYDNEY_TZ,
            )

            # Format the ISO string with correct UTC offset
            iso_str = meeting_dt.isoformat()

            # Determine AEST vs AEDT for display
            utc_offset = meeting_dt.utcoffset()
            if utc_offset and utc_offset.total_seconds() == 11 * 3600:
                tz_label = "AEDT"
            else:
                tz_label = "AEST"

            all_meetings.append({
                "date": iso_str,
                "display_date": meeting_dt.strftime("%-d %B %Y"),
                "display_time": f"2:30pm {tz_label}",
            })

    # Find the next upcoming meeting
    now_sydney = datetime.now(SYDNEY_TZ)
    next_meeting = None
    for m in all_meetings:
        meeting_dt = datetime.fromisoformat(m["date"])
        if meeting_dt > now_sydney:
            next_meeting = m
            break

    if next_meeting is None:
        # Fallback: use the last meeting if all are in the past
        next_meeting = all_meetings[-1]

    # Separate meetings by year
    meetings_current_year = [
        m for m in all_meetings
        if datetime.fromisoformat(m["date"]).year == current_year
    ]
    meetings_next_year = [
        m for m in all_meetings
        if datetime.fromisoformat(m["date"]).year == next_year
    ]

    result = {
        "next_meeting": next_meeting,
        f"meetings_{current_year}": meetings_current_year,
        f"meetings_{next_year}": meetings_next_year,
    }

    output_path = PUBLIC_DATA_DIR / "meetings.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Created {output_path}")
    print(f"  Next meeting: {next_meeting['display_date']}")

    return result


def main():
    """Generate all frontend data files."""
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating frontend data files...")
    print()

    generate_rates_json()
    print()
    generate_meetings_json()

    print()
    print("Done.")


if __name__ == "__main__":
    main()
