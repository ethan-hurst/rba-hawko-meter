# Project Design: The RBA Hawk-O-Meter
**Status:** Draft | **Version:** 1.0

## 1. Executive Summary
The **RBA Hawk-O-Meter** is an automated, unbiased economic dashboard designed to visualize the probability of Australian interest rate hikes. Unlike media headlines which rely on nominal figures (prone to "money illusion"), this system ingests raw economic data, normalizes it for inflation and population growth, and calculates a statistical "Z-Score" to display how current conditions compare to the 10-year average.

**Goal:** Provide a "Traffic Light" system for mortgage holders to decide between Fixed vs. Variable rates based on data, not opinion.

---

## 2. Solution Architecture
The system follows a **Serverless "Silent Automation" Pattern** using GitHub Actions as the cron scheduler and compute engine.

### Data Flow
1.  **Ingestion:** Python script fetches data from ABS, RBA, and scraped sources.
2.  **Processing:** Data is normalized (ratios over raw numbers) and Z-scored.
3.  **Storage:** Processed snapshot saved as `status.json`.
4.  **Presentation:** GitHub Pages hosts a static HTML site consuming the JSON.

---

## 3. The "Unbiased" Data Strategy
To prevent inflation bias (where 2026 dollars look "scarier" than 2016 dollars), strictly **NO nominal currency values** are used in the gauges. All inputs are converted to **Ratios** or **Per Capita** metrics before analysis.

### Core Metrics & Normalization Rules

| Gauge | Data Source | Raw Metric | **Normalization Formula** (The "Real" Metric) |
| :--- | :--- | :--- | :--- |
| **Housing Heat** | CoreLogic / ABS | Median Dwelling Price | `Median Price / Average Weekly Earnings` (Price-to-Income Ratio) |
| **Job Market** | ANZ / ABS | Total Job Advertisements | `(Job Ads / Working Age Population) * 1000` |
| **Spending** | ABS Retail Trade | Total Retail Turnover ($) | `Turnover / (CPI Index / Base CPI)` (Real Volume) |
| **Capacity** | NAB Survey | Capacity Utilisation % | *None needed (Already a ratio)* |
| **Inflation** | Melb Institute | Monthly Inflation Gauge | *None needed (Already % change)* |

---

## 4. The Algorithm: Z-Score Gauge Logic
The dashboard answers one question: *"Is this normal?"*
We use Standard Deviations (Z-Scores) over a 10-year lookback window.

**Formula:**
$$Z = \frac{x - \mu}{\sigma}$$
*Where $x$ is the current value, $\mu$ is the 10-year mean, and $\sigma$ is the standard deviation.*

**The "Traffic Light" Mapping:**

| Z-Score | Gauge Value (0-100) | Visual Zone | Interpretation |
| :--- | :--- | :--- | :--- |
| **< -1.5** | 0 - 20 | **Blue (Cold)** | Recessionary. Rates likely to cut. |
| **-0.5 to +0.5** | 40 - 60 | **Grey (Neutral)** | "Goldilocks" Economy. Rates hold. |
| **> +1.5** | 80 - 100 | **Red (Hot)** | Overheating. High risk of RBA hike. |

---

## 5. Technical Stack

### Backend (The "Engine")
* **Language:** Python 3.11+
* **Key Libraries:**
    * `pandas` (Data manipulation)
    * `readabs` (Official wrapper for ABS/RBA spreadsheets)
    * `beautifulsoup4` (Scraping CoreLogic/NAB)
    * `numpy` (Statistical calculations)
* **Infrastructure:** GitHub Actions (Scheduled workflow: `cron: '0 0 * * 1'` for weekly runs).

### Storage
* **Database:** Flat file JSON (`data/history.csv` for time-series, `public/status.json` for live dashboard).
* **Persistence:** The GitHub Action commits the updated CSV/JSON back to the repo after every run.

### Frontend (The "Dashboard")
* **Hosting:** GitHub Pages.
* **Framework:** Vanilla HTML/JS (No build step required).
* **Visualization:** `Plotly.js` (Best-in-class support for "Speedometer" charts).
* **CSS:** Tailwind (via CDN for rapid styling).

---

## 6. Data Pipeline Specification

### Step 1: Ingestion (`ingest.py`)
* **Task:** Download latest spreadsheets.
* **Output:** Append new rows to `raw_history.csv`.
* **Fail Safe:** If scraping fails (e.g., website change), use previous week's data and log a warning.

### Step 2: Processing (`process.py`)
* **Task:**
    1.  Load `raw_history.csv`.
    2.  Apply **Normalization Formulas** (Section 3).
    3.  Calculate **Rolling Mean (10y)** and **Rolling StdDev (10y)**.
    4.  Compute current **Z-Scores**.
    5.  Map Z-Scores to **0-100 Scale**.
* **Output:** `public/status.json`

```json
{
  "last_updated": "2026-02-04",
  "overall_hawk_score": 78,
  "verdict": "HAWKISH - Fix Rates Considered",
  "gauges": [
    {
      "id": "housing",
      "label": "Housing Pressure",
      "value": 85,
      "context": "Prices are rising faster than wages."
    }
  ]
}
