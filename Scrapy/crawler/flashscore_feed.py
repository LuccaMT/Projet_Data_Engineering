"""
Flashscore feed scraping and parsing module.

This module handles the retrieval and parsing of football match data
from Flashscore's obfuscated feed API. It provides functions to:
- Download match data for a given date
- Parse Flashscore's proprietary format
- Convert data into structured Python objects

The Flashscore data format uses special separators:
- '~': segment separator
- '÷' (\\xf7): key/value separator
- '¬' (\\xac): entry separator within a segment
"""

# Standard library
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Generator, Optional

# Third-party
import requests


# Flashscore uses obfuscated feeds under /x/feed/.
# Responses are in plain text with:
#   - segment separator: "~"
#   - key/value separator: "\xf7" (division sign)
#   - entry separator within a segment: "\xac" (negation sign)
SEGMENT_SEPARATOR = "~"
ENTRY_SEPARATOR = "\xac"
KV_SEPARATOR = "\xf7"

# Feed URL template:
#  - sport_id is 1 for football
#  - offset corresponds to the day offset from today (e.g., 0 = today, 1 = tomorrow, -1 = yesterday)
#  - variant can be left at 0; other variants only change order/visibility
#  - Flashscore migrated feeds from d.flashscore.com to global.flashscore.ninja
#    (project id 16 for flashscore.fr).
FEED_URL = "https://global.flashscore.ninja/16/x/feed/f_{sport_id}_{offset}_{variant}_fr_1"

REQUEST_HEADERS = {
    "User-Agent": "ProjetDataEngBot/0.1 (+contact)",
    # Required header to access feed endpoints.
    "x-fsign": "SW9D1eZo",
}

STATUS_MAP = {
    "1": "not_started",
    "2": "live",
    "3": "finished",
}


def _safe_int(value: Optional[str]) -> Optional[int]:
    """
    Safely convert a string to an integer.
    
    Args:
        value (Optional[str]): String to convert.
    
    Returns:
        Optional[int]: Converted integer or None if conversion fails or value is empty.
        
    Note:
        Returns None for values: None, "", "-", or if ValueError occurs.
    """
    try:
        return int(value) if value not in (None, "", "-") else None
    except ValueError:
        return None


def _to_iso_utc(ts: Optional[str]) -> Optional[str]:
    """
    Convert a Unix timestamp to an ISO 8601 UTC string.
    
    Args:
        ts (Optional[str]): Unix timestamp as a string.
    
    Returns:
        Optional[str]: Date/time in ISO 8601 format with 'Z', or None on error.
        
    Example:
        >>> _to_iso_utc("1704484800")
        '2024-01-05T20:00:00Z'
    """
    try:
        return datetime.utcfromtimestamp(int(ts)).isoformat() + "Z" if ts else None
    except (ValueError, OSError, OverflowError):
        return None


def _date_to_offset(target: date) -> int:
    """
    Calculate the number of days between a target date and today.
    
    Args:
        target (date): Target date.
    
    Returns:
        int: Number of days offset (positive = future, negative = past, 0 = today).
        
    Example:
        If today is 2024-01-05:
        >>> _date_to_offset(date(2024, 1, 6))
        1
        >>> _date_to_offset(date(2024, 1, 4))
        -1
    """
    return (target - date.today()).days


def daterange(start_date: date, end_date: date) -> Generator[date, None, None]:
    """
    Generate a range of dates from start_date to end_date (inclusive).
    
    Args:
        start_date (date): First date in the range.
        end_date (date): Last date in the range (inclusive).
    
    Yields:
        date: Each date in the range.
        
    Example:
        >>> list(daterange(date(2024, 1, 1), date(2024, 1, 3)))
        [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]
    """
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(days=n)


@dataclass
class Match:
    """
    Representation of a football match extracted from the Flashscore feed.
    
    Attributes:
        id (Optional[str]): Unique match identifier on Flashscore.
        start_timestamp (Optional[int]): Timestamp Unix du début du match.
        start_time_utc (Optional[str]): Date/heure de début au format ISO 8601.
        status_code (Optional[str]): Code de statut brut ('1', '2', '3').
        status (str): Statut lisible ('not_started', 'live', 'finished', 'unknown').
        league (Optional[str]): Nom de la compétition.
        country (Optional[str]): Pays de la compétition.
        competition_path (Optional[str]): Chemin complet de la compétition sur Flashscore.
        home (Optional[str]): Nom de l'équipe à domicile.
        away (Optional[str]): Nom de l'équipe à l'extérieur.
        home_score (Optional[int]): Score de l'équipe à domicile (temps plein).
        away_score (Optional[int]): Score de l'équipe à l'extérieur (temps plein).
        home_score_ht (Optional[int]): Score à domicile à la mi-temps.
        away_score_ht (Optional[int]): Score à l'extérieur à la mi-temps.
        home_logo (Optional[str]): URL du logo de l'équipe à domicile.
        away_logo (Optional[str]): URL du logo de l'équipe à l'extérieur.
    """
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


def fetch_feed_for_date(target: date, variant: int = 0, sport_id: int = 1) -> str:
    """
    Download the Flashscore feed for a given date.
    
    Args:
        target (date): Target date for which to retrieve matches.
        variant (int, optional): Feed variant (default: 0). Affects order/visibility.
        sport_id (int, optional): Sport ID (default: 1 for football).
    
    Returns:
        str: Raw feed content in Flashscore's proprietary format.
        
    Raises:
        requests.HTTPError: If HTTP request fails (non-2xx status code).
        requests.Timeout: If request exceeds 20 seconds.
        
    Note:
        Requires 'x-fsign' header for authentication.
    """
    url = FEED_URL.format(sport_id=sport_id, offset=_date_to_offset(target), variant=variant)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


def parse_feed(feed_text: str) -> Generator[Match, None, None]:
    """
    Parse the raw Flashscore feed and generate Match objects.
    
    This function is critical as it is used by all spiders.
    It decodes Flashscore's proprietary format into structured Python objects.
    
    Args:
        feed_text (str): Raw Flashscore feed content.
    
    Yields:
        Match: Match objects one by one for each match found in the feed.
        
    Note:
        The feed contains two types of segments:
        - Competition segments (with 'ZA' key): define the context
        - Match segments (with 'AA' key): contain match data
        
        Competition segments must precede their associated match segments.
    """
    current_comp: Dict[str, str] = {}

    for segment in feed_text.split(SEGMENT_SEPARATOR):
        if not segment:
            continue

        kv: Dict[str, str] = {}
        for entry in segment.split(ENTRY_SEPARATOR):
            if KV_SEPARATOR in entry:
                key, value = entry.split(KV_SEPARATOR, 1)
                kv[key] = value

        # Competition header (ZA = competition name, ZY = country, ZL = path)
        if "ZA" in kv:
            current_comp = kv
            continue

        # Match record (AA = match identifier)
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
