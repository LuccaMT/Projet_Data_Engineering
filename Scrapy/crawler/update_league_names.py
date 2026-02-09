"""Update league names for matches that have 'Unknown League'.

This script attempts to identify the correct league for matches by:
1. Using Flashscore feed data (most reliable)
2. Matching team names with existing matches that have known leagues
3. Extracting league from match URL structure (fallback)
4. Using pattern matching on team names (last resort)
"""

import re
import sys
from collections import defaultdict
from datetime import date

from pymongo import MongoClient

from flashscore_feed import fetch_feed_for_date, parse_feed


def log(msg: str) -> None:
    """Print a message immediately."""
    print(msg, flush=True)
    sys.stdout.flush()


def extract_league_from_patterns(home: str, away: str) -> str:
    """Try to extract league from team name patterns.
    
    Args:
        home: Home team name
        away: Away team name
        
    Returns:
        League name or None if not detected
    """
    # Common patterns in team names that indicate league
    patterns = {
        # Youth leagues
        r'\b(U19|U20|U21|U23|-19|-20|-21|-23)\b': 'Youth League',
        # Women's leagues
        r'\b(Women|Femmes|F\b|Féminin|Feminino)\b': 'Women\'s League',
        # Reserve leagues
        r'\b(Reserves?|B\b|II)\b': 'Reserve League',
        # Country-specific patterns
        r'\bJong\b': 'NETHERLANDS: Eerste Divisie',
        r'\bChampionship\b': 'ENGLAND: Championship',
        r'\bLigue 2\b': 'FRANCE: Ligue 2',
        r'\bSegunda\b': 'SPAIN: Segunda División',
        r'\bSerie B\b': 'ITALY: Serie B',
        r'\b2\. Bundesliga\b': 'GERMANY: 2. Bundesliga',
    }
    
    combined_text = f"{home} {away}"
    
    for pattern, league in patterns.items():
        if re.search(pattern, combined_text, re.IGNORECASE):
            return league
    
    # Try to detect by country/region in team names
    country_patterns = {
        r'\(Ukr\)|\(Geo\)|\(Kaz\)|\(Arm\)': 'INTERNATIONAL: Friendly',
        r'Sheffield|Middlesbrough|Leeds|Derby|Norwich': 'ENGLAND: Championship',
        r'Racing Santander|Mirandes|Eibar|Sporting Gijon': 'SPAIN: Segunda División',
        r'Amiens|Clermont|Bastia|Caen|Grenoble': 'FRANCE: Ligue 2',
        r'Aarhus|Odense|Vejle|Fredericia': 'DENMARK: Superliga',
        r'Anorthosis|Aris|AEL|Omonia|Chloraka': 'CYPRUS: First Division',
        r'M\. Tel Aviv|H\. Beer Sheva|B\. Jerusalem|Maccabi Bnei': 'ISRAEL: Ligat ha\'Al',
        r'Porto\b|Sporting\b|Benfica|Famalicao|Portimonense': 'PORTUGAL: Primeira Liga',
        r'Fenerbahce|Galatasaray|Besiktas|Gaziantep|Kasimpasa|Sakaryaspor|Erzurumspor': 'TURKEY: Süper Lig',
        r'Bucarest|Craiova|Steaua|Dinamo': 'ROMANIA: Liga I',
        r'Piast|Plock|Glogow|Rzeszow|Lech|Legia': 'POLAND: Ekstraklasa',
        r'Gimnasia|Estudiantes|Riestra|Talleres|Lanus|Barracas': 'ARGENTINA: Liga Profesional',
        r'Cerro\b|Danubio|Nacional|Penarol': 'URUGUAY: Primera División',
        r'Cobresal|Calera|Colo|Universidad': 'CHILE: Primera División',
        r'Cajamarca|Garcilaso|Cusco|Cristal': 'PERU: Liga 1',
        r'Cavalier|Spanish Town': 'JAMAICA: Premier League',
        r'Mons Calpe|Europa Point|Lincoln': 'GIBRALTAR: National League',
    }
    
    for pattern, league in country_patterns.items():
        if re.search(pattern, combined_text, re.IGNORECASE):
            return league
    
    return None


def build_team_to_league_mapping(mongo_db):
    """Build a mapping of team names to their leagues from known matches."""
    log("📊 Construction du mapping équipe -> ligue...")
    
    team_to_leagues = defaultdict(set)
    
    # Get all matches with known leagues (not "Unknown League")
    matches = mongo_db.matches_upcoming.find({"league": {"$ne": "Unknown League"}})
    
    for match in matches:
        league = match.get("league")
        home = match.get("home")
        away = match.get("away")
        
        if league and home:
            team_to_leagues[home].add(league)
        if league and away:
            team_to_leagues[away].add(league)
    
    # Also check finished matches
    matches = mongo_db.matches_finished.find({"league": {"$ne": "Unknown League"}})
    
    for match in matches:
        league = match.get("league")
        home = match.get("home")
        away = match.get("away")
        
        if league and home:
            team_to_leagues[home].add(league)
        if league and away:
            team_to_leagues[away].add(league)
    
    # Convert sets to most common league (first one)
    team_to_league = {}
    for team, leagues in team_to_leagues.items():
        if leagues:
            team_to_league[team] = list(leagues)[0]
    
    log(f"  ✅ {len(team_to_league)} équipes identifiées avec leur ligue")
    return team_to_league


