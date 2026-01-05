"""Scrape Flashscore standings (Top 5 leagues) and store them in MongoDB.

This script uses Selenium to extract the league table, including optional
qualification labels and their legend.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pymongo import MongoClient

sys.path.insert(0, os.path.dirname(__file__))

from selenium_utils import create_chrome_driver

LEAGUES_URLS = {
    "FRANCE: Ligue 1": "https://www.flashscore.fr/football/france/ligue-1/classement/",
    "SPAIN: LaLiga": "https://www.flashscore.fr/football/espagne/laliga/classement/",
    "ENGLAND: Premier League": "https://www.flashscore.fr/football/angleterre/premier-league/classement/",
    "GERMANY: Bundesliga": "https://www.flashscore.fr/football/allemagne/bundesliga/classement/",
    "ITALY: Serie A": "https://www.flashscore.fr/football/italie/serie-a/classement/",
}


def extract_league_name_from_url(url: str) -> str:
    """Infer a human-readable league name from a Flashscore URL.

    Args:
        url: Flashscore standings URL.

    Returns:
        A league label like "Country: League" when it can be inferred,
        otherwise "Unknown League".
    """
    match = re.search(r'/football/([^/]+)/([^/]+)/', url)
    if match:
        country = match.group(1).capitalize()
        league = match.group(2).replace('-', ' ').title()
        return f"{country}: {league}"
    return "Unknown League"


def scrape_standings(url: str, league_name: Optional[str] = None) -> Optional[Dict]:
    """Scrape standings for a league.

    Args:
        url: Flashscore standings URL.
        league_name: Optional display name. If omitted, it is inferred from the URL.

    Returns:
        A dict ready to store in MongoDB, or None if scraping failed or produced no data.
    """
    driver = None
    
    try:
        print(f"🌐 Ouverture de {url}")
        driver = create_chrome_driver()
        driver.get(url)
        
        print("   ⏳ Chargement...")
        wait = WebDriverWait(driver, 15)
        
        table_container = wait.until(
            EC.presence_of_element_located((By.ID, "tournament-table"))
        )
        
        time.sleep(2)
        
        rows = driver.find_elements(By.CSS_SELECTOR, "div.ui-table__row")
        
        if not rows:
            print("   ⚠️  No rows found")
            return None
        
        standings = []
        print(f"   📊 {len(rows)} rows found")
        
        for idx, row in enumerate(rows, 1):
            try:
                # Extract qualification info from rank badge
                qualification_label = None
                qualification_color = None
                try:
                    rank_elem = row.find_element(By.CSS_SELECTOR, "div.tableCellRank")
                    qualification_label = rank_elem.get_attribute("title")
                    
                    # Also extract color for reference
                    style = rank_elem.get_attribute("style")
                    if "background-color" in style:
                        color_match = re.search(r'background-color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
                        if color_match:
                            r, g, b = color_match.groups()
                            qualification_color = f"rgb({r}, {g}, {b})"
                except NoSuchElementException:
                    pass
                
                # Extraire le nom de l'équipe
                team_elem = row.find_element(By.CSS_SELECTOR, "a.tableCellParticipant__name")
                team_name = team_elem.text.strip()
                
                if not team_name:
                    continue
                
                # Extraire toutes les cellules de statistiques
                stat_cells = row.find_elements(By.CSS_SELECTOR, "span.table__cell")
                
                if len(stat_cells) >= 7:
                    # Parser les statistiques
                    # Format: MJ, V, N, D, BP:BC, Diff, Pts
                    goals_str = stat_cells[4].text  # Format "31:13"
                    goals_for = 0
                    goals_against = 0
                    
                    if ':' in goals_str:
                        try:
                            gf, ga = goals_str.split(':')
                            goals_for = int(gf)
                            goals_against = int(ga)
                        except (ValueError, IndexError):
                            pass
                    
                    team_data = {
                        "position": idx,
                        "team": team_name,
                        "played": int(stat_cells[0].text) if stat_cells[0].text.isdigit() else 0,
                        "wins": int(stat_cells[1].text) if stat_cells[1].text.isdigit() else 0,
                        "draws": int(stat_cells[2].text) if stat_cells[2].text.isdigit() else 0,
                        "losses": int(stat_cells[3].text) if stat_cells[3].text.isdigit() else 0,
                        "goals_for": goals_for,
                        "goals_against": goals_against,
                        "goal_difference": int(stat_cells[5].text) if stat_cells[5].text.lstrip('-').isdigit() else 0,
                        "points": int(stat_cells[6].text) if stat_cells[6].text.isdigit() else 0,
                    }
                    
                    # Ajouter les informations de qualification si présentes
                    if qualification_label:
                        team_data["qualification_label"] = qualification_label
                    if qualification_color:
                        team_data["qualification_color"] = qualification_color
                    
                    standings.append(team_data)
                    
            except (NoSuchElementException, ValueError, IndexError) as e:
                print(f"   ⚠️  Erreur parsing ligne {idx}: {e}")
                continue
        
        if not standings:
            print("   ❌ No data extracted")
            return None
        
        # Extraire la légende des qualifications
        qualification_legend = []
        try:
            # La légende est dans div.tableLegend
            legend_container = driver.find_element(By.CSS_SELECTOR, "div.tableLegend")
            legend_rows = legend_container.find_elements(By.CSS_SELECTOR, "div.tableLegend__row")
            
            for legend_row in legend_rows:
                try:
                    # Récupérer le carré de couleur
                    color_square = legend_row.find_element(By.CSS_SELECTOR, "div.tableLegend__coloredSquare")
                    style = color_square.get_attribute("style")
                    color = None
                    if "background-color" in style:
                        color_match = re.search(r'background-color:\s*rgb\((\d+),\s*(\d+),\s*(\d+)\)', style)
                        if color_match:
                            r, g, b = color_match.groups()
                            color = f"rgb({r}, {g}, {b})"
                    
                    # Récupérer le texte de description
                    text = legend_row.text.strip()
                    
                    if color and text:
                        qualification_legend.append({
                            "color": color,
                            "description": text
                        })
                except (NoSuchElementException, AttributeError):
                    continue
        except NoSuchElementException:
            print(f"   ⚠️  Legend not found")
        except Exception as e:
            print(f"   ⚠️  Error extracting legend: {e}")
        
        # Déterminer le nom de la ligue
        if not league_name:
            league_name = extract_league_name_from_url(url)
        
        result = {
            "league_name": league_name,
            "url": url,
            "season": "2025-2026",
            "standings": standings,
            "qualification_legend": qualification_legend,
            "scraped_at": datetime.utcnow().isoformat() + "Z",
            "total_teams": len(standings),
        }
        
        print(f"   ✅ {len(standings)} équipes extraites")
        if qualification_legend:
            print(f"   📋 {len(qualification_legend)} zones de qualification détectées")
        return result
        
    except TimeoutException:
        print("   ❌ Timeout: table did not load in time")
        return None
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None
    finally:
        if driver:
            driver.quit()


def save_to_mongodb(standings_data: Dict, mongo_uri: str, mongo_db: str) -> bool:
    """Save standings data into MongoDB.

    Args:
        standings_data: Standings document produced by :func:`scrape_standings`.
        mongo_uri: MongoDB connection URI.
        mongo_db: Database name.

    Returns:
        True on success, False otherwise.
    """
    try:
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        collection = db.standings
        
        # Créer l'index
        collection.create_index([("league_name", 1)], unique=True)
        
        # Upsert
        result = collection.update_one(
            {"league_name": standings_data["league_name"]},
            {"$set": standings_data},
            upsert=True
        )
        
        client.close()
        return True
        
    except Exception as e:
        print(f"❌ Erreur MongoDB: {e}")
        return False


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Scrape standings from Flashscore with Selenium"
    )
    parser.add_argument(
        "--league",
        action="append",
        choices=list(LEAGUES_URLS.keys()),
        help="League to scrape (can be repeated). If omitted, all leagues."
    )
    parser.add_argument(
        "--url",
        help="Custom URL of a Flashscore standings page"
    )
    parser.add_argument(
        "--name",
        help="League name for the custom URL"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file (optional)"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Do not save to MongoDB"
    )
    return parser.parse_args()


def main() -> None:
    """Point d'entrée pour l'utilisation CLI."""
    args = parse_args()
    
    # MongoDB configuration
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
    mongo_db = os.getenv('MONGO_DB', 'flashscore')
    
    all_standings = []
    success_count = 0
    
    # Custom URL mode
    if args.url:
        print(f"🚀 Scraping a custom URL\n")
        print("="*60)
        
        league_name = args.name if args.name else extract_league_name_from_url(args.url)
        standings_data = scrape_standings(args.url, league_name)
        
        if standings_data:
            all_standings.append(standings_data)
            if not args.no_db and save_to_mongodb(standings_data, mongo_uri, mongo_db):
                print(f"✅ Saved to MongoDB\n")
                success_count += 1
        
    # Mode ligues prédéfinies
    else:
        leagues_to_scrape = args.league if args.league else list(LEAGUES_URLS.keys())
        
        print(f"🚀 Scraping des classements pour {len(leagues_to_scrape)} ligue(s)\n")
        print("="*60)
        
        for league_name in leagues_to_scrape:
            url = LEAGUES_URLS[league_name]
            print(f"\n📊 {league_name}")
            print("-"*60)
            
            standings_data = scrape_standings(url, league_name)
            
            if standings_data:
                all_standings.append(standings_data)
                
                if not args.no_db and save_to_mongodb(standings_data, mongo_uri, mongo_db):
                    print(f"   ✅ Saved to MongoDB")
                    success_count += 1
            
            # Pause entre les requêtes
            if league_name != leagues_to_scrape[-1]:
                time.sleep(2)
    
    # Export JSON optionnel
    if args.output and all_standings:
        try:
            with open(args.output, 'w', encoding='utf-8') as f:
                json.dump(all_standings, f, ensure_ascii=False, indent=2)
            print(f"\n📄 Export JSON → {args.output}")
        except Exception as e:
            print(f"\n❌ Erreur export JSON: {e}")
    
    print("\n" + "="*60)
    print(f"✅ {success_count} classement(s) récupéré(s) avec succès")
    print("="*60)


if __name__ == "__main__":
    main()
