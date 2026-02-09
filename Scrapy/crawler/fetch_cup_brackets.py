"""
Script pour scraper les brackets (tableaux à élimination) des coupes depuis Flashscore.
Les brackets sont organisés par phases (poules, 1/8, 1/4, 1/2, finale).
"""

import os
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pymongo import MongoClient

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from crawler.selenium_utils import create_chrome_driver
from crawler.settings import MONGO_URI, MONGO_DB


# URLs des coupes à scraper
CUP_BRACKETS_URLS = {
    "FRANCE: Coupe De France": "https://www.flashscore.fr/football/france/coupe-de-france/",
    "EUROPE: UEFA Champions League": "https://www.flashscore.fr/football/europe/ligue-des-champions/",
    "EUROPE: UEFA Europa League": "https://www.flashscore.fr/football/europe/europa-league/",
    "EUROPE: UEFA Conference League": "https://www.flashscore.fr/football/europe/europa-conference-league/",
    "ENGLAND: FA Cup": "https://www.flashscore.fr/football/angleterre/fa-cup/",
    "SPAIN: Copa del Rey": "https://www.flashscore.fr/football/espagne/copa-del-rey/",
    "GERMANY: DFB Pokal": "https://www.flashscore.fr/football/allemagne/dfb-pokal/",
    "ITALY: Coppa Italia": "https://www.flashscore.fr/football/italie/coppa-italia/",
}


def scrape_cup_bracket(driver: webdriver.Chrome, league_name: str, url: str) -> Optional[Dict]:
    """
    Scrape le bracket d'une coupe depuis Flashscore.
    
    Args:
        driver: Instance du WebDriver Selenium.
        league_name: Nom de la ligue/coupe.
        url: URL de base de la coupe.
    
    Returns:
        Dictionnaire contenant les données du bracket, ou None si échec.
    """
    print(f"\n🏆 Scraping bracket: {league_name}")
    print(f"   URL: {url}")
    
    try:
        # Charger la page
        driver.get(url)
        time.sleep(3)
        
        # Gérer la bannière de cookies si elle apparaît
        try:
            cookie_button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
            cookie_button.click()
            print(f"   ✓ Cookies acceptés")
            time.sleep(1)
        except:
            pass
        
        # Chercher l'onglet "Tableau" ou "Brackets"
        try:
            # Essayer de trouver et cliquer sur l'onglet "Tableau"
            tabs = driver.find_elements(By.CSS_SELECTOR, ".tabs__tab")
            tableau_tab = None
            
            for tab in tabs:
                tab_text = tab.text.lower()
                if "tableau" in tab_text or "bracket" in tab_text or "draw" in tab_text:
                    tableau_tab = tab
                    break
            
            if tableau_tab:
                print(f"   ✓ Onglet 'Tableau' trouvé, clic...")
                # Scroll vers l'élément avant de cliquer
                driver.execute_script("arguments[0].scrollIntoView(true);", tableau_tab)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", tableau_tab)  # Clic JavaScript plus fiable
                time.sleep(5)  # Attendre plus longtemps que les données se chargent
                print(f"   ⏳ Attente du chargement des brackets...")
            else:
                print(f"   ⚠ Onglet 'Tableau' non trouvé")
        
        except Exception as e:
            print(f"   ⚠ Erreur lors de la recherche de l'onglet: {e}")
        
        # Chercher les données du bracket dans la structure .draw
        try:
            draw_container = driver.find_element(By.CSS_SELECTOR, ".draw")
            print(f"   ✓ Conteneur .draw trouvé")
            
            # Sauvegarder le HTML pour debug
            html_content = draw_container.get_attribute('outerHTML')
            debug_file = f"/tmp/draw_debug_{league_name.replace(' ', '_').replace(':', '')}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"   💾 HTML sauvegardé dans {debug_file} ({len(html_content)} chars)")
            
            # Extraire tous les tours/rounds
            phases = []
            rounds = draw_container.find_elements(By.CSS_SELECTOR, ".draw__round")
            print(f"   📊 {len(rounds)} tour(s) trouvé(s)")
            
            for round_elem in rounds:
                try:
                    # Nom du tour (1/16, 1/8, 1/4, etc.)
                    round_header = round_elem.find_element(By.CSS_SELECTOR, ".draw__header")
                    round_name = round_header.text.strip()
                    
                    # Extraire les matchs de ce tour
                    matches = []
                    
                    # Essayer de trouver le conteneur de brackets
                    try:
                        brackets_container = round_elem.find_element(By.CSS_SELECTOR, ".draw__brackets")
                        bracket_matches = brackets_container.find_elements(By.CSS_SELECTOR, ".draw__bracket")
                        print(f"      🔍 {round_name}: {len(bracket_matches)} bracket(s) trouvé(s)")
                    except NoSuchElementException:
                        print(f"      ⚠ {round_name}: .draw__brackets non trouvé, essai alternatif...")
                        # Essai alternatif : chercher directement les draw__bracket
                        bracket_matches = round_elem.find_elements(By.CSS_SELECTOR, ".draw__bracket")
                        print(f"      🔍 {round_name}: {len(bracket_matches)} bracket(s) trouvé(s) (alternatif)")
                    
                    for match_elem in bracket_matches:
                        try:
                            # Chercher le conteneur .bracket à l'intérieur
                            bracket = match_elem.find_element(By.CSS_SELECTOR, ".bracket")
                            
                            # Extraire équipe à domicile
                            try:
                                home_row = bracket.find_element(By.CSS_SELECTOR, ".bracket__participantRow--home")
                                home_name_elem = home_row.find_element(By.CSS_SELECTOR, ".bracket__name")
                                home_team = home_name_elem.text.strip()
                            except NoSuchElementException:
                                # Pas d'équipe à domicile, peut-être un match à venir
                                continue
                            
                            # Extraire équipe visiteur
                            try:
                                away_row = bracket.find_element(By.CSS_SELECTOR, ".bracket__participantRow--away")
                                away_name_elem = away_row.find_element(By.CSS_SELECTOR, ".bracket__name")
                                away_team = away_name_elem.text.strip()
                            except NoSuchElementException:
                                # Pas d'équipe visiteur, peut-être un match à venir
                                continue
                            
                            # Si on n'a pas les deux équipes, ignorer ce match
                            if not home_team or not away_team:
                                continue
                            
                            # Extraire scores
                            home_score = None
                            away_score = None
                            
                            try:
                                home_result = bracket.find_element(By.CSS_SELECTOR, ".bracket__result--home .result")
                                home_score = int(home_result.text.strip())
                            except (NoSuchElementException, ValueError):
                                pass
                            
                            try:
                                away_result = bracket.find_element(By.CSS_SELECTOR, ".bracket__result--away .result")
                                away_score = int(away_result.text.strip())
                            except (NoSuchElementException, ValueError):
                                pass
                            
                            match_data = {
                                "home": home_team,
                                "away": away_team,
                            }
                            
                            if home_score is not None:
                                match_data["home_score"] = home_score
                            if away_score is not None:
                                match_data["away_score"] = away_score
                            
                            matches.append(match_data)
                            print(f"         ✓ {home_team} {home_score if home_score is not None else '-'} - {away_score if away_score is not None else '-'} {away_team}")
                        
                        except Exception as e:
                            print(f"         ⚠ Match ignoré: {str(e)[:80]}")
                            continue
                    
                    if matches:
                        phases.append({
                            "round_name": round_name,
                            "matches": matches,
                        })
                        print(f"      ✓ {round_name}: {len(matches)} match(s)")
                
                except Exception as e:
                    print(f"      ⚠ Erreur tour: {e}")
                    continue
            
            if phases:
                print(f"   ✅ {len(phases)} phase(s) avec matchs extraite(s)")
                return {
                    "league": league_name,
                    "rounds": phases,
                    "scraped_at": datetime.utcnow().isoformat() + "Z",
                }
            else:
                print(f"   ⚠ Aucune phase avec matchs trouvée")
                return None
        
        except NoSuchElementException:
            print(f"   ⚠ Conteneur .draw non trouvé")
            return None
    
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return None


