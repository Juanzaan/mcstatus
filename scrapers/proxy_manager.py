# proxy_manager.py
"""Utility for managing residential proxy rotation.

Replace the placeholder values with credentials from your chosen provider.
The function returns a dictionary suitable for the `proxy` argument of
undetected_chromedriver or Playwright.
"""
import os
import random

# Example list of proxy URLs – replace with real ones or load from env/file.
PROXY_POOL = [
    # "http://user:pass@proxy1.residential.net:8000",
    # "http://user:pass@proxy2.residential.net:8000",
]

def get_random_proxy():
    """Return a random proxy URL from the pool or ``None`` if the pool is empty.
    The caller should pass the result directly to the browser launch options.
    """
    if not PROXY_POOL:
        return None
    return random.choice(PROXY_POOL)

def build_proxy_options():
    """Construct the ``proxy`` dict expected by the browser driver.

    Example return value for undetected_chromedriver::
        {"http": proxy_url, "https": proxy_url}
    """
    proxy_url = get_random_proxy()
    if not proxy_url:
        return None
    return {"http": proxy_url, "https": proxy_url}

# Helper to load proxy list from an environment variable (one per line)
def load_proxies_from_env(var_name="RESIDENTIAL_PROXIES"):
    raw = os.getenv(var_name, "")
    if raw:
        global PROXY_POOL
        PROXY_POOL = [p.strip() for p in raw.split("\n") if p.strip()]
