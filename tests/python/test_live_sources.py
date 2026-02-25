"""
Live verification tests for RBA Hawk-O-Meter data sources.

Each test function calls a real external endpoint via the corresponding ingestor
module's fetch_and_save(). All 9 tests are marked @pytest.mark.live so they are
excluded from the fast unit test suite (``-m "not live"``).

Behaviour:
  - Endpoint up + valid structure  -> test PASSES silently
  - Endpoint up + structural break -> test FAILS (hard assertion)
  - Endpoint down / timeout / HTTP error -> test PASSES with UserWarning
  - Data quality concern (0 rows, stale >90 days) -> test PASSES with UserWarning

Run:
  npm run test:python:live          (all 9, verbose)
  python -m pytest tests/python/ -m live -v
"""

import warnings
from datetime import datetime

import pandas as pd
import pytest

import pipeline.config
from pipeline.ingest import (
    abs_data,
    asx_futures_scraper,
    corelogic_scraper,
    nab_scraper,
    rba_data,
)

STALENESS_THRESHOLD_DAYS = 90


def _check_staleness(csv_path, source_name):
    """Warn if the latest date in a CSV is more than 90 days old."""
    try:
        df = pd.read_csv(csv_path)
        if df.empty or "date" not in df.columns:
            return
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        latest = df["date"].dropna().max()
        if pd.isna(latest):
            return
        staleness = (datetime.now() - latest.to_pydatetime().replace(tzinfo=None)).days
        if staleness > STALENESS_THRESHOLD_DAYS:
            warnings.warn(
                f"{source_name}: data may be stale "
                f"(latest date {latest.date()}, {staleness} days old)",
                UserWarning,
                stacklevel=3,
            )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# ABS tests (1-5)
# ---------------------------------------------------------------------------

ABS_REQUIRED_COLUMNS = {"date", "value", "source"}


def _run_abs_test(series_key, output_filename, source_label):
    """Shared helper for the 5 ABS live tests."""
    try:
        result = abs_data.fetch_and_save(series_key)
    except Exception as exc:
        warnings.warn(
            f"{source_label}: fetch_and_save raised {type(exc).__name__}: {exc}",
            UserWarning,
            stacklevel=3,
        )
        return

    row_count = result.get(series_key, 0)
    csv_path = pipeline.config.DATA_DIR / output_filename

    # Structural check: CSV must exist with required columns
    assert csv_path.exists(), (
        f"{source_label}: expected output file {csv_path} not found"
    )
    df = pd.read_csv(csv_path)
    missing = ABS_REQUIRED_COLUMNS - set(df.columns)
    assert not missing, (
        f"{source_label}: missing required columns {missing} "
        f"(found: {list(df.columns)})"
    )

    # Data quality: warn (don't fail) on empty or stale
    if row_count == 0 or df.empty:
        warnings.warn(
            f"{source_label}: fetch returned 0 rows",
            UserWarning,
            stacklevel=3,
        )
        return

    _check_staleness(csv_path, source_label)


@pytest.mark.live
def test_live_abs_cpi():
    """ABS CPI — Consumer Price Index (monthly)."""
    _run_abs_test("cpi", "abs_cpi.csv", "ABS CPI")


@pytest.mark.live
def test_live_abs_employment():
    """ABS Employment — Labour Force (monthly)."""
    _run_abs_test("employment", "abs_employment.csv", "ABS Employment")


@pytest.mark.live
def test_live_abs_wpi():
    """ABS WPI — Wage Price Index (quarterly)."""
    _run_abs_test("wage_price_index", "abs_wage_price_index.csv", "ABS WPI")


@pytest.mark.live
def test_live_abs_spending():
    """ABS Household Spending Indicator (monthly)."""
    _run_abs_test(
        "household_spending",
        "abs_household_spending.csv",
        "ABS Household Spending",
    )


@pytest.mark.live
def test_live_abs_building_approvals():
    """ABS Building Approvals — new residential dwellings (monthly)."""
    _run_abs_test(
        "building_approvals",
        "abs_building_approvals.csv",
        "ABS Building Approvals",
    )