def build_feed_match_map(dates: set[date]) -> dict[str, dict]:
    """Build a match-id -> league mapping from Flashscore feed for given dates."""
    mapping: dict[str, dict] = {}
    for target_date in sorted(dates):
        try:
            feed_text = fetch_feed_for_date(target_date)
        except Exception as e:
            log(f"  [feed] Skipped {target_date} (error: {e})")
            continue

        for match in parse_feed(feed_text):
            if not match.id or not match.league:
                continue
            mapping[match.id] = {
                "league": match.league,
                "country": match.country,
                "competition_path": match.competition_path,
            }

    log(f"  [feed] Mapping loaded for {len(mapping)} matchs")
    return mapping


def update_unknown_leagues(mongo_db, team_to_league):
    """Update matches with 'Unknown League' to their correct league."""
    log("\n🔄 Mise à jour des matchs avec 'Unknown League'...")
    
    collection = mongo_db.matches_upcoming
    unknown_matches = list(collection.find({"league": "Unknown League"}))
    
    log(f"  📊 {len(unknown_matches)} matchs trouvés avec 'Unknown League'")

    feed_dates = set()
    for match in unknown_matches:
        target_date = match.get("target_date")
        if not target_date:
            continue
        try:
            feed_dates.add(date.fromisoformat(target_date))
        except ValueError:
            continue

    feed_map = build_feed_match_map(feed_dates) if feed_dates else {}
    
    updated = 0
    updated_by_feed = 0
    updated_by_team = 0
    updated_by_pattern = 0
    not_found = 0
    
    for match in unknown_matches:
        match_id = match.get("id")
        home = match.get("home")
        away = match.get("away")
        
        # Multi-level approach to find league
        # Level 1: Feed data (most reliable)
        feed_info = feed_map.get(match_id) if feed_map else None
        league = None
        source = None
        
        if feed_info and feed_info.get("league"):
            league = feed_info.get("league")
            source = "feed"
            updated_by_feed += 1
        
        # Level 2: Team mapping (from known matches)
        if not league:
            if home in team_to_league:
                league = team_to_league[home]
                source = "team_home"
                updated_by_team += 1
            elif away in team_to_league:
                league = team_to_league[away]
                source = "team_away"
                updated_by_team += 1
        
        # Level 3: Pattern matching (last resort)
        if not league:
            league = extract_league_from_patterns(home, away)
            if league:
                source = "pattern"
                updated_by_pattern += 1
        
        if league:
            update_fields = {"league": league}
            if feed_info:
                if feed_info.get("country"):
                    update_fields["country"] = feed_info.get("country")
                if feed_info.get("competition_path"):
                    update_fields["competition_path"] = feed_info.get("competition_path")

            result = collection.update_one(
                {"id": match_id},
                {"$set": update_fields}
            )
            if result.modified_count > 0:
                updated += 1
                log(f"  ✅ {home} - {away}: {league} (source: {source})")
        else:
            not_found += 1
            log(f"  ⚠️ {home} - {away}: Ligue non identifiée")
    
    log(f"\n  📈 Détails:")
    log(f"    - Via feed Flashscore: {updated_by_feed}")
    log(f"    - Via mapping équipes: {updated_by_team}")
    log(f"    - Via patterns: {updated_by_pattern}")
    
    return updated, not_found


def main():
    """Main execution."""
    log("="*60)
    log("🔧 Mise à jour des noms de ligues")
    log("="*60)
    
    # Connect to MongoDB
    mongo_uri = "mongodb://admin:admin123@mongodb:27017/"
    client = MongoClient(mongo_uri)
    mongo_db = client["flashscore"]
    log("✅ Connecté à MongoDB: flashscore\n")
    
    # Build team to league mapping
    team_to_league = build_team_to_league_mapping(mongo_db)
    
    # Update unknown leagues
    updated, not_found = update_unknown_leagues(mongo_db, team_to_league)
    
    # Summary
    log("\n" + "="*60)
    log("📊 Résumé:")
    log(f"  - Matchs mis à jour: {updated}")
    log(f"  - Matchs non identifiés: {not_found}")
    log("="*60)
    
    client.close()
    log("✅ Terminé!")


if __name__ == "__main__":
    main()
