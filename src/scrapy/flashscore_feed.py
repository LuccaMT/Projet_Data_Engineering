import json
from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from typing import Dict, Generator, List, Optional

import requests


# Flashscore utilise des flux obfusqués sous /x/feed/.
# Les réponses sont en texte brut avec :
#   - séparateur de segment : "~"
#   - séparateur clé/valeur : "\xf7" (signe de division)
#   - séparateur d'entrée dans un segment : "\xac" (signe de négation)
SEGMENT_SEPARATOR = "~"
ENTRY_SEPARATOR = "\xac"
KV_SEPARATOR = "\xf7"

# Modèle d'URL du flux :
#  - sport_id est 1 pour le football
#  - offset correspond au décalage en jours par rapport à aujourd'hui (par exemple, 0 = aujourd'hui, 1 = demain, -1 = hier)
#  - variant peut être laissé à 0 ; les autres variantes ne changent que l'ordre/la visibilité
FEED_URL = "https://d.flashscore.com/x/feed/f_{sport_id}_{offset}_{variant}_fr_1"

REQUEST_HEADERS = {
    "User-Agent": "ProjetDataEngBot/0.1 (+contact)",
    # En-tête requis pour accéder aux points de terminaison des flux.
    "x-fsign": "SW9D1eZo",
}

STATUS_MAP = {
    "1": "not_started",
    "2": "live",
    "3": "finished",
}


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


def fetch_feed_for_date(target: date, variant: int = 0, sport_id: int = 1) -> str:
    url = FEED_URL.format(sport_id=sport_id, offset=_date_to_offset(target), variant=variant)
    resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text


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

        # En-tête de compétition (ZA = nom de la compétition, ZY = pays, ZL = chemin)
        if "ZA" in kv:
            current_comp = kv
            continue

        # Enregistrement d'un match (AA = identifiant du match)
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


def dump_matches(matches: List[Match], output_path: str) -> None:
    data = [asdict(m) for m in matches]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def daterange(start: date, end: date) -> Generator[date, None, None]:
    current = start
    while current <= end:
        yield current
        current = current + timedelta(days=1)
