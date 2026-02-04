"""
ASX RBA Rate Tracker futures scraper.
CRITICAL source - provides daily market expectations for RBA rate decisions.
"""

import json
import logging
import re
import traceback
from datetime import datetime
from typing import Dict, Union

import pandas as pd
from bs4 import BeautifulSoup

from pipeline.config import DATA_DIR, BROWSER_USER_AGENT, DEFAULT_TIMEOUT
from pipeline.utils.csv_handler import append_to_csv
from pipeline.utils.http_client import create_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scrape_asx_futures() -> pd.DataFrame:
    """
    Scrape ASX RBA Rate Tracker futures data for market rate expectations.

    Returns:
        DataFrame with columns: [scrape_date, meeting_date, implied_rate,
                                 probability_hold, probability_cut, probability_hike, source]

    Raises:
        ValueError: If page structure doesn't match expectations
        requests.RequestException: If HTTP request fails
    """
    session = create_session(retries=3, backoff_factor=0.5, user_agent=BROWSER_USER_AGENT)

    target_url = "https://www.asx.com.au/markets/trade-our-derivatives-market/futures-market/rba-rate-tracker"

    logger.info(f"Fetching ASX RBA Rate Tracker data from {target_url}")

    try:
        response = session.get(target_url, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'lxml')

        # Check if page is JavaScript-rendered (common for modern ASX pages)
        page_text = soup.get_text(strip=True)
        if len(page_text) < 500 or "javascript" in page_text.lower()[:1000]:
            logger.warning("ASX page appears to be JavaScript-rendered. Static scraping may not work.")

            # Look for JSON data in script tags (common pattern for React/Vue apps)
            script_tags = soup.find_all('script')
            for script in script_tags:
                script_content = script.string if script.string else ""

                # Look for API endpoints or embedded data
                if 'api' in script_content.lower() or 'data' in script_content.lower():
                    # Try to find JSON-like patterns
                    json_match = re.search(r'\{["\'].*?rate.*?tracker.*?\}', script_content, re.IGNORECASE | re.DOTALL)
                    if json_match:
                        logger.info("Found potential JSON data in script tags")
                        # Further parsing would go here

                # Look for fetch/XHR URLs
                api_match = re.search(r'(https?://[^\s"\'\)]+(?:api|data)[^\s"\'\)]*)', script_content)
                if api_match:
                    api_url = api_match.group(1)
                    logger.info(f"Found potential API endpoint: {api_url}")
                    # Could try fetching this API directly

        # Try to find the rate tracker table/data
        # ASX typically uses tables or structured divs for this data
        tables = soup.find_all('table')

        if not tables:
            logger.warning("No HTML tables found on ASX Rate Tracker page")
            logger.warning("Page may be JavaScript-rendered or structure has changed")

            # Check for common React/Vue root elements
            react_root = soup.find('div', id=re.compile(r'root|app', re.IGNORECASE))
            if react_root and len(react_root.get_text(strip=True)) < 100:
                logger.warning("Found React/Vue root element with minimal content - page is JavaScript-rendered")
                logger.warning("Static scraping with BeautifulSoup will not work")
                logger.warning("Options: 1) Use Selenium/Playwright, 2) Find API endpoint, 3) Use alternative data source")

            raise ValueError("ASX Rate Tracker page structure not compatible with static scraping")

        # Look for the rate tracker table
        # Expected columns: Meeting Date, Implied Rate, Probability (Hold/Cut/Hike)
        rate_data = []
        scrape_date = datetime.now().strftime('%Y-%m-%d')

        for table in tables:
            rows = table.find_all('tr')
            if not rows:
                continue

            # Check if this table has rate-related headers
            header_row = rows[0]
            headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

            if any('meeting' in h or 'date' in h for h in headers) and any('rate' in h or 'implied' in h for h in headers):
                logger.info(f"Found rate tracker table with headers: {headers}")

                # Parse data rows
                for row in rows[1:]:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        cell_values = [cell.get_text(strip=True) for cell in cells]

                        # Try to extract meeting date and implied rate
                        # This is a best-effort parse - exact structure depends on ASX page format
                        try:
                            meeting_date = cell_values[0]  # Usually first column
                            implied_rate_str = cell_values[1]  # Usually second column

                            # Extract numeric rate (remove % sign if present)
                            implied_rate = float(re.sub(r'[^\d.]', '', implied_rate_str))

                            # Extract probabilities if available (columns 3-5 typically)
                            prob_hold = prob_cut = prob_hike = None
                            if len(cell_values) >= 5:
                                prob_hold = float(re.sub(r'[^\d.]', '', cell_values[2])) if cell_values[2] else None
                                prob_cut = float(re.sub(r'[^\d.]', '', cell_values[3])) if cell_values[3] else None
                                prob_hike = float(re.sub(r'[^\d.]', '', cell_values[4])) if cell_values[4] else None

                            rate_data.append({
                                'scrape_date': scrape_date,
                                'meeting_date': meeting_date,
                                'implied_rate': implied_rate,
                                'probability_hold': prob_hold,
                                'probability_cut': prob_cut,
                                'probability_hike': prob_hike,
                                'source': 'ASX'
                            })

                        except (ValueError, IndexError) as e:
                            logger.debug(f"Could not parse row: {cell_values} - {e}")
                            continue

        if not rate_data:
            raise ValueError("No rate tracker data extracted from ASX page - table structure may have changed")

        # Validate extracted data
        df = pd.DataFrame(rate_data)

        # Rates should be between 0-15%
        if not df['implied_rate'].between(0, 15).all():
            logger.warning(f"Some implied rates outside expected range 0-15%: {df['implied_rate'].describe()}")

        # Probabilities should sum to ~100% if present
        if 'probability_hold' in df.columns and df['probability_hold'].notna().any():
            prob_sums = df[['probability_hold', 'probability_cut', 'probability_hike']].sum(axis=1)
            if not prob_sums.between(95, 105).all():
                logger.warning(f"Some probability sums not ~100%: {prob_sums.describe()}")

        logger.info(f"Extracted {len(df)} meeting rate expectations from ASX")
        return df

    except Exception as e:
        logger.error(f"Failed to scrape ASX futures: {e}")
        logger.debug(traceback.format_exc())
        raise


