"""Scrape full-season matches for Top 5 leagues from Flashscore.

This script loads both the fixtures (upcoming) and results (finished) pages for
each league and stores matches into MongoDB.
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from pymongo import MongoClient

from selenium_utils import create_chrome_driver


def log(msg: str) -> None:
    """Print a message immediately (flush stdout).

    Args:
        msg: Message to print.
    """
    print(msg, flush=True)
    sys.stdout.flush()

LEAGUES = {
    "FRANCE: Ligue 1": {
        "calendrier": "https://www.flashscore.fr/football/france/ligue-1/calendrier/",
        "resultats": "https://www.flashscore.fr/football/france/ligue-1/resultats/"
    },
    "ENGLAND: Premier League": {
        "calendrier": "https://www.flashscore.fr/football/angleterre/premier-league/calendrier/",
        "resultats": "https://www.flashscore.fr/football/angleterre/premier-league/resultats/"
    },
    "SPAIN: LaLiga": {
        "calendrier": "https://www.flashscore.fr/football/espagne/laliga/calendrier/",
        "resultats": "https://www.flashscore.fr/football/espagne/laliga/resultats/"
    },
    "ITALY: Serie A": {
        "calendrier": "https://www.flashscore.fr/football/italie/serie-a/calendrier/",
        "resultats": "https://www.flashscore.fr/football/italie/serie-a/resultats/"
    },
    "GERMANY: Bundesliga": {
        "calendrier": "https://www.flashscore.fr/football/allemagne/bundesliga/calendrier/",
        "resultats": "https://www.flashscore.fr/football/allemagne/bundesliga/resultats/"
    }
}


def click_show_more(driver) -> int:
    """Click "Afficher plus" until no more matches are loaded.

    Args:
        driver: Selenium WebDriver instance.

    Returns:
        Number of clicks performed.
    """
    clicked = 0
    max_attempts = 200
    no_change_count = 0
    previous_count = 0
    
    time.sleep(2)
    
    while clicked < max_attempts:
        try:
            current_count = len(driver.find_elements(By.CSS_SELECTOR, "div.event__match"))
            
            if current_count == previous_count and clicked > 0:
                no_change_count += 1
                if no_change_count >= 3:
                    log(f"  ℹ️ Aucun nouveau match après 3 tentatives, arrêt")
                    break
            else:
                no_change_count = 0
                previous_count = current_count
            
            buttons = driver.find_elements(By.CSS_SELECTOR, 'a[data-testid="wcl-buttonLink"]')
            
            if not buttons:
                break
            
            show_more_button = buttons[0]
            
            if not show_more_button.is_displayed():
                break
            
            driver.execute_script("arguments[0].scrollIntoView(true);", show_more_button)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", show_more_button)
            clicked += 1
            
            if clicked % 10 == 0:
                log(f"  ⏳ {clicked} clics, {current_count} matchs affichés...")
            
            time.sleep(1.5)
        except Exception as e:
            if clicked > 0:
                log(f"  ℹ️ Fin des clics après {clicked} tentatives")
            break
    
    return clicked


def parse_date_from_list(date_text: str, is_upcoming: bool = False) -> Tuple[Optional[str], Optional[int]]:
    """Parse a Flashscore list date/time into a date string and UNIX timestamp.

    Args:
        date_text: Raw text like "05.01. 21:00".
        is_upcoming: If True, resolves the year for future fixtures.

    Returns:
        A tuple (YYYY-MM-DD, unix_timestamp). Both can be None on parse failure.
    """
    try:
        parts = date_text.strip().split()
        if len(parts) >= 2:
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else "00:00"

            day, month = date_part.rstrip(".").split(".")
            day = int(day)
            month = int(month)

            current_date = datetime.now()
            current_year = current_date.year
            current_month = current_date.month

            if is_upcoming:
                year = current_year + 1 if month < current_month else current_year
            else:
                year = current_year - 1 if month > current_month else current_year

            date_str = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
            datetime_str = f"{date_str} {time_part}"

            dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M")
            timestamp = int(dt.timestamp())

            return date_str, timestamp
    except Exception as e:
        log(f"Erreur parse date '{date_text}': {e}")
        return None, None

    return None, None


def scrape_matches_from_list(driver, url: str, league_name: str, match_type: str) -> List[Dict]:
    """Scrape matches from a Flashscore list page (fixtures or results).

    Args:
        driver: Selenium WebDriver instance.
        url: Target Flashscore page URL.
        league_name: League display name.
        match_type: Either "calendrier" (upcoming) or "resultats" (finished).

    Returns:
        List of match documents.
    """
    log(f"\n{'='*60}")
    log(f"🔍 {league_name} - {match_type.upper()}")
    log(f"{'='*60}")
    
    driver.get(url)
    time.sleep(3)
    
    log(f"📄 Page chargée: {url}")
    
    clicks = click_show_more(driver)
    log(f"🔄 {clicks} clics sur 'Afficher plus'")
    
    time.sleep(2)
    
    matches = []
    
    try:
        match_elements = driver.find_elements(By.CSS_SELECTOR, "div.event__match[data-event-row='true']")
        log(f"📊 {len(match_elements)} éléments de match trouvés")
        
        for i, match_elem in enumerate(match_elements, 1):
            try:
                match_id = None
                
                try:
                    elem_id = match_elem.get_attribute("id")
                    if elem_id and elem_id.startswith("g_1_"):
                        match_id = elem_id.replace("g_1_", "")
                except:
                    pass
                
                if not match_id:
                    try:
                        link_elem = match_elem.find_element(By.CSS_SELECTOR, "a.eventRowLink")
                        href = link_elem.get_attribute("href")
                        if href and "?mid=" in href:
                            match_id = href.split("?mid=")[1].split("&")[0]
                    except:
                        pass
                
                if not match_id:
                    log(f"  ⚠️ Match #{i}: ID non trouvé, ignoré")
                    continue
                
                time_elem = match_elem.find_element(By.CSS_SELECTOR, "div.event__time")
                date_text = time_elem.text.strip()
                target_date, start_timestamp = parse_date_from_list(date_text, is_upcoming=(match_type == "calendrier"))
                
                if not target_date:
                    log(f"  ⚠️ Match #{i}: Date invalide, ignoré")
                    continue
                
                home_elem = match_elem.find_element(By.CSS_SELECTOR, "div.event__homeParticipant span.wcl-name_jjfMf")
                home_team = home_elem.text.strip()
                
                home_logo = None
                try:
                    home_logo_elem = match_elem.find_element(By.CSS_SELECTOR, "div.event__homeParticipant img")
                    home_logo = home_logo_elem.get_attribute("src")
                except:
                    pass
                
                away_elem = match_elem.find_element(By.CSS_SELECTOR, "div.event__awayParticipant span.wcl-name_jjfMf")
                away_team = away_elem.text.strip()
                
                away_logo = None
                try:
                    away_logo_elem = match_elem.find_element(By.CSS_SELECTOR, "div.event__awayParticipant img")
                    away_logo = away_logo_elem.get_attribute("src")
                except:
                    pass
                
                score_home = None
                score_away = None
                
                try:
                    score_home_elem = match_elem.find_element(By.CSS_SELECTOR, "span.event__score--home")
                    score_home = score_home_elem.text.strip()
                    
                    score_away_elem = match_elem.find_element(By.CSS_SELECTOR, "span.event__score--away")
                    score_away = score_away_elem.text.strip()
                except NoSuchElementException:
                    pass
                
                if match_type == "calendrier":
                    status = "not_started"
                    status_code = 0
                else:
                    if score_home and score_away:
                        status = "finished"
                        status_code = 100
                    else:
                        status = "finished"
                        status_code = 100
                
                match_data = {
                    "id": match_id,
                    "league": league_name,
                    "home": home_team,
                    "away": away_team,
                    "home_logo": home_logo,
                    "away_logo": away_logo,
                    "target_date": target_date,
                    "start_timestamp": start_timestamp,
                    "start_time_utc": datetime.fromtimestamp(start_timestamp).isoformat() if start_timestamp else None,
                    "status": status,
                    "status_code": status_code
                }
                
                if status == "finished" and score_home and score_away:
                    try:
                        match_data["home_score"] = int(score_home)
                        match_data["away_score"] = int(score_away)
                    except (ValueError, TypeError):
                        match_data["home_score"] = None
                        match_data["away_score"] = None
                
                matches.append(match_data)
                
                if i % 50 == 0:
                    log(f"  ⏳ Traitement: {i}/{len(match_elements)} matchs...")
                
            except Exception as e:
                log(f"  ⚠️ Erreur match #{i}: {e}")
                continue
        
        log(f"✅ {len(matches)} matchs extraits")
        
    except Exception as e:
        log(f"❌ Erreur extraction: {e}")
    
    return matches


def store_matches(matches: List[Dict], match_type: str) -> None:
    """Upsert matches into MongoDB.

    Args:
        matches: Matches to store.
        match_type: "calendrier" for upcoming, "resultats" for finished.
    """
    if not matches:
        log("⚠️ Aucun match à stocker")
        return

    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
    client = MongoClient(mongo_uri)
    db = client['flashscore']

    collection_name = "matches_upcoming" if match_type == "calendrier" else "matches_finished"
    collection = db[collection_name]

    inserted = 0
    updated = 0

    for match in matches:
        try:
            result = collection.update_one(
                {"id": match["id"]},
                {"$set": match},
                upsert=True,
            )

            if result.upserted_id:
                inserted += 1
            elif result.modified_count > 0:
                updated += 1

        except Exception as e:
            log(f"❌ Erreur stockage {match.get('id', 'unknown')}: {e}")

    log(f"💾 Stockage: {inserted} ajouts, {updated} mises à jour")
    client.close()


def scrape_league_full_season(league_name: str, urls: Dict[str, str]) -> None:
    """Scrape one league (fixtures + results) and store data.

    Args:
        league_name: League display name.
        urls: Mapping containing keys "calendrier" and "resultats".
    """
    log(f"\n{'='*70}")
    log(f"🏆 {league_name}")
    log(f"{'='*70}")
    
    driver = create_chrome_driver()
    
    try:
        upcoming_matches = scrape_matches_from_list(
            driver, 
            urls["calendrier"], 
            league_name, 
            "calendrier"
        )
        
        if upcoming_matches:
            store_matches(upcoming_matches, "calendrier")
        
        finished_matches = scrape_matches_from_list(
            driver, 
            urls["resultats"], 
            league_name, 
            "resultats"
        )
        
        if finished_matches:
            store_matches(finished_matches, "resultats")
        
        log(f"\n✅ {league_name}: {len(upcoming_matches)} à venir, {len(finished_matches)} terminés")
        
    finally:
        driver.quit()


def main() -> None:
    """Point d'entrée pour le scraping de saison complète."""
    log("="*70)
    log("🌟 SCRAPING TOP 5 LIGUES - SAISON COMPLÈTE")
    log("="*70)
    
    start_time = time.time()
    
    for league_name, urls in LEAGUES.items():
        try:
            scrape_league_full_season(league_name, urls)
        except Exception as e:
            log(f"❌ Erreur {league_name}: {e}")
    
    elapsed = time.time() - start_time
    log(f"\n{'='*70}")
    log(f"✅ SCRAPING TERMINÉ en {elapsed:.1f}s")
    log(f"{'='*70}")

if __name__ == "__main__":
    main()

