"""Debug script to inspect Flashscore homepage structure."""

import sys
import time
from selenium.webdriver.common.by import By
from selenium_utils import create_chrome_driver


def log(msg: str):
    print(msg, flush=True)
    sys.stdout.flush()


def main():
    log("Starting Chrome driver...")
    driver = create_chrome_driver()
    
    try:
        log("Loading Flashscore homepage...")
        driver.get("https://www.flashscore.fr/")
        time.sleep(3)
        
        # Try different selectors
        selectors_to_test = [
            "div.event__time--date",
            "div.event__title",
            "div.event__header",
            "span.event__title--type",
            "span.event__title--name",
            "[class*='event__title']",
            "[class*='event__header']",
        ]
        
        for selector in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                log(f"\nSelector: {selector}")
                log(f"  Found: {len(elements)} elements")
                if elements and len(elements) < 10:
                    for i, elem in enumerate(elements[:5]):
                        try:
                            text = elem.text.strip()[:100]
                            classes = elem.get_attribute("class")
                            log(f"  [{i}] text='{text}' classes='{classes}'")
                        except:
                            pass
            except Exception as e:
                log(f"  Error: {e}")
        
        # Get page source sample
        log("\n\nGetting page source sample...")
        source = driver.page_source
        
        # Find event__title occurrences
        import re
        title_pattern = re.compile(r'<div[^>]*class="[^"]*event__title[^"]*"[^>]*>(.*?)</div>', re.DOTALL)
        matches = title_pattern.findall(source[:50000])
        log(f"\nFound {len(matches)} div.event__title in first 50KB of HTML")
        for i, match in enumerate(matches[:3]):
            clean_match = match.replace('\n', ' ').strip()[:200]
            log(f"  [{i}] {clean_match}")
        
    finally:
        driver.quit()
        log("\nDriver closed")


if __name__ == "__main__":
    main()
