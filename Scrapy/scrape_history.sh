#!/bin/bash

# Script pour récupérer l'historique et maximiser le nombre de ligues
# Usage: ./scrape_history.sh [nombre_de_mois]

set -e

MONTHS=${1:-6}

echo "🎯 Objectif: Maximiser le nombre de ligues dans la base de données"
echo ""
echo "📋 Plan:"
echo "   1. Vérifier la configuration (dry-run)"
echo "   2. Récupérer l'historique des $MONTHS derniers mois"
echo "   3. Afficher les statistiques finales"
echo ""
echo "⏱️  Estimation: environ 1-2 minutes par mois (dépend de la connexion)"
echo ""

# Étape 1: Dry-run pour vérifier
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Étape 1/3: Vérification des dates (dry-run)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python /app/crawler/fetch_historical.py --months "$MONTHS" --dry-run

echo ""
read -p "▶️  Continuer avec le scraping? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Annulé par l'utilisateur"
    exit 0
fi

# Étape 2: Statistiques avant
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Statistiques AVANT le scraping"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python -c "
from pymongo import MongoClient
import os

try:
    client = MongoClient(os.getenv('MONGO_URI'), serverSelectionTimeoutMS=5000)
    db = client[os.getenv('MONGO_DB', 'flashscore')]
    
    upcoming_count = db.matches_upcoming.count_documents({})
    finished_count = db.matches_finished.count_documents({})
    
    upcoming_leagues = set(db.matches_upcoming.distinct('league'))
    finished_leagues = set(db.matches_finished.distinct('league'))
    total_leagues = upcoming_leagues.union(finished_leagues)
    
    print(f'   Matchs à venir    : {upcoming_count:>6}')
    print(f'   Matchs terminés   : {finished_count:>6}')
    print(f'   Total matchs      : {upcoming_count + finished_count:>6}')
    print()
    print(f'   Ligues (upcoming) : {len(upcoming_leagues):>6}')
    print(f'   Ligues (finished) : {len(finished_leagues):>6}')
    print(f'   Ligues uniques    : {len(total_leagues):>6}')
    
    client.close()
except Exception as e:
    print(f'   ❌ Erreur: {e}')
"

echo ""

# Étape 3: Lancer le scraping
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 Étape 2/3: Lancement du scraping historique"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

START_TIME=$(date +%s)

python /app/crawler/fetch_historical.py --months "$MONTHS"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

echo ""
echo "⏱️  Durée: ${MINUTES}m ${SECONDS}s"
echo ""

# Étape 4: Statistiques après
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Statistiques APRÈS le scraping"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

python -c "
from pymongo import MongoClient
import os

try:
    client = MongoClient(os.getenv('MONGO_URI'), serverSelectionTimeoutMS=5000)
    db = client[os.getenv('MONGO_DB', 'flashscore')]
    
    upcoming_count = db.matches_upcoming.count_documents({})
    finished_count = db.matches_finished.count_documents({})
    
    upcoming_leagues = set(db.matches_upcoming.distinct('league'))
    finished_leagues = set(db.matches_finished.distinct('league'))
    total_leagues = upcoming_leagues.union(finished_leagues)
    
    print(f'   Matchs à venir    : {upcoming_count:>6}')
    print(f'   Matchs terminés   : {finished_count:>6}')
    print(f'   Total matchs      : {upcoming_count + finished_count:>6}')
    print()
    print(f'   Ligues (upcoming) : {len(upcoming_leagues):>6}')
    print(f'   Ligues (finished) : {len(finished_leagues):>6}')
    print(f'   Ligues uniques    : {len(total_leagues):>6}')
    print()
    
    # Afficher quelques ligues pour vérification
    print('   Exemples de ligues:')
    for i, league in enumerate(sorted(total_leagues)[:10], 1):
        print(f'      {i:2}. {league}')
    if len(total_leagues) > 10:
        print(f'      ... et {len(total_leagues) - 10} autres ligues')
    
    client.close()
except Exception as e:
    print(f'   ❌ Erreur: {e}')
"

echo ""
echo "✅ Terminé!"
echo ""
