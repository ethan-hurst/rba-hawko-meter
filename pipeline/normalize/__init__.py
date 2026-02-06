"""
Normalization engine for RBA Hawk-O-Meter.

Transforms raw economic CSV data into comparable 0-100 gauge values:
  1. ratios.py  -- Raw values to YoY percentage change
  2. zscore.py  -- Ratios to robust Z-scores (median/MAD, 10-year rolling)
  3. gauge.py   -- Z-scores to 0-100 gauge values ([-3,+3] linear clamp)
  4. engine.py  -- Orchestrator: reads all CSVs, computes gauges, writes status.json
"""
