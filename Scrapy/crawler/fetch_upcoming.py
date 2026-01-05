import argparse
import os
from dataclasses import asdict
from datetime import date, timedelta

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from flashscore_feed import (
    FEED_URL,
    REQUEST_HEADERS,
    Match,
    _date_to_offset,
    parse_feed,
)


def parse_args() -> argparse.Namespace:
    """Parse les arguments CLI pour le scraping des matches à venir.

    Returns:
        argparse.Namespace: Arguments parsés (date/offset/days/variant/leagues/output).
    """
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
        "--leagues",
        nargs="+",
        help="Filtrer uniquement ces ligues (ex: 'FRANCE: Ligue 1'). Si spécifié, la limite de 7 jours est levée.",
    )
    parser.add_argument(
        "--output",
        help="Chemin du fichier JSON de sortie. Par defaut: matches_upcoming_<date>.json",
    )
    return parser.parse_args()


def resolve_date(arg_date: str | None, offset: int) -> date:
    """Résout la date cible à partir de `--date` ou d'un offset.

    Args:
        arg_date (str | None): Date ISO (YYYY-MM-DD) ou None.
        offset (int): Décalage en jours appliqué si arg_date est None.

    Returns:
        date: Date cible.
    """
    if arg_date:
        return date.fromisoformat(arg_date)
    return date.today() + timedelta(days=offset)


class UpcomingSpider(scrapy.Spider):
    name = "flashscore_upcoming"

    def __init__(self, target_date: date, variant: int, league_filter: list[str] | None = None, *args, **kwargs):
        """Initialise le spider.

        Args:
            target_date (date): Date à scraper.
            variant (int): Variante du feed Flashscore.
            league_filter (list[str] | None): Liste de ligues autorisées (match.league).
            *args: Arguments Scrapy.
            **kwargs: Arguments Scrapy.
        """
        super().__init__(*args, **kwargs)
        self.target_date = target_date
        self.variant = variant
        self.league_filter = league_filter or []

    def start_requests(self):
        """Génère la requête vers le feed Flashscore pour la date cible."""
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
        """Parse la réponse du feed et yield les items à venir/en cours.

        Args:
            response (scrapy.http.TextResponse): Réponse HTTP (texte brut Flashscore).

        Yields:
            dict: Item prêt à être stocké (MongoDB pipeline).
        """
        for match in parse_feed(response.text):
            if match.status_code in {"1", "2"}:
                if self.league_filter and match.league not in self.league_filter:
                    continue
                    
                item = asdict(match)
                item["target_date"] = response.meta["target_date"].isoformat()
                yield item


def main() -> None:
    """Point d'entrée CLI.

    Configure Scrapy, planifie les dates à scraper et lance le process.

    Returns:
        None
    """
    args = parse_args()
    target_date = resolve_date(args.date, args.offset)
    
    days = max(1, args.days)
    
    # Si on filtre par ligues spécifiques (Top 5), on peut scraper plus loin
    if not args.leagues and days > 7:
        print(f"⚠️  WARNING: Without league filter, limited to 7 days (instead of {days}).")
        days = 7
    elif args.leagues:
        print(f"🌟 Extended scraping enabled for {len(args.leagues)} league(s): {days} days")
    
    dates = [target_date + timedelta(days=offset) for offset in range(days)]

    settings = get_project_settings()
    
    print(f"Configuration MongoDB:")
    print(f"  MONGO_URI: {settings.get('MONGO_URI')}")
    print(f"  MONGO_DB: {settings.get('MONGO_DB')}")
    print(f"  Pipelines: {settings.get('ITEM_PIPELINES')}")
    
    settings.set('USER_AGENT', REQUEST_HEADERS["User-Agent"])
    
    if args.output:
        output_path = args.output
        settings.set('FEEDS', {
            output_path: {
                "format": "json",
                "overwrite": True,
                "encoding": "utf-8",
            }
        })
        print(f"Export JSON configured to: {output_path}")

    process = CrawlerProcess(settings=settings)
    for dt in dates:
        process.crawl(UpcomingSpider, target_date=dt, variant=args.variant, league_filter=args.leagues)
    process.start()
    
    mongo_uri = settings.get('MONGO_URI')
    mongo_db = settings.get('MONGO_DB')
    
    if mongo_uri:
        print(f"✅ Data stored in MongoDB ({mongo_db}.matches_upcoming)")
    if args.output:
        print(f"✅ JSON export completed -> {args.output}")



if __name__ == "__main__":
    main()