def main():
    """Fonction principale pour scraper tous les brackets des coupes."""
    print("=" * 60)
    print("🏆 SCRAPING DES BRACKETS DES COUPES")
    print("=" * 60)
    
    driver = None
    mongo_client = None
    
    try:
        # Connexion MongoDB
        mongo_client = MongoClient(MONGO_URI)
        db = mongo_client[MONGO_DB]
        print(f"✓ Connexion MongoDB établie\n")
        
        driver = create_chrome_driver()
        print("✓ WebDriver créé\n")
        
        scraped_count = 0
        failed_count = 0
        
        for league_name, url in CUP_BRACKETS_URLS.items():
            bracket_data = scrape_cup_bracket(driver, league_name, url)
            
            if bracket_data:
                # Sauvegarder dans MongoDB
                try:
                    db["cup_brackets"].replace_one(
                        {"league": league_name},
                        bracket_data,
                        upsert=True
                    )
                    print(f"   ✓ Sauvegardé dans MongoDB")
                    scraped_count += 1
                except Exception as e:
                    print(f"   ✗ Erreur MongoDB: {e}")
                    failed_count += 1
            else:
                failed_count += 1
            
            # Pause entre les requêtes
            time.sleep(2)
        
        print("\n" + "=" * 60)
        print(f"✅ Scraping terminé: {scraped_count} bracket(s) récupéré(s)")
        if failed_count > 0:
            print(f"⚠  {failed_count} bracket(s) non trouvé(s)")
        print("=" * 60)
    
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()
            print("\n✓ WebDriver fermé")
        
        if mongo_client:
            mongo_client.close()
            print("✓ Connexion MongoDB fermée")


if __name__ == "__main__":
    main()
