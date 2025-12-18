"""
Script intelligent pour maximiser les ligues en scrapant des périodes stratégiques.
Au lieu de scraper tous les jours (dont la plupart sont hors limite Flashscore),
on scrappe des dates clés espacées pour capturer différentes saisons/compétitions.
"""

import argparse
import os
from dataclasses import asdict
from datetime import date, timedelta

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

import sys
sys.path.insert(0, os.path.dirname(__file__))

from flashscore_feed import (
    FEED_URL,
    REQUEST_HEADERS,
    Match,
    _date_to_offset,
    parse_feed,
)


def generate_strategic_dates():
    """
    Génère des dates stratégiques pour maximiser la couverture des ligues.
    
    Stratégie:
    1. Fenêtre actuelle complète (J-7 à J+7) pour avoir toutes les ligues actives
    2. Dates passées stratégiques (début/milieu/fin de chaque mois sur 6 mois)
       pour capturer différentes saisons
    """
    today = date.today()
    strategic_dates = []
    
    # 1. Fenêtre actuelle complète (±7 jours)
    print("📅 Fenêtre actuelle (±7 jours):")
    for offset in range(-7, 8):
        target = today + timedelta(days=offset)
        strategic_dates.append(target)
        print(f"   • {target} (J{offset:+d})")
    
    print()
    print("📅 Échantillonnage historique (6 derniers mois):")
    
    # 2. Échantillonnage historique: 1er, 10e et 20e jour de chaque mois
    for month_offset in range(1, 7):  # 6 derniers mois
        # Calculer le mois cible
        target_month = today.month - month_offset
        target_year = today.year
        
        while target_month <= 0:
            target_month += 12
            target_year -= 1
        
        # 3 dates par mois: début, milieu, fin
        for day in [1, 10, 20]:
            try:
                target = date(target_year, target_month, day)
                if target < today:  # Seulement les dates passées
                    strategic_dates.append(target)
                    days_ago = (today - target).days
                    print(f"   • {target} ({days_ago} jours en arrière)")
            except ValueError:
                # Jour invalide pour ce mois (ex: 30 février)
                pass
    
    return sorted(set(strategic_dates))


class SmartHistoricalSpider(scrapy.Spider):
    name = "flashscore_smart_historical"
    
    custom_settings = {
        'CONCURRENT_REQUESTS': 2,  # Limiter pour ne pas surcharger
        'DOWNLOAD_DELAY': 0.5,  # Délai entre les requêtes
    }
    
    def __init__(self, dates: list, variant: int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dates = dates
        self.variant = variant
    
    def start_requests(self):
        for target_date in self.dates:
            offset = _date_to_offset(target_date)
            url = FEED_URL.format(sport_id=1, offset=offset, variant=self.variant)
            
            yield scrapy.Request(
                url,
                headers=REQUEST_HEADERS,
                callback=self.parse_feed_response,
                dont_filter=True,
                meta={"target_date": target_date, "offset": offset},
                errback=self.handle_error,
            )
    
    def parse_feed_response(self, response: scrapy.http.TextResponse):
        """Parse le flux et extrait tous les matchs."""
        match_count_finished = 0
        match_count_upcoming = 0
        leagues = set()
        
        for match in parse_feed(response.text):
            item = asdict(match)
            item["target_date"] = response.meta["target_date"].isoformat()
            
            # Ajouter la ligue au compteur
            if match.league:
                leagues.add(match.league)
            
            # Router vers la bonne collection selon le statut
            if match.status_code == "3":  # Terminé
                item["collection"] = "matches_finished"
                match_count_finished += 1
            else:  # À venir ou en cours
                item["collection"] = "matches_upcoming"
                match_count_upcoming += 1
            
            yield item
        
        total = match_count_finished + match_count_upcoming
        offset = response.meta["offset"]
        
        if abs(offset) <= 7:
            status_icon = "✅"
        else:
            status_icon = "⚠️ " if total > 0 else "❌"
        
        self.logger.info(
            f"{status_icon} {response.meta['target_date']} (offset {offset:+4d}): "
            f"{total:3d} matchs ({match_count_upcoming} upcoming, {match_count_finished} finished), "
            f"{len(leagues)} ligues"
        )
    
    def handle_error(self, failure):
        self.logger.error(f"Erreur de requête: {failure.value}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraping intelligent pour maximiser les ligues avec des dates stratégiques.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les dates sans lancer le scraping.",
    )
    args = parser.parse_args()
    
    print("=" * 70)
    print("🎯 SCRAPING INTELLIGENT POUR MAXIMISER LES LIGUES")
    print("=" * 70)
    print()
    
    strategic_dates = generate_strategic_dates()
    
    print()
    print(f"📊 Résumé:")
    print(f"   Total de dates à scraper: {len(strategic_dates)}")
    
    within_window = sum(1 for d in strategic_dates if abs((date.today() - d).days) <= 7)
    outside_window = len(strategic_dates) - within_window
    
    print(f"   • Dans la fenêtre Flashscore (±7j): {within_window}")
    print(f"   • Hors fenêtre (données limitées): {outside_window}")
    print()
    
    if args.dry_run:
        print("🔍 Mode dry-run activé - Aucun scraping effectué")
        return
    
    print("🚀 Lancement du scraping...")
    print()
    
    # Charger les settings du projet
    settings = get_project_settings()
    
    # Configuration spécifique
    settings.set('LOG_LEVEL', 'INFO')
    
    # Créer et lancer le crawler
    process = CrawlerProcess(settings)
    process.crawl(SmartHistoricalSpider, dates=strategic_dates)
    
    print()
    print("⏳ Scraping en cours...")
    process.start()
    
    print()
    print("=" * 70)
    print("✅ SCRAPING TERMINÉ")
    print("=" * 70)


if __name__ == "__main__":
    main()
