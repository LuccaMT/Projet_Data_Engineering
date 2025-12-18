"""
Script pour récupérer l'historique complet des matchs sur plusieurs mois
afin de maximiser le nombre de ligues dans la base de données.

Usage:
    python fetch_historical.py --months 6
    python fetch_historical.py --start-date 2024-06-01 --end-date 2024-12-17
"""

import argparse
import os
from dataclasses import asdict
from datetime import date, timedelta
from typing import Tuple

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
    daterange,
    parse_feed,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Récupère l'historique des matchs sur plusieurs mois pour maximiser les ligues.",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=6,
        help="Nombre de mois d'historique à récupérer (par défaut: 6 mois).",
    )
    parser.add_argument(
        "--start-date",
        help="Date de début au format YYYY-MM-DD (optionnel, sinon calculé depuis --months).",
    )
    parser.add_argument(
        "--end-date",
        help="Date de fin au format YYYY-MM-DD (par défaut: aujourd'hui).",
    )
    parser.add_argument(
        "--variant",
        type=int,
        default=0,
        help="Variante du flux Flashscore (laisser 0 sauf besoin spécifique).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Afficher les dates qui seront scrapées sans lancer le scraping.",
    )
    return parser.parse_args()


def resolve_date_range(args: argparse.Namespace) -> Tuple[date, date]:
    """Détermine la plage de dates à scraper."""
    end = date.fromisoformat(args.end_date) if args.end_date else date.today()
    
    if args.start_date:
        start = date.fromisoformat(args.start_date)
    else:
        # Calculer depuis N mois en arrière
        months = max(1, min(args.months, 12))  # Limiter à 12 mois
        # Approximation: 1 mois = 30 jours
        start = end - timedelta(days=months * 30)
    
    return start, end


class HistoricalSpider(scrapy.Spider):
    name = "flashscore_historical"
    
    def __init__(self, target_date: date, variant: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_date = target_date
        self.variant = variant
    
    def start_requests(self):
        offset = _date_to_offset(self.target_date)
        
        # Vérifier si la date est dans la limite de Flashscore (±7 jours)
        if abs(offset) > 7:
            self.logger.warning(
                f"Date {self.target_date} hors limite Flashscore (offset={offset}). "
                f"Flashscore limite à ±7 jours. Les données peuvent être incomplètes."
            )
        
        url = FEED_URL.format(sport_id=1, offset=offset, variant=self.variant)
        yield scrapy.Request(
            url,
            headers=REQUEST_HEADERS,
            callback=self.parse_feed_response,
            dont_filter=True,
            meta={"target_date": self.target_date},
            errback=self.handle_error,
        )
    
    def parse_feed_response(self, response: scrapy.http.TextResponse):
        """Parse le flux et extrait tous les matchs (terminés et à venir)."""
        match_count = 0
        for match in parse_feed(response.text):
            item = asdict(match)
            item["target_date"] = response.meta["target_date"].isoformat()
            
            # Router vers la bonne collection selon le statut
            if match.status_code == "3":  # Terminé
                item["collection"] = "matches_finished"
            else:  # À venir ou en cours
                item["collection"] = "matches_upcoming"
            
            match_count += 1
            yield item
        
        self.logger.info(
            f"Date {response.meta['target_date']}: {match_count} matchs récupérés"
        )
    
    def handle_error(self, failure):
        self.logger.error(f"Erreur de requête: {failure.value}")


def main() -> None:
    args = parse_args()
    start_date, end_date = resolve_date_range(args)
    
    # Générer la liste des dates à scraper
    dates = list(daterange(start_date, end_date))
    
    print("=" * 70)
    print("📅 RÉCUPÉRATION DE L'HISTORIQUE DES MATCHS")
    print("=" * 70)
    print(f"Date de début : {start_date}")
    print(f"Date de fin   : {end_date}")
    print(f"Nombre de jours : {len(dates)} jours")
    print(f"Période : {(end_date - start_date).days} jours")
    print()
    
    # Avertissement sur les limitations Flashscore
    today = date.today()
    days_outside = sum(1 for d in dates if abs((d - today).days) > 7)
    if days_outside > 0:
        print("⚠️  AVERTISSEMENT:")
        print(f"   {days_outside}/{len(dates)} dates sont hors de la fenêtre Flashscore (±7 jours)")
        print("   Ces dates peuvent retourner des données incomplètes ou vides.")
        print("   Pour un historique complet, il faut scraper régulièrement au fil du temps.")
        print()
    
    if args.dry_run:
        print("🔍 Mode dry-run - Dates qui seront scrapées:")
        for i, d in enumerate(dates[:10], 1):
            offset = (d - today).days
            print(f"   {i}. {d} (offset: {offset:+d} jours)")
        if len(dates) > 10:
            print(f"   ... et {len(dates) - 10} dates supplémentaires")
        print()
        print("Pour lancer le scraping, réexécutez sans --dry-run")
        return
    
    # Configuration MongoDB
    mongo_uri = os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/")
    mongo_db = os.getenv("MONGO_DB", "flashscore")
    
    print(f"📊 Configuration MongoDB:")
    print(f"   URI: {mongo_uri}")
    print(f"   Database: {mongo_db}")
    print()
    
    # Charger les settings du projet
    settings = get_project_settings()
    
    # Vérifier que les pipelines MongoDB sont activés
    if "pipelines.MongoDBPipeline" in str(settings.get("ITEM_PIPELINES", {})):
        print("✅ Pipeline MongoDB activé")
    else:
        print("⚠️  Pipeline MongoDB non trouvé dans settings.py")
    
    print()
    print("🚀 Lancement du scraping...")
    print(f"   Cela peut prendre plusieurs minutes pour {len(dates)} jours")
    print()
    
    # Créer et lancer le crawler
    process = CrawlerProcess(settings)
    
    # Lancer un spider pour chaque date
    for target_date in dates:
        process.crawl(
            HistoricalSpider,
            target_date=target_date,
            variant=args.variant,
        )
    
    process.start()
    
    print()
    print("=" * 70)
    print("✅ SCRAPING TERMINÉ")
    print("=" * 70)
    print()
    print("📊 Vérifier les statistiques dans MongoDB:")
    print("   docker exec flashscore-mongodb mongosh \\")
    print('     "mongodb://admin:admin123@localhost:27017/flashscore?authSource=admin" \\')
    print('     --quiet --eval "')
    print("       print('Matchs à venir:', db.matches_upcoming.countDocuments({}));")
    print("       print('Matchs terminés:', db.matches_finished.countDocuments({}));")
    print("       print('Ligues uniques upcoming:', db.matches_upcoming.distinct('league').length);")
    print("       print('Ligues uniques finished:', db.matches_finished.distinct('league').length);")
    print('     "')
    print()


if __name__ == "__main__":
    main()
