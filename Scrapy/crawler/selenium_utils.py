"""Common Selenium utilities used in Flashscore scrapers.

This module contains reusable functions to configure and manage
Selenium sessions in Docker context (Chromium + chromedriver).
"""

# Standard library
from typing import Optional

# Third-party
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def create_chrome_driver(
    *,
    chromedriver_path: str = "/usr/bin/chromedriver",
    chromium_binary: Optional[str] = "/usr/bin/chromium",
) -> webdriver.Chrome:
    """Create and configure a Chrome/Chromium driver for Selenium.

    Args:
        chromedriver_path (str): Path to chromedriver executable.
        chromium_binary (Optional[str]): Path to Chromium/Chrome executable.
            Set to None to let Selenium auto-detect.

    Returns:
        webdriver.Chrome: Configured driver instance.

    Note:
        Applied options (Docker-compatible): headless, no-sandbox,
        disable-dev-shm-usage, disable-gpu, window-size, user-agent.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    if chromium_binary:
        chrome_options.binary_location = chromium_binary

    service = Service(chromedriver_path)
    return webdriver.Chrome(service=service, options=chrome_options)
