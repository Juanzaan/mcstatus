# flaresolverr_wrapper.py
"""Simple wrapper around a local FlareSolverr instance.

FlareSolverr runs a headless browser that automatically solves Cloudflare
challenges and returns the final HTML. It must be running (default
``http://127.0.0.1:8191``). This helper sends a request and returns the
``response`` field which contains the page source.
"""
import requests
from typing import Optional

FLARESOLVERR_URL = "http://127.0.0.1:8191/v1"

def fetch_page(url: str, max_timeout: int = 120) -> Optional[str]:
    """Request FlareSolverr to fetch *url*.

    Returns the HTML string on success or ``None`` on failure.
    """
    payload = {
        "cmd": "request.get",
        "url": url,
        "maxTimeout": max_timeout,
        "returnOnlyHeaders": False,
        "post": False,
        "session": "mcstatus",
    }
    try:
        resp = requests.post(FLARESOLVERR_URL, json=payload, timeout=30)
        data = resp.json()
        if data.get("status") == "ok":
            return data["solution"]["response"]
        print(f"[FlareSolverr] Error response: {data}")
    except Exception as e:
        print(f"[FlareSolverr] Exception: {e}")
    return None
