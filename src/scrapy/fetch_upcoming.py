import argparse
from dataclasses import asdict
from datetime import date, timedelta

import scrapy
from scrapy.crawler import CrawlerProcess

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

    custom_settings = {
        "ROBOTSTXT_OBEY": False,  # feed endpoint; avoid robots fetch on every run
        "DOWNLOAD_DELAY": 0.5,
    }

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
    output_path = args.output or f"data/matches_upcoming_{target_date.isoformat()}.json"

    settings = {
        "FEEDS": {
            output_path: {
                "format": "json",
                "overwrite": True,
                "encoding": "utf-8",
            }
        },
        "USER_AGENT": REQUEST_HEADERS["User-Agent"],
    }

    process = CrawlerProcess(settings=settings)
    process.crawl(UpcomingSpider, target_date=target_date, variant=args.variant)
    process.start()
    print(f"Export termine -> {output_path}")


if __name__ == "__main__":
    main()
