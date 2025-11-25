# captcha_solver.py
"""Utility to solve Cloudflare hCaptcha/reCAPTCHA challenges using 2Captcha.

Set the environment variable ``CAPTCHA_API_KEY`` with your 2Captcha API key.
The ``solve_captcha`` function takes the page URL and the site‑key and returns
the solution token, or ``None`` on failure.
"""
import os
import time
import requests
from typing import Optional

API_KEY = os.getenv("CAPTCHA_API_KEY", "914976fe886a909ad64fa8bc250ff60f")
API_ENDPOINT = "http://2captcha.com/in.php"
RESULT_ENDPOINT = "http://2captcha.com/res.php"

def _request_captcha(url: str, site_key: str) -> Optional[str]:
    """Submit a captcha solving request to 2Captcha.

    Returns the captcha ID if the request succeeded, otherwise ``None``.
    """
    if not API_KEY:
        print("[CAPTCHA] No API key found in CAPTCHA_API_KEY env var.")
        return None
    payload = {
        "key": API_KEY,
        "method": "hcaptcha",
        "sitekey": site_key,
        "pageurl": url,
        "json": 1,
    }
    try:
        resp = requests.post(API_ENDPOINT, data=payload, timeout=30)
        data = resp.json()
        if data.get("status") == 1:
            return data.get("request")
        print(f"[CAPTCHA] Submission error: {data}")
    except Exception as e:
        print(f"[CAPTCHA] Exception during submission: {e}")
    return None

def _poll_result(captcha_id: str, max_wait: int = 120) -> Optional[str]:
    """Poll 2Captcha for the solution token.

    ``max_wait`` is the total seconds to wait before giving up.
    """
    start = time.time()
    while time.time() - start < max_wait:
        try:
            resp = requests.get(
                RESULT_ENDPOINT,
                params={"key": API_KEY, "action": "get", "id": captcha_id, "json": 1},
                timeout=30,
            )
            data = resp.json()
            if data.get("status") == 1:
                return data.get("request")
            # 0 means still processing
            time.sleep(5)
        except Exception as e:
            print(f"[CAPTCHA] Polling exception: {e}")
            time.sleep(5)
    print("[CAPTCHA] Timed out waiting for solution.")
    return None

def solve_captcha(page_url: str, site_key: str) -> Optional[str]:
    """High‑level helper: submit and retrieve a captcha token.

    Returns the token string that can be injected into the page via
    ``document.getElementById('h-captcha-response').value = token`` (or the
    equivalent for reCAPTCHA).
    """
    captcha_id = _request_captcha(page_url, site_key)
    if not captcha_id:
        return None
    token = _poll_result(captcha_id)
    return token
