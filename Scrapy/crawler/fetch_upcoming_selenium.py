"""Scrape upcoming matches from Flashscore homepage using Selenium.

This script scrapes the main Flashscore page which shows matches for multiple days
and multiple leagues (not limited to Top 5).
"""

import os
import sys
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from pymongo import MongoClient

from flashscore_feed import fetch_feed_for_date, parse_feed
from selenium_utils import create_chrome_driver


def log(msg: str) -> None:
    """Print a message immediately (flush stdout)."""
    print(msg, flush=True)
    sys.stdout.flush()


def _resolve_relative_date(label: str, now: datetime) -> Optional[date]:
    normalized = label.strip().lower()
    if normalized in ["aujourd'hui", "aujourd hui", "today"]:
        return now.date()
    if normalized in ["demain", "tomorrow"]:
        return now.date() + timedelta(days=1)
    if normalized in ["hier", "yesterday"]:
        return now.date() - timedelta(days=1)
    return None


def _resolve_date_near_today(day: int, month: int, now: datetime) -> Optional[date]:
    candidates: List[date] = []
    for year in (now.year - 1, now.year, now.year + 1):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(candidates, key=lambda d: abs((d - now.date()).days))


def _combine_date_time(target_date: date, time_text: str) -> Tuple[str, int]:
    time_text = time_text.strip()
    try:
        dt = datetime.strptime(f"{target_date.isoformat()} {time_text}", "%Y-%m-%d %H:%M")
    except ValueError:
        dt = datetime.combine(target_date, datetime.min.time())
    return target_date.isoformat(), int(dt.timestamp())


def parse_date_only(date_text: str) -> Tuple[Optional[str], Optional[datetime]]:
    """Parse just a date (no time) from homepage section headers.
    
    Args:
        date_text: Raw text like "09.02." or "Aujourd'hui" or "Demain".
    
    Returns:
        A tuple (YYYY-MM-DD, datetime object). Both can be None on parse failure.
    """
    try:
        date_text = date_text.strip()
        now = datetime.now()
        
        relative = _resolve_relative_date(date_text, now)
        if relative:
            return relative.isoformat(), datetime.combine(relative, datetime.min.time())
        
        # Handle "DD.MM." format
        if "." in date_text:
            parts = date_text.strip(".").split(".")
            if len(parts) >= 2:
                day = int(parts[0])
                month = int(parts[1])
                
                resolved = _resolve_date_near_today(day, month, now)
                if resolved:
                    return resolved.isoformat(), datetime.combine(resolved, datetime.min.time())
    except Exception as e:
        log(f"  ⚠️ Erreur parse date seule '{date_text}': {e}")
        return None, None
    
    return None, None


def parse_date_from_homepage(date_text: str) -> Tuple[Optional[str], Optional[int]]:
    """Parse a Flashscore homepage date/time into a date string and UNIX timestamp.

    Args:
        date_text: Raw text like "09.02. 20:00" or "Aujourd'hui 20:00" or "Demain 15:00".

    Returns:
        A tuple (YYYY-MM-DD, unix_timestamp). Both can be None on parse failure.
    """
    try:
        date_text = date_text.strip()
        if not date_text:
            return None, None

        now = datetime.now()
        parts = date_text.split()
        if not parts:
            return None, None

        relative = _resolve_relative_date(parts[0], now)
        if relative:
            time_part = parts[1] if len(parts) > 1 else "00:00"
            return _combine_date_time(relative, time_part)

        if len(parts) >= 2:
            date_part = parts[0]
            time_part = parts[1]

            day, month = date_part.rstrip(".").split(".")
            day = int(day)
            month = int(month)

            resolved = _resolve_date_near_today(day, month, now)
            if not resolved:
                return None, None
            return _combine_date_time(resolved, time_part)
    except Exception as e:
        log(f"  ⚠️ Erreur parse date+time '{date_text}': {e}")
        return None, None

    return None, None


def extract_match_id(element) -> Optional[str]:
    """Extract Flashscore match ID from an element."""
    try:
        match_id = element.get_attribute("id")
        if match_id and match_id.startswith("g_1_"):
            return match_id.replace("g_1_", "")
        return None
    except:
        return None


