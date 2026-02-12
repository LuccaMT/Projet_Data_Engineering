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
    _date_to_offset,
    parse_feed,
)


def generate_strategic_dates():
    """Génère une liste de dates "stratégiques" pour maximiser la couverture.

    La stratégie inclut:
    - Fenêtre locale (±7 jours)
    - Échantillonnage sur 12 mois (jours 1/10/20)
    - Ancres coupes (dates typiques de phases importantes)

    Returns:
        list[date]: Liste triée et dédupliquée de dates.
    """
    today = date.today()
    strategic_dates = []

    print("Fenetre actuelle (±7 jours):")
    for offset in range(-7, 8):
        target = today + timedelta(days=offset)
        strategic_dates.append(target)
        print(f"   - {target} (J{offset:+d})")

    print()
    print("Echantillonnage elargi (12 derniers mois):")

    for month_offset in range(1, 13):
        target_month = today.month - month_offset
        target_year = today.year

        while target_month <= 0:
            target_month += 12
            target_year -= 1

        for day in [1, 10, 20]:
            try:
                target = date(target_year, target_month, day)
                if target <= today:
                    strategic_dates.append(target)
                    delta = (today - target).days
                    print(f"   - {target} ({delta} jours en arriere)")
            except ValueError:
                pass

    print()
    print("Ancres coupes (groupes/finales):")
    cup_anchor_days = [
        (2, 15), (3, 15), (4, 15), (5, 28),
        (8, 15), (9, 15), (10, 20), (12, 15),
    ]
    for anchor_year in [today.year, today.year - 1]:
        for m, d in cup_anchor_days:
            try:
                target = date(anchor_year, m, d)
                if target not in strategic_dates:
                    strategic_dates.append(target)
                    delta = (today - target).days
                    label = f"{delta} jours en arriere" if delta >= 0 else f"{-delta} jours devant"
                    print(f"   - {target} ({label})")
            except ValueError:
                pass

    return sorted(set(strategic_dates))


class SmartHistoricalSpider(scrapy.Spider):
    name = "flashscore_smart_historical"

    custom_settings = {
        'CONCURRENT_REQUESTS': 2,
        'DOWNLOAD_DELAY': 0.5,
    }

    def __init__(self, dates: list, variant: int = 0, *args, **kwargs):
        """Initialise le spider.

        Args:
            dates (list): Liste de dates (objets `date`).
            variant (int): Variante du feed Flashscore.
            *args: Arguments Scrapy.
            **kwargs: Arguments Scrapy.
        """
        super().__init__(*args, **kwargs)
        self.dates = dates
        self.variant = variant

    def start_requests(self):
        """Génère les requêtes Scrapy pour chaque date."""
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
        """Parse le feed et route les matches vers upcoming/finished.

        Args:
            response (scrapy.http.TextResponse): Réponse HTTP.

        Yields:
            dict: Item match enrichi avec `collection`.
        """
        match_count_finished = 0
        match_count_upcoming = 0
        leagues = set()

        for match in parse_feed(response.text):
            item = asdict(match)
            item["target_date"] = response.meta["target_date"].isoformat()

            if match.league:
                leagues.add(match.league)

            if match.status_code == "3":
                item["collection"] = "matches_finished"
                match_count_finished += 1
            else:
                item["collection"] = "matches_upcoming"
                match_count_upcoming += 1

            yield item

        total = match_count_finished + match_count_upcoming
        offset = response.meta["offset"]
        status_icon = "OK" if abs(offset) <= 7 else ("WARN" if total > 0 else "MISS")

        self.logger.info(
            f"{status_icon} {response.meta['target_date']} (offset {offset:+4d}): "
            f"{total:3d} matchs ({match_count_upcoming} upcoming, {match_count_finished} finished), "
            f"{len(leagues)} ligues"
        )

    def handle_error(self, failure):
        """Callback d'erreur Scrapy.

        Args:
            failure: Objet failure Scrapy/Twisted.

        Returns:
            None
        """
        self.logger.error(f"Erreur de requete: {failure.value}")


def main() -> None:
    """Point d'entrée CLI.

    Affiche les dates stratégiques, puis lance le spider sauf en mode dry-run.

    Returns:
        None
    """
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
    print("SCRAPING INTELLIGENT POUR MAXIMISER LES LIGUES/COUPES")
    print("=" * 70)
    print()

    strategic_dates = generate_strategic_dates()

    print()
    print("Resume:")
    print(f"   Total de dates a scraper: {len(strategic_dates)}")

    within_window = sum(1 for d in strategic_dates if abs((date.today() - d).days) <= 7)
    outside_window = len(strategic_dates) - within_window

    print(f"   - Dans la fenetre Flashscore (±7j): {within_window}")
    print(f"   - Hors fenetre (donnees limitees): {outside_window}")
    print()

    if args.dry_run:
        print("Mode dry-run active - Aucun scraping effectue")
        return

    print("Lancement du scraping...")
    print()

    settings = get_project_settings()
    settings.set('LOG_LEVEL', 'INFO')

    process = CrawlerProcess(settings)
    process.crawl(SmartHistoricalSpider, dates=strategic_dates)

    print()
    print("Scraping en cours...")
    process.start()

    print()
    print("=" * 70)
    print("SCRAPING TERMINE")
    print("=" * 70)


if __name__ == "__main__":
    main()
