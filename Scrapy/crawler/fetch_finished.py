import argparse
import os
from dataclasses import asdict
from datetime import date, timedelta
from typing import Iterable, List, Tuple

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

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
        description="Recupere les matches de football termines pour une date ou une plage de dates via Scrapy.",
    )
    parser.add_argument(
        "--date",
        help="Date cible au format YYYY-MM-DD. Par defaut: aujourd'hui.",
    )
    parser.add_argument(
        "--start-date",
        help="Date de debut au format YYYY-MM-DD (utilise avec --end-date).",
    )
    parser.add_argument(
        "--end-date",
        help="Date de fin au format YYYY-MM-DD (utilise avec --start-date).",
    )
    parser.add_argument(
        "--week-date",
        help="Une date (YYYY-MM-DD) appartenant a la semaine cible (lundi->dimanche).",
    )
    parser.add_argument(
        "--month",
        help="Mois cible au format YYYY-MM (ex: 2025-12). Par defaut: le mois en cours.",
    )
    parser.add_argument(
        "--year",
        type=int,
        help="Raccourci pour toute une annee (equivaut a start=1er janvier, end=31 decembre).",
    )
    parser.add_argument(
        "--offset",
        type=int,
        default=0,
        help="Decalage en jours si aucune date n'est fournie (0=today, 1=demain, -1=hier).",
    )
    parser.add_argument(
        "--variant",
        type=int,
        default=0,
        help="Variante du flux Flashscore (laisser 0 sauf besoin specifique).",
    )
    parser.add_argument(
        "--output",
        help="Chemin du fichier JSON de sortie. Par defaut: matches_finished_<date|year>.json",
    )
    return parser.parse_args()


def resolve_range(args: argparse.Namespace) -> Tuple[date, date, str]:
    if args.year:
        start = date(args.year, 1, 1)
        end = date(args.year, 12, 31)
        label = str(args.year)
        return start, end, label

    # Semaine (lundi -> dimanche) si specifiee
    if args.week_date:
        target = date.fromisoformat(args.week_date)
        start = target - timedelta(days=target.weekday())
        end = start + timedelta(days=6)
        label = f"week_{start.isoformat()}_to_{end.isoformat()}"
        return start, end, label

    # Mois cible (YYYY-MM) sinon mois courant par defaut
    if args.month:
        year, month = map(int, args.month.split("-"))
        target = date(year, month, 1)
    else:
        target = date.today()

    # Plage explicite jour a jour
    if args.start_date or args.end_date:
        start_str = args.start_date or args.end_date
        end_str = args.end_date or args.start_date
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
        label = f"{start.isoformat()}_to_{end.isoformat()}"
        return start, end, label

    if args.start_date or args.end_date:
        start_str = args.start_date or args.end_date
        end_str = args.end_date or args.start_date
        start = date.fromisoformat(start_str)
        end = date.fromisoformat(end_str)
        label = f"{start.isoformat()}_to_{end.isoformat()}"
        return start, end, label

    # Jour unique si --date fourni (ou via offset)
    if args.date:
        target_day = date.fromisoformat(args.date)
        return target_day, target_day, target_day.isoformat()
    if args.offset:
        target_day = date.today() + timedelta(days=args.offset)
        return target_day, target_day, target_day.isoformat()

    # Par defaut: mois du target (courant ou fourni)
    start = target.replace(day=1)
    if start.month == 12:
        end = date(start.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(start.year, start.month + 1, 1) - timedelta(days=1)
    label = f"month_{start.isoformat()}"
    return start, end, label


class FinishedSpider(scrapy.Spider):
    name = "flashscore_finished"

    # On ne surcharge pas les custom_settings pour garder les pipelines du projet
    # custom_settings sont déjà définis dans settings.py

    def __init__(self, dates: Iterable[date], variant: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dates = list(dates)
        self.variant = variant

    def start_requests(self):
        for dt in self.dates:
            offset = _date_to_offset(dt)
            url = FEED_URL.format(sport_id=1, offset=offset, variant=self.variant)
            yield scrapy.Request(
                url,
                headers=REQUEST_HEADERS,
                callback=self.parse_feed_response,
                dont_filter=True,
                meta={"target_date": dt},
            )

    def parse_feed_response(self, response: scrapy.http.TextResponse):
        for match in parse_feed(response.text):
            if match.status_code == "3":
                item = asdict(match)
                item["target_date"] = response.meta["target_date"].isoformat()
                yield item


def main() -> None:
    args = parse_args()
    start, end, label = resolve_range(args)
    dates = list(daterange(start, end))

    # Charger les settings du projet Scrapy (incluant MongoDB)
    settings = get_project_settings()
    
    # Récupérer les variables d'environnement pour MongoDB si disponibles
    mongo_uri = os.getenv('MONGO_URI')
    mongo_db = os.getenv('MONGO_DB')
    
    if mongo_uri:
        settings.set('MONGO_URI', mongo_uri)
    if mongo_db:
        settings.set('MONGO_DB', mongo_db)
    
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
    process.crawl(FinishedSpider, dates=dates, variant=args.variant)
    process.start()
    
    if mongo_uri:
        print(f"✅ Données stockées dans MongoDB ({mongo_db}.matches_finished)")
    if args.output:
        print(f"✅ Export JSON terminé -> {output_path}")


if __name__ == "__main__":
    main()
