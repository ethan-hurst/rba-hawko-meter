"""
Ratio normalization module.

Converts raw CSV data to normalized ratios (primarily YoY % change).
Ensures no nominal currency values pass through to the gauge engine.
"""

import pandas as pd
import numpy as np
from pathlib import Path

from pipeline.config import DATA_DIR


def load_indicator_csv(csv_path):
    """
    Read a CSV file with date/value columns, parse dates, sort by date.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        DataFrame with parsed date and numeric value columns, or None if file missing.
    """
    path = Path(csv_path)
    if not path.exists():
        print(f"  CSV not found: {path}")
        return None

    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.sort_values('date').reset_index(drop=True)
    return df


def compute_yoy_pct_change(df, periods):
    """
    Compute year-over-year percentage change.

    Formula: ((value_t / value_{t-periods}) - 1) * 100

    Args:
        df: DataFrame with 'date' and 'value' columns.
        periods: Number of periods for YoY (4 for quarterly, 12 for monthly).

    Returns:
        DataFrame with 'date' and 'value' (now YoY % change), leading NaN rows dropped.
    """
    result = df.copy()
    result['value'] = (result['value'] / result['value'].shift(periods) - 1) * 100
    result = result.dropna(subset=['value']).reset_index(drop=True)
    return result


def resample_to_quarterly(df):
    """
    Resample monthly data to quarterly using end-of-quarter last value.

    Args:
        df: DataFrame with 'date' and 'value' columns (monthly frequency).

    Returns:
        DataFrame resampled to quarterly frequency.
    """
    df = df.set_index('date')
    quarterly = df[['value']].resample('QE').last()
    quarterly = quarterly.dropna(subset=['value']).reset_index()
    return quarterly


def filter_valid_data(df):
    """
    Drop NaN, inf, and zero-value rows.

    Args:
        df: DataFrame with 'value' column.

    Returns:
        DataFrame with invalid rows removed.
    """
    df = df.copy()
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=['value'])
    df = df[df['value'] != 0]
    return df.reset_index(drop=True)


def normalize_indicator(name, config):
    """
    Main entry point: load CSV, normalize, and return quarterly DataFrame.

    Args:
        name: Indicator name (e.g. 'inflation', 'wages').
        config: Dict with csv_file, normalize, frequency, yoy_periods keys.

    Returns:
        DataFrame with [date, value] columns (quarterly, YoY % change),
        or None if data unavailable.
    """
    csv_file = config.get('csv_file')
    if csv_file is None:
        return None

    csv_path = DATA_DIR / csv_file
    df = load_indicator_csv(csv_path)
    if df is None:
        return None

    # Filter out zeros and invalid values before normalization
    df = filter_valid_data(df)

    if len(df) == 0:
        print(f"  {name}: no valid data after filtering")
        return None

    normalize_type = config.get('normalize', 'yoy_pct_change')

    if normalize_type == 'yoy_pct_change':
        periods = config.get('yoy_periods', 4)
        df = compute_yoy_pct_change(df, periods)
    elif normalize_type == 'direct':
        pass  # Use values as-is (already a ratio/index)

    if len(df) == 0:
        print(f"  {name}: no data after normalization")
        return None

    # Resample monthly data to quarterly
    frequency = config.get('frequency', 'quarterly')
    if frequency == 'monthly':
        df = resample_to_quarterly(df)

    if len(df) == 0:
        print(f"  {name}: no data after resampling")
        return None

    # Filter any remaining invalid values after normalization
    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=['value'])

    # Return only date and value columns
    return df[['date', 'value']].reset_index(drop=True)
