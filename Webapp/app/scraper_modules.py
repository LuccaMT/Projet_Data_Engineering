"""
Modules Scrapy et utilitaires pour le scraping - Copie depuis le dossier Scrapy
Ce fichier contient tous les éléments nécessaires au scraping depuis la webapp
"""
import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Dict, Generator, List, Optional

import scrapy
import requests
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from scrapy.exceptions import NotConfigured


# ==================== CONSTANTES ET CONFIGURATION ====================

SEGMENT_SEPARATOR = "~"
ENTRY_SEPARATOR = "\xac"
KV_SEPARATOR = "\xf7"

FEED_URL = "https://d.flashscore.com/x/feed/f_{sport_id}_{offset}_{variant}_fr_1"

REQUEST_HEADERS = {
    "User-Agent": "ProjetDataEngBot/0.1 (+contact)",
    "x-fsign": "SW9D1eZo",
}

STATUS_MAP = {
    "1": "not_started",
    "2": "live",
    "3": "finished",
}


# ==================== FONCTIONS UTILITAIRES ====================

def _safe_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(value) if value not in (None, "", "-") else None
    except ValueError:
        return None


def _to_iso_utc(ts: Optional[str]) -> Optional[str]:
    try:
        return datetime.utcfromtimestamp(int(ts)).isoformat() + "Z" if ts else None
    except (ValueError, OSError, OverflowError):
        return None


def _date_to_offset(target: date) -> int:
    return (target - date.today()).days


def daterange(start: date, end: date) -> Generator[date, None, None]:
    current = start
    while current <= end:
        yield current
        current = current + timedelta(days=1)


# ==================== DATACLASS ====================

@dataclass
class Match:
    id: Optional[str]
    start_timestamp: Optional[int]
    start_time_utc: Optional[str]
    status_code: Optional[str]
    status: str
    league: Optional[str]
    country: Optional[str]
    competition_path: Optional[str]
    home: Optional[str]
    away: Optional[str]
    home_score: Optional[int]
    away_score: Optional[int]
    home_score_ht: Optional[int]
    away_score_ht: Optional[int]
    home_logo: Optional[str]
    away_logo: Optional[str]


# ==================== PARSING ====================

def parse_feed(feed_text: str) -> Generator[Match, None, None]:
    current_comp: Dict[str, str] = {}

    for segment in feed_text.split(SEGMENT_SEPARATOR):
        if not segment:
            continue

        kv: Dict[str, str] = {}
        for entry in segment.split(ENTRY_SEPARATOR):
            if KV_SEPARATOR in entry:
                key, value = entry.split(KV_SEPARATOR, 1)
                kv[key] = value

        if "ZA" in kv:
            current_comp = kv
            continue

        if "AA" in kv:
            status_code = kv.get("AB")

            def _logo_url(raw: Optional[str]) -> Optional[str]:
                if not raw:
                    return None
                if raw.startswith("http"):
                    return raw
                return f"https://static.flashscore.com/res/image/data/{raw}"

            yield Match(
                id=kv.get("AA"),
                start_timestamp=_safe_int(kv.get("AD")),
                start_time_utc=_to_iso_utc(kv.get("AD")),
                status_code=status_code,
                status=STATUS_MAP.get(status_code, "unknown"),
                league=current_comp.get("ZA"),
                country=current_comp.get("ZY"),
                competition_path=current_comp.get("ZL"),
                home=kv.get("AE"),
                away=kv.get("AF"),
                home_score=_safe_int(kv.get("AG")),
                away_score=_safe_int(kv.get("AH")),
                home_score_ht=_safe_int(kv.get("AT")),
                away_score_ht=_safe_int(kv.get("AU")),
                home_logo=_logo_url(kv.get("OA")),
                away_logo=_logo_url(kv.get("OB")),
            )


# ==================== SPIDERS ====================

class UpcomingSpider(scrapy.Spider):
    name = "flashscore_upcoming"

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


class FinishedSpider(scrapy.Spider):
    name = "flashscore_finished"

    def __init__(self, dates: List[date], variant: int, *args, **kwargs):
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