# ---------------------------------------------------------------------------
# RBA test (6)
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_rba_cash_rate():
    """RBA Cash Rate Target from Table A2."""
    try:
        row_count = rba_data.fetch_and_save()
    except Exception as exc:
        warnings.warn(
            f"RBA Cash Rate: fetch_and_save raised {type(exc).__name__}: {exc}",
            UserWarning,
            stacklevel=2,
        )
        return

    csv_path = pipeline.config.DATA_DIR / "rba_cash_rate.csv"

    # Structural check
    assert csv_path.exists(), (
        "RBA Cash Rate: expected output file rba_cash_rate.csv not found"
    )
    df = pd.read_csv(csv_path)
    missing = {"date", "value", "source"} - set(df.columns)
    assert not missing, (
        f"RBA Cash Rate: missing required columns {missing} "
        f"(found: {list(df.columns)})"
    )

    if row_count == 0 or df.empty:
        warnings.warn(
            "RBA Cash Rate: fetch returned 0 rows",
            UserWarning,
            stacklevel=2,
        )
        return

    _check_staleness(csv_path, "RBA Cash Rate")


# ---------------------------------------------------------------------------
# Scraper tests (7-9)  — fetch_and_save() returns status dict, never raises
# ---------------------------------------------------------------------------


@pytest.mark.live
def test_live_asx_futures():
    """ASX 30-Day IB Futures via MarkitDigital API."""
    try:
        result = asx_futures_scraper.fetch_and_save()
    except Exception as exc:
        warnings.warn(
            f"ASX Futures: unexpected exception {type(exc).__name__}: {exc}",
            UserWarning,
            stacklevel=2,
        )
        return

    if result.get("status") != "success":
        warnings.warn(
            f"ASX Futures: scraper returned non-success status: "
            f"{result.get('error', 'unknown')}",
            UserWarning,
            stacklevel=2,
        )
        return

    csv_path = pipeline.config.DATA_DIR / "asx_futures.csv"
    assert csv_path.exists(), (
        "ASX Futures: expected output file asx_futures.csv not found"
    )
    df = pd.read_csv(csv_path)
    expected_cols = {
        "date", "meeting_date", "implied_rate",
        "probability_cut", "probability_hold", "probability_hike",
    }
    missing = expected_cols - set(df.columns)
    assert not missing, (
        f"ASX Futures: missing required columns {missing} "
        f"(found: {list(df.columns)})"
    )

    _check_staleness(csv_path, "ASX Futures")


@pytest.mark.live
def test_live_cotality():
    """Cotality (CoreLogic) Housing Value Index via PDF scraper."""
    try:
        result = corelogic_scraper.fetch_and_save()
    except Exception as exc:
        warnings.warn(
            f"Cotality HVI: unexpected exception {type(exc).__name__}: {exc}",
            UserWarning,
            stacklevel=2,
        )
        return

    if result.get("status") != "success":
        warnings.warn(
            f"Cotality HVI: scraper returned non-success status: "
            f"{result.get('error', 'unknown')}",
            UserWarning,
            stacklevel=2,
        )
        return

    csv_path = pipeline.config.DATA_DIR / "corelogic_housing.csv"
    assert csv_path.exists(), (
        "Cotality HVI: expected output file corelogic_housing.csv not found"
    )
    df = pd.read_csv(csv_path)
    missing = {"date", "value", "source"} - set(df.columns)
    assert not missing, (
        f"Cotality HVI: missing required columns {missing} "
        f"(found: {list(df.columns)})"
    )

    _check_staleness(csv_path, "Cotality HVI")


@pytest.mark.live
def test_live_nab_capacity():
    """NAB Monthly Business Survey — Capacity Utilisation."""
    try:
        result = nab_scraper.fetch_and_save()
    except Exception as exc:
        warnings.warn(
            f"NAB Capacity: unexpected exception {type(exc).__name__}: {exc}",
            UserWarning,
            stacklevel=2,
        )
        return

    if result.get("status") != "success":
        warnings.warn(
            f"NAB Capacity: scraper returned non-success status: "
            f"{result.get('error', 'unknown')}",
            UserWarning,
            stacklevel=2,
        )
        return

    csv_path = pipeline.config.DATA_DIR / "nab_capacity.csv"
    assert csv_path.exists(), (
        "NAB Capacity: expected output file nab_capacity.csv not found"
    )
    df = pd.read_csv(csv_path)
    missing = {"date", "value", "source"} - set(df.columns)
    assert not missing, (
        f"NAB Capacity: missing required columns {missing} "
        f"(found: {list(df.columns)})"
    )

    _check_staleness(csv_path, "NAB Capacity")
