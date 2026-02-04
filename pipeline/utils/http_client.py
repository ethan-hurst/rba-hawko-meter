"""
HTTP client with retry logic and exponential backoff.
Handles transient network failures automatically.
"""

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pipeline.config import USER_AGENT


def create_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    user_agent: str = None
) -> requests.Session:
    """
    Create a requests.Session with retry logic configured.

    Args:
        retries: Maximum number of retry attempts
        backoff_factor: Backoff factor for exponential delay (0.5 = 0.5s, 1s, 2s...)
        user_agent: Custom User-Agent string (default: from config)

    Returns:
        Configured requests.Session instance
    """
    session = requests.Session()

    # Configure retry strategy
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],  # Retry on server errors
        allowed_methods=["GET", "POST"],
    )

    # Mount adapter with retry strategy on both HTTP and HTTPS
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    # Set User-Agent header
    session.headers.update({
        'User-Agent': user_agent or USER_AGENT
    })

    return session
