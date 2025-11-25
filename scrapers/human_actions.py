# human_actions.py
"""Utility functions to add human‑like behaviour to Selenium/Playwright browsers.

These helpers are deliberately lightweight – they just add random delays,
mouse movements and scrolling. They can be imported and called from the
scraper before each interaction.
"""
import random
import time
from selenium.webdriver.common.action_chains import ActionChains

def random_delay(min_seconds: float = 1.0, max_seconds: float = 3.0):
    """Sleep for a random interval between *min_seconds* and *max_seconds*.
    """
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)

def human_scroll(driver, distance: int = None, steps: int = 10):
    """Scroll the page in small increments to mimic a user.
    If *distance* is None a random distance between 300‑800px is used.
    """
    if distance is None:
        distance = random.randint(300, 800)
    step = distance // steps
    for _ in range(steps):
        driver.execute_script(f"window.scrollBy(0, {step});")
        time.sleep(random.uniform(0.1, 0.3))

def human_move_mouse(driver, element):
    """Move the mouse cursor to *element* with a small random offset.
    Works with Selenium's ActionChains.
    """
    try:
        actions = ActionChains(driver)
        # Get element location
        loc = element.location_once_scrolled_into_view
        offset_x = random.randint(-5, 5)
        offset_y = random.randint(-5, 5)
        actions.move_by_offset(loc['x'] + offset_x, loc['y'] + offset_y)
        actions.perform()
        time.sleep(random.uniform(0.2, 0.5))
    except Exception:
        # Fallback – just pause
        time.sleep(random.uniform(0.5, 1.0))