def fetch_and_save() -> Dict[str, Union[str, int]]:
    """
    Fetch ASX futures data and save to CSV.
    Returns status dict - logs errors but doesn't raise (graceful degradation).

    Returns:
        Dict with 'status' key ('success' or 'failed') and additional info
    """
    try:
        df = scrape_asx_futures()

        if df.empty:
            logger.warning("ASX scraper returned no data")
            return {
                'status': 'failed',
                'error': 'No data extracted from ASX Rate Tracker'
            }

        output_path = DATA_DIR / "asx_futures.csv"
        row_count = append_to_csv(output_path, df, date_column='scrape_date')

        meeting_count = df['meeting_date'].nunique()

        logger.info(f"ASX futures data saved successfully: {row_count} total rows, {meeting_count} meetings")
        return {
            'status': 'success',
            'rows': row_count,
            'meetings': meeting_count
        }

    except Exception as e:
        # Log error but don't crash - allows pipeline to continue with other sources
        logger.error(f"ASX scraper failed: {e}")
        logger.debug(traceback.format_exc())
        return {
            'status': 'failed',
            'error': str(e)
        }


if __name__ == '__main__':
    print("ASX RBA Rate Tracker Scraper")
    print("=" * 50)
    result = fetch_and_save()
    print(f"\nResult: {result}")

    # If successful, show a sample of the data
    if result['status'] == 'success':
        try:
            df = pd.read_csv(DATA_DIR / "asx_futures.csv")
            print(f"\nData sample (first 5 rows):")
            print(df.head())
        except Exception as e:
            print(f"Could not read CSV: {e}")
