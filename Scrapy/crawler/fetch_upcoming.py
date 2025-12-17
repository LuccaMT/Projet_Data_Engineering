import argparse
import os
from dataclasses import asdict
from datetime import date, timedelta

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from flashscore_feed import (
    FEED_URL,
    REQUEST_HEADERS,
    Match,
    _date_to_offset,
    parse_feed,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recupere les matches de football a venir (ou en cours) pour une date donnee en utilisant Scrapy.",
    )
    parser.add_argument(
        "--date",
        help="Date cible au format YYYY-MM-DD. Par defaut: aujourd'hui.",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Decalage en jours depuis aujourd'hui si --date n'est pas fourni (0=today, 1=demain, -1=hier).",
    )
    parser.add_argument(
        "--variant",
        type=int,
        default=0,
        help="Variante du flux Flashscore (laisser 0 sauf besoin specifique).",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=1,
        help="Nombre de jours a scraper a partir de la date de depart (inclus). Exemple: 7 pour aujourd'hui + les 6 prochains jours.",
    )
    parser.add_argument(
        "--output",
        help="Chemin du fichier JSON de sortie. Par defaut: matches_upcoming_<date>.json",
    )
    return parser.parse_args()


def resolve_date(arg_date: str | None, offset: int) -> date:
    if arg_date:
        return date.fromisoformat(arg_date)
    return date.today() + timedelta(days=offset)


class UpcomingSpider(scrapy.Spider):
    name = "flashscore_upcoming"

    # On ne surcharge pas les custom_settings pour garder les pipelines du projet
    # custom_settings sont déjà définis dans settings.py

    def __init__(self, target_date: date, variant: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_date = target_date
        self.variant = variant

    def start_requests(self):
        offset = _date_to_offset(self.target_date)
        url = FEED_URL.format(sport_id=1, offset=offset, variant=self.variant)
        yield scrapy.Request(
            url,
            headers=REQUEST_HEADERS,
            callback=self.parse_feed_response,
            dont_filter=True,
            meta={"target_date": self.target_date},
        )

    def parse_feed_response(self, response: scrapy.http.TextResponse):
        for match in parse_feed(response.text):
            if match.status_code in {"1", "2"}:
                item = asdict(match)
                item["target_date"] = response.meta["target_date"].isoformat()
                yield item


def main() -> None:
    args = parse_args()
    target_date = resolve_date(args.date, args.offset)
    
    days = max(1, args.days)
    if days > 7:
        print(f"WARNING: Flashscore limite les donnees a +/- 7 jours. --days reduit de {days} a 7.")
        days = 7
    dates = [target_date + timedelta(days=offset) for offset in range(days)]

    # IMPORTANT: Charger les settings APRÈS avoir défini les variables d'environnement
    # car le module settings.py lit os.getenv() à l'import
    settings = get_project_settings()
    
    # Afficher la configuration pour debug
    print(f"Configuration MongoDB:")
    print(f"  MONGO_URI: {settings.get('MONGO_URI')}")
    print(f"  MONGO_DB: {settings.get('MONGO_DB')}")
    print(f"  Pipelines: {settings.get('ITEM_PIPELINES')}")
    
    # Ajouter le User-Agent
    settings.set('USER_AGENT', REQUEST_HEADERS["User-Agent"])
    
    # Si un output est spécifié, on garde aussi l'export JSON
    if args.output:
        output_path = args.output
        settings.set('FEEDS', {
            output_path: {
                "format": "json",
                "overwrite": True,
                "encoding": "utf-8",
            }
        })
        print(f"Export JSON configuré vers: {output_path}")

    process = CrawlerProcess(settings=settings)
    for dt in dates:
        process.crawl(UpcomingSpider, target_date=dt, variant=args.variant)
    process.start()
    
    mongo_uri = settings.get('MONGO_URI')
    mongo_db = settings.get('MONGO_DB')
    
    if mongo_uri:
        print(f"✅ Données stockées dans MongoDB ({mongo_db}.matches_upcoming)")
    if args.output:
        print(f"✅ Export JSON terminé -> {args.output}")



if __name__ == "__main__":
    main()