def build_feed_match_map(start_date: date, end_date: date) -> Dict[str, Dict[str, Optional[str]]]:
    mapping: Dict[str, Dict[str, Optional[str]]] = {}
    current = start_date
    while current <= end_date:
        try:
            feed_text = fetch_feed_for_date(current)
        except Exception as e:
            log(f"  [feed] Skipped {current} (error: {e})")
            current += timedelta(days=1)
            continue

        for match in parse_feed(feed_text):
            if not match.id:
                continue
            mapping[match.id] = {
                "league": match.league,
                "country": match.country,
                "competition_path": match.competition_path,
                "status": match.status,
                "status_code": match.status_code,
            }

        current += timedelta(days=1)

    log(f"  [feed] Mapping loaded: {len(mapping)} matches ({start_date} -> {end_date})")
    return mapping


def scrape_homepage_matches(driver, mongo_db, days_past: int = 7, days_future: int = 7) -> Dict[str, int]:
    """Scrape upcoming matches from Flashscore homepage.

    Args:
        driver: Selenium WebDriver.
        mongo_db: MongoDB database object.

    Returns:
        Dict with statistics (total, new, updated).
    """
    stats = {"total": 0, "new": 0, "updated": 0, "errors": 0}

    days_past = max(0, days_past)
    days_future = max(0, days_future)
    window_start = date.today() - timedelta(days=days_past)
    window_end = date.today() + timedelta(days=days_future)
    log(f"[window] Collecting matches from {window_start} to {window_end}")
    feed_map = build_feed_match_map(window_start, window_end)
    
    log("📡 Chargement de la page d'accueil Flashscore...")
    driver.get("https://www.flashscore.fr/")
    time.sleep(3)
    
    # Click "Show More" to load more matches
    log("🔄 Chargement de plus de matchs...")
    clicks = 0
    max_clicks = 10
    
    while clicks < max_clicks:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="wcl-buttonLink"]')
            if not buttons:
                break
            
            show_more = buttons[0]
            if not show_more.is_displayed():
                break
            
            driver.execute_script("arguments[0].scrollIntoView(true);", show_more)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", show_more)
            clicks += 1
            log(f"  ⏳ Clic #{clicks} sur 'Afficher plus'...")
            time.sleep(1.5)
        except:
            break
    
    log(f"✅ {clicks} clics effectués")
    
    # Parse all matches
    log("🔍 Parsing des matchs...")
    
    # Get all relevant elements in order: date headers, league headers, and matches
    all_elements = driver.find_elements(By.CSS_SELECTOR, "div.event__time--date, div.event__title, div.event__match[data-event-row='true']")
    log(f"  📊 {len(all_elements)} éléments trouvés (dates, ligues, matchs)")
    
    collection = mongo_db.matches_upcoming
    
    # Track current date and league as we iterate
    current_date = date.today()
    current_date_str = current_date.isoformat()
    current_league = "Unknown League"  # Default league
    
    for element in all_elements:
        try:
            # Check element type
            class_name = element.get_attribute("class") or ""
            
            # Update current date if this is a date header
            if "event__time--date" in class_name:
                date_text = element.text.strip()
                parsed_date, parsed_dt = parse_date_only(date_text)
                if parsed_date:
                    current_date_str = parsed_date
                    if parsed_dt:
                        current_date = parsed_dt.date()
                    else:
                        current_date = date.fromisoformat(parsed_date)
                    log(f"  📅 Date: {current_date_str}")
                continue
            
            # Update current league if this is a league header
            if "event__title" in class_name and "event__match" not in class_name:
                try:
                    # Extract league name from title elements
                    title_parts = []
                    
                    # Try to find country/region
                    country_elem = element.find_elements(By.CSS_SELECTOR, "span.event__title--type")
                    if country_elem:
                        title_parts.append(country_elem[0].text.strip())
                    
                    # Try to find league name
                    league_elem = element.find_elements(By.CSS_SELECTOR, "span.event__title--name")
                    if league_elem:
                        title_parts.append(league_elem[0].text.strip())
                    
                    if title_parts:
                        current_league = ": ".join(title_parts)
                        log(f"  🏆 Ligue: {current_league}")
                except:
                    pass
                continue
            
            # This should be a match element
            if "event__match" not in class_name:
                continue
            
            match_id = extract_match_id(element)
            if not match_id:
                # Try alternative method
                try:
                    link_elem = element.find_element(By.CSS_SELECTOR, "a.eventRowLink")
                    href = link_elem.get_attribute("href")
                    if href and "?mid=" in href:
                        match_id = href.split("?mid=")[1].split("&")[0]
                except:
                    pass
                
                if not match_id:
                    stats["errors"] += 1
                    continue
            
            # Extract data with correct selectors
            try:
                home_elem = element.find_element(By.CSS_SELECTOR, "div.event__homeParticipant span.wcl-name_jjfMf")
                away_elem = element.find_element(By.CSS_SELECTOR, "div.event__awayParticipant span.wcl-name_jjfMf")
                home = home_elem.text.strip()
                away = away_elem.text.strip()
            except Exception as e:
                stats["errors"] += 1
                continue
            
            # Date and time
            try:
                time_elem = element.find_element(By.CSS_SELECTOR, "div.event__time")
                time_text = time_elem.text.strip()
                # Remove any line breaks and extra text (e.g., "20:00\nRFS" -> "20:00")
                time_text = time_text.split('\n')[0].strip()
            except Exception as e:
                stats["errors"] += 1
                continue
            
            # Use current tracked date (filter within window)
            if current_date < window_start or current_date > window_end:
                continue

            target_date, timestamp = _combine_date_time(current_date, time_text)

            if not target_date:
                stats["errors"] += 1
                continue
            
            # Use feed mapping for league/status when available
            feed_info = feed_map.get(match_id, {})
            league = feed_info.get("league") or current_league or "Unknown League"
            status = feed_info.get("status") or "not_started"
            status_code = feed_info.get("status_code")
            if status_code is None:
                status_code = 0
            
            # Extract logos if available
            home_logo = None
            away_logo = None
            try:
                home_logo_elem = element.find_element(By.CSS_SELECTOR, "div.event__homeParticipant img")
                home_logo = home_logo_elem.get_attribute("src")
            except:
                pass
            
            try:
                away_logo_elem = element.find_element(By.CSS_SELECTOR, "div.event__awayParticipant img")
                away_logo = away_logo_elem.get_attribute("src")
            except:
                pass
            
            # Build match document
            match_doc = {
                "id": match_id,
                "home": home,
                "away": away,
                "home_logo": home_logo,
                "away_logo": away_logo,
                "league": league,
                "target_date": target_date,
                "start_timestamp": timestamp,
                "start_time_utc": datetime.utcfromtimestamp(timestamp).isoformat() + "Z" if timestamp else None,
                "status": status,
                "status_code": status_code,
                "home_score": None,
                "away_score": None,
                "scraped_at": datetime.utcnow(),
                "collection": "matches_upcoming"
            }

            if feed_info.get("country"):
                match_doc["country"] = feed_info.get("country")
            if feed_info.get("competition_path"):
                match_doc["competition_path"] = feed_info.get("competition_path")
            
            # Upsert to MongoDB
            result = collection.update_one(
                {"id": match_id},
                {"$set": match_doc},
                upsert=True
            )
            
            if result.upserted_id:
                stats["new"] += 1
            elif result.modified_count > 0:
                stats["updated"] += 1
            
            stats["total"] += 1
            
            if stats["total"] % 50 == 0:
                log(f"  📈 {stats['total']} matchs traités ({stats['new']} nouveaux, {stats['updated']} mis à jour)...")
        
        except Exception as e:
            stats["errors"] += 1
            log(f"  ⚠️ Erreur parsing match: {e}")
    
    return stats


def main():
    """Main entry point."""
    log("=" * 60)
    log("🚀 Scraping des matchs à venir depuis la page d'accueil")
    log("=" * 60)
    
    # MongoDB connection
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
    mongo_db_name = os.getenv('MONGO_DB', 'flashscore')
    
    client = MongoClient(mongo_uri)
    db = client[mongo_db_name]
    
    log(f"✅ Connecté à MongoDB: {mongo_db_name}")
    
    # Create driver
    driver = create_chrome_driver()
    
    try:
        stats = scrape_homepage_matches(driver, db)
        
        log("=" * 60)
        log("📊 Résumé du scraping:")
        log(f"  - Total matchs traités: {stats['total']}")
        log(f"  - Nouveaux matchs: {stats['new']}")
        log(f"  - Matchs mis à jour: {stats['updated']}")
        log(f"  - Erreurs: {stats['errors']}")
        log("=" * 60)
        
    finally:
        driver.quit()
        client.close()
        log("✅ Navigateur et connexion MongoDB fermés")


if __name__ == "__main__":
    main()
