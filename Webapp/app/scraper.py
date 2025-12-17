"""
Module pour exécuter le scraping Flashscore en appelant le conteneur scrapy,
avec un fallback local (sans docker) si le binaire docker n'est pas disponible.
"""
import os
import subprocess
from dataclasses import asdict
from datetime import date, datetime, timedelta
from typing import List, Optional

import requests
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError

# Variables d'environnement pour MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
MONGO_DB = os.getenv('MONGO_DB', 'flashscore')

# Import des utilitaires de parsing pour le fallback local (sans docker)
from scraper_modules import (
    FEED_URL,
    REQUEST_HEADERS,
    _date_to_offset,
    daterange,
    parse_feed,
)


def scrape_upcoming_matches(target_date: str) -> tuple[bool, str]:
    """
    Scrappe les matchs à venir pour une date donnée en appelant le conteneur scrapy
    
    Args:
        target_date: Date au format YYYY-MM-DD
    
    Returns:
        (success, message)
    """
    try:
        try:
            # Construire la commande pour exécuter dans le conteneur Scrapy
            docker_cmd = [
                "docker", "exec", "flashscore-scrapy",
                "python", "/app/crawler/fetch_upcoming.py",
                "--date", target_date
            ]
            
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, check=False, timeout=120)
            success = proc.returncode == 0
            
            if success:
                # Compter les matchs dans le message de sortie
                output = proc.stdout
                if "items processed:" in output:
                    # Extraire le nombre depuis "Total items processed: X"
                    import re
                    match = re.search(r'Total items processed: (\d+)', output)
                    if match:
                        count = match.group(1)
                        return True, f'Scraping completed: {count} items'
                return True, 'Scraping completed'
            else:
                return False, f"Erreur: {proc.stderr}"
        except FileNotFoundError:
            # Fallback local si la commande docker n'est pas disponible
            return _scrape_upcoming_local(target_date)
    except subprocess.TimeoutExpired:
        return False, "Scraping timeout (120s)"
    except Exception as e:
        return False, f"Erreur lors du scraping: {str(e)}"


def scrape_finished_matches(target_date: Optional[str] = None, month: Optional[str] = None) -> tuple[bool, str]:
    """
    Scrappe les matchs terminés pour une date ou un mois en appelant le conteneur scrapy
    
    Args:
        target_date: Date au format YYYY-MM-DD (optionnel)
        month: Mois au format YYYY-MM (optionnel)
    
    Returns:
        (success, message)
    """
    try:
        try:
            # Construire la commande pour exécuter dans le conteneur Scrapy
            docker_cmd = [
                "docker", "exec", "flashscore-scrapy",
                "python", "/app/crawler/fetch_finished.py"
            ]
            
            if target_date:
                docker_cmd.extend(["--date", target_date])
            elif month:
                docker_cmd.extend(["--month", month])
            else:
                return False, "Vous devez spécifier soit target_date soit month"
            
            proc = subprocess.run(docker_cmd, capture_output=True, text=True, check=False, timeout=180)
            success = proc.returncode == 0
            
            if success:
                # Compter les matchs dans le message de sortie
                output = proc.stdout
                if "items processed:" in output:
                    # Extraire le nombre depuis "Total items processed: X"
                    import re
                    match = re.search(r'Total items processed: (\d+)', output)
                    if match:
                        count = match.group(1)
                        return True, f'Scraping completed: {count} items'
                return True, 'Scraping completed'
            else:
                return False, f"Erreur: {proc.stderr}"
        except FileNotFoundError:
            # Fallback local si la commande docker n'est pas disponible
            return _scrape_finished_local(target_date=target_date, month=month)
    except subprocess.TimeoutExpired:
        return False, "Scraping timeout (180s)"
    except Exception as e:
        return False, f"Erreur lors du scraping: {str(e)}"


def _fetch_feed_for_date(target_date: date, status_filter: set[str]) -> List[dict]:
    """
    Récupère et parse le flux Flashscore pour une date donnée (fallback sans docker).
    """
    offset = _date_to_offset(target_date)
    url = FEED_URL.format(sport_id=1, offset=offset, variant=0)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    
    matches = []
    for match in parse_feed(resp.text):
        if match.status_code in status_filter:
            item = asdict(match)
            item["target_date"] = target_date.isoformat()
            matches.append(item)
    return matches


def _store_matches(collection: str, matches: List[dict]) -> int:
    """Stocke les matchs dans MongoDB en upsert (fallback sans docker)."""
    if not matches:
        return 0
    
    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    ops = []
    for item in matches:
        item["scraped_at"] = datetime.utcnow()
        if collection == "matches_upcoming":
            filt = {"id": item["id"]}
        else:
            filt = {"id": item["id"], "target_date": item.get("target_date")}
        ops.append(UpdateOne(filt, {"$set": item}, upsert=True))
    
    try:
        result = db[collection].bulk_write(ops, ordered=False)
        return result.upserted_count + result.modified_count
    except BulkWriteError as exc:
        return len(matches)
    finally:
        client.close()


def _scrape_upcoming_local(target_date: str) -> tuple[bool, str]:
    """
    Fallback local (sans docker) pour scraper une date de matchs à venir.
    """
    try:
        dt = date.fromisoformat(target_date)
    except ValueError:
        return False, f"Date invalide: {target_date}"
    
    try:
        matches = _fetch_feed_for_date(dt, {"1", "2"})
        stored = _store_matches("matches_upcoming", matches)
        return True, f"Scraping local: {len(matches)} match(s), {stored} upsert(s)"
    except Exception as exc:
        return False, f"Scraping local échoué: {exc}"


def _month_date_range(month: str) -> List[date]:
    year, m = map(int, month.split("-"))
    start = date(year, m, 1)
    if m == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, m + 1, 1) - timedelta(days=1)
    return list(daterange(start, end))


def _scrape_finished_local(target_date: Optional[str], month: Optional[str]) -> tuple[bool, str]:
    """
    Fallback local (sans docker) pour scraper les matchs terminés sur une date ou un mois.
    """
    dates: List[date]
    if target_date:
        try:
            dates = [date.fromisoformat(target_date)]
        except ValueError:
            return False, f"Date invalide: {target_date}"
    elif month:
        try:
            dates = _month_date_range(month)
        except Exception:
            return False, f"Mois invalide: {month}"
    else:
        return False, "Vous devez spécifier target_date ou month"
    
    try:
        collected: List[dict] = []
        for dt in dates:
            collected.extend(_fetch_feed_for_date(dt, {"3"}))
        stored = _store_matches("matches_finished", collected)
        return True, f"Scraping local: {len(collected)} match(s), {stored} upsert(s)"
    except Exception as exc:
        return False, f"Scraping local échoué: {exc}"
