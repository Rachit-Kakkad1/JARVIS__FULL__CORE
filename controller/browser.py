"""
JARVIS Browser Controller — Chrome/YouTube/web automation via Selenium.
Singleton driver pattern: init once, reuse across calls.
"""

import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG

_driver = None
_selenium_available = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options as ChromeOptions
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    _selenium_available = True
except ImportError:
    print("⚠️  Selenium not installed. Browser automation disabled.")


def get_driver():
    """
    Get or create the Chrome WebDriver singleton.
    
    Returns:
        WebDriver instance or None if Selenium unavailable
    """
    global _driver

    if not _selenium_available:
        return None

    # Check if existing driver is still alive
    if _driver is not None:
        try:
            _ = _driver.session_id
            _driver.title  # Quick check if session is valid
            return _driver
        except Exception:
            _driver = None

    try:
        options = ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-notifications")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

        service = Service(ChromeDriverManager().install())
        _driver = webdriver.Chrome(service=service, options=options)
        return _driver

    except Exception as e:
        print(f"⚠️  Chrome WebDriver init failed: {e}")
        return None


def play_youtube(query):
    """
    Search and play a video on YouTube.
    
    Args:
        query: Search query string
    
    Returns:
        str: Confirmation message
    """
    driver = get_driver()
    if not driver:
        return f"Browser automation is not available, {CONFIG['USER_NAME']}. Please install selenium and webdriver-manager."

    try:
        search_url = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
        driver.get(search_url)
        time.sleep(2.5)

        # Click the first video result
        try:
            wait = WebDriverWait(driver, 10)
            first_video = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ytd-video-renderer a#video-title"))
            )
            first_video.click()
            return f"Playing '{query}' on YouTube, {CONFIG['USER_NAME']}."
        except Exception:
            # Fallback: try different selector
            try:
                first_video = driver.find_element(By.CSS_SELECTOR, "a#video-title")
                first_video.click()
                return f"Playing '{query}' on YouTube, {CONFIG['USER_NAME']}."
            except Exception:
                return f"Found YouTube results for '{query}', but couldn't auto-play, {CONFIG['USER_NAME']}."

    except Exception as e:
        return f"Error playing YouTube: {e}"


def open_url(url):
    """
    Open a URL in Chrome.
    
    Args:
        url: URL to navigate to
    
    Returns:
        str: Confirmation message
    """
    driver = get_driver()
    if not driver:
        return f"Browser automation is not available, {CONFIG['USER_NAME']}."

    try:
        if not url.startswith("http"):
            url = "https://" + url
        driver.get(url)
        return f"Navigating to {url}, {CONFIG['USER_NAME']}."
    except Exception as e:
        return f"Error navigating to {url}: {e}"


def new_tab(url=None):
    """
    Open a new browser tab, optionally navigating to a URL.
    
    Args:
        url: Optional URL to open in the new tab
    
    Returns:
        str: Confirmation message
    """
    driver = get_driver()
    if not driver:
        return f"Browser automation is not available, {CONFIG['USER_NAME']}."

    try:
        driver.execute_script("window.open('');")
        driver.switch_to.window(driver.window_handles[-1])
        if url:
            if not url.startswith("http"):
                url = "https://" + url
            driver.get(url)
            return f"New tab opened with {url}, {CONFIG['USER_NAME']}."
        return f"New tab opened, {CONFIG['USER_NAME']}."
    except Exception as e:
        return f"Error opening new tab: {e}"


def close_tab():
    """
    Close the current browser tab.
    
    Returns:
        str: Confirmation message
    """
    driver = get_driver()
    if not driver:
        return f"Browser automation is not available, {CONFIG['USER_NAME']}."

    try:
        driver.close()
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[-1])
        return f"Tab closed, {CONFIG['USER_NAME']}."
    except Exception as e:
        return f"Error closing tab: {e}"


def get_page_title():
    """
    Get the title of the current browser page.
    
    Returns:
        str: Page title or error message
    """
    driver = get_driver()
    if not driver:
        return "No browser session active."

    try:
        return driver.title
    except Exception:
        return "Could not retrieve page title."
