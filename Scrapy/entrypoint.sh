#!/bin/bash
set -e

echo "[startup] Lancement du conteneur Scrapy Flashscore"
echo "================================================"

wait_for_mongodb() {
    echo "[startup] Attente de MongoDB..."
    for i in {1..30}; do
        if python -c "from pymongo import MongoClient; MongoClient('$MONGO_URI', serverSelectionTimeoutMS=2000).admin.command('ping')" 2>/dev/null; then
            echo "[startup] MongoDB prêt"
            return 0
        fi
        echo "  tentative $i/30..."
        sleep 2
    done
    echo "[warn] MongoDB non accessible après 60s"
    return 1
}

wait_for_mongodb

echo
echo "[startup] Initialisation du tracker"
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.init_status(); tracker.close()"

echo
echo "[startup] Initialisation MongoDB"
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('mongodb_setup', 'in_progress', 0, 'Configuration MongoDB...'); tracker.close()"
if python /app/crawler/setup_mongodb.py; then
    python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('mongodb_setup', 'completed', 100); tracker.close()"
    echo "[ok] MongoDB initialisé"
else
    echo "[warn] Erreur initialisation MongoDB"
fi

echo
echo "[startup] Scraping initial"
echo "================================================"
echo "  -> Classements..."
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('classements', 'in_progress', 0, 'Récupération des classements...'); tracker.close()"
if python /app/crawler/fetch_standings.py 2>&1 | tail -10; then
    python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('classements', 'completed', 100); tracker.close()"
    echo "  [ok] Classements récupérés"
else
    echo "  [warn] Erreur classements"
fi

echo
echo "  -> Top 5 - Calendrier complet (liste directe)..."
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('top5_leagues', 'in_progress', 30, 'Scraping Top 5 championnats...'); tracker.close()"
if python -u /app/crawler/fetch_top5_full_season.py 2>&1 | tail -30; then
    python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('top5_leagues', 'completed', 100); tracker.close()"
    echo "  [ok] Top 5 - Calendrier complet OK"
else
    echo "  [warn] Erreur Top 5 calendrier complet"
fi

echo
echo "  -> Autres ligues - Page d'accueil (7+ jours)..."
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('other_leagues_upcoming', 'in_progress', 50, 'Matchs à venir page d accueil...'); tracker.close()"
if python /app/crawler/fetch_upcoming_selenium.py 2>&1 | tail -10; then
    python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('other_leagues_upcoming', 'completed', 100); tracker.close()"
    echo "  [ok] Autres ligues OK"
    
    # Normaliser les noms de ligues après scraping
    echo "  -> Normalisation des ligues..."
    python /app/crawler/update_league_names.py > /dev/null 2>&1
    echo "  [ok] Ligues normalisées"
else
    echo "  [warn] Erreur autres ligues"
fi

echo "  -> Matchs terminés (mois courant)..."
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('finished_matches', 'in_progress', 30, 'Matchs terminés...'); tracker.close()"
if python /app/crawler/fetch_finished.py --month $(date +%Y-%m) 2>&1 | tail -5; then
    python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('finished_matches', 'completed', 100); tracker.close()"
    echo "  [ok] Matchs terminés OK"
else
    echo "  [warn] Erreur matchs terminés"
fi

SEASON_YEAR=$(date +%Y)
CURRENT_MONTH=$(date +%m)
if [ "$CURRENT_MONTH" -lt 7 ]; then
  SEASON_YEAR=$((SEASON_YEAR - 1))
fi
SEASON_START="${SEASON_YEAR}-07-01"
TODAY="$(date +%Y-%m-%d)"
echo "  -> Historique saison (${SEASON_START} -> ${TODAY})..."
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('season_history', 'in_progress', 50, 'Historique saison...'); tracker.close()"
if python /app/crawler/fetch_finished.py --start-date "${SEASON_START}" --end-date "${TODAY}" 2>&1 | tail -5; then
    python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('season_history', 'completed', 100); tracker.close()"
    echo "  [ok] Historique OK"
else
    echo "  [warn] Erreur historique"
fi

echo "  -> Catalogue élargi..."
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('smart_catalog', 'in_progress', 70, 'Catalogue élargi...'); tracker.close()"
if python /app/crawler/fetch_smart_history.py 2>&1 | tail -5; then
    python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.update_step('smart_catalog', 'completed', 100); tracker.close()"
    echo "  [ok] Catalogue OK"
else
    echo "  [warn] Erreur catalogue"
fi

echo
python -c "from crawler.initialization_tracker import InitializationTracker; tracker = InitializationTracker(); tracker.mark_completed(); tracker.close()"
echo "================================================"
echo "[startup] Stats MongoDB:"
python -c "
from pymongo import MongoClient
import os
try:
    client = MongoClient(os.getenv('MONGO_URI'), serverSelectionTimeoutMS=5000)
    db = client[os.getenv('MONGO_DB', 'flashscore')]
    print(f'  - Matchs à venir: {db.matches_upcoming.count_documents({})}')
    print(f'  - Matchs terminés: {db.matches_finished.count_documents({})}')
    print(f'  - Classements: {db.standings.count_documents({})}')
    client.close()
except Exception as e:
    print(f'  Erreur: {e}')
"
echo "================================================"
echo "[loop] Scraping continu"
echo

continuous_scraping() {
    local iteration=1
    local standings_counter=0
    local homepage_counter=0
    
    while true; do
        local delay=$((5 + RANDOM % 10))
        sleep $delay

        # Every 120 iterations (~15-20 minutes), scrape homepage for all leagues (7+ days)
        homepage_counter=$((homepage_counter + 1))
        if [ $homepage_counter -ge 120 ]; then
            echo "[$(date +%H:%M:%S)] Scraping page d'accueil (toutes ligues, 7+ jours)..."
            python /app/crawler/fetch_upcoming_selenium.py > /dev/null 2>&1
            echo "[$(date +%H:%M:%S)] Normalisation des ligues..."
            python /app/crawler/update_league_names.py > /dev/null 2>&1
            homepage_counter=0
        fi

        # Every 10 iterations, check for finished matches
        if [ $((iteration % 10)) -eq 0 ]; then
            echo "[$(date +%H:%M:%S)] #$iteration - Vérification matchs terminés..."
            python /app/crawler/fetch_finished.py --date $(date +%Y-%m-%d) > /dev/null 2>&1
        fi
        
        # Update standings every ~30 minutes
        standings_counter=$((standings_counter + 1))
        if [ $standings_counter -ge 180 ]; then
            echo "[$(date +%H:%M:%S)] Mise à jour des classements..."
            python /app/crawler/fetch_standings.py > /dev/null 2>&1
            standings_counter=0
        fi

        iteration=$((iteration + 1))
    done
}

continuous_scraping
