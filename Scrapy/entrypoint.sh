#!/bin/bash

# Script d'initialisation automatique pour le conteneur Scrapy
# Exécuté au démarrage du conteneur

set -e

echo "🚀 Démarrage du conteneur Scrapy Flashscore..."
echo "================================================"

# Fonction pour attendre que MongoDB soit prêt
wait_for_mongodb() {
    echo "⏳ Attente de MongoDB..."
    
    for i in {1..30}; do
        if python -c "from pymongo import MongoClient; MongoClient('$MONGO_URI', serverSelectionTimeoutMS=2000).admin.command('ping')" 2>/dev/null; then
            echo "✅ MongoDB est prêt"
            return 0
        fi
        echo "   Tentative $i/30..."
        sleep 2
    done
    
    echo "❌ MongoDB n'est pas accessible après 60 secondes"
    return 1
}

# Attendre MongoDB
if ! wait_for_mongodb; then
    echo "⚠️  Impossible de se connecter à MongoDB"
    echo "Le conteneur va continuer mais les fonctionnalités seront limitées"
fi

# Initialiser MongoDB (créer les collections et index)
echo ""
echo "📊 Initialisation de MongoDB..."
if python /app/crawler/setup_mongodb.py; then
    echo "✅ MongoDB initialisé"
else
    echo "⚠️  Erreur lors de l'initialisation de MongoDB"
fi

# Lancer un scraping initial
echo ""
echo "📥 Lancement du scraping initial..."

# Scraper les matchs à venir (prochains 7 jours)
echo "  → Matchs à venir (7 prochains jours)..."
# --days 8 pour couvrir aujourd'hui + 7 jours (offset 0 à 7)
if python /app/crawler/fetch_upcoming.py --date $(date +%Y-%m-%d) --days 8 2>&1 | tail -5; then
    echo "  ✅ Matchs à venir récupérés (8 jours, jusqu'à J+7)"
else
    echo "  ⚠️  Erreur lors du scraping des matchs à venir"
fi

# Scraper les matchs terminés (mois en cours)
echo "  → Matchs terminés (mois en cours)..."
if python /app/crawler/fetch_finished.py --month $(date +%Y-%m) 2>&1 | tail -5; then
    echo "  ✅ Matchs terminés récupérés"
else
    echo "  ⚠️  Erreur lors du scraping des matchs terminés"
fi

echo ""
echo "================================================"
echo "✅ Initialisation terminée"
echo "📊 Statistiques MongoDB:"
python -c "
from pymongo import MongoClient
import os
try:
    client = MongoClient(os.getenv('MONGO_URI'), serverSelectionTimeoutMS=5000)
    db = client[os.getenv('MONGO_DB', 'flashscore')]
    print(f'  - Matchs à venir: {db.matches_upcoming.count_documents({})}')
    print(f'  - Matchs terminés: {db.matches_finished.count_documents({})}')
    client.close()
except Exception as e:
    print(f'  Erreur: {e}')
"
echo "================================================"
echo "🔄 Lancement du scraping continu (délai aléatoire 1-10s)..."
echo ""

# Fonction de scraping continu
continuous_scraping() {
    local iteration=1
    
    while true; do
        # Délai aléatoire entre 1 et 10 secondes
        local delay=$((1 + RANDOM % 10))
        
        echo "🔄 Itération #$iteration - Prochain scraping dans ${delay}s..."
        sleep $delay
        
        local current_date=$(date +%Y-%m-%d)
        local current_time=$(date +%H:%M:%S)
        
        echo "[$current_time] 📥 Scraping en cours..."
        
        # Scraper les matchs à venir pour aujourd'hui
        if python /app/crawler/fetch_upcoming.py --date $current_date > /dev/null 2>&1; then
            echo "  ✅ Matchs à venir mis à jour"
        else
            echo "  ⚠️  Erreur matchs à venir"
        fi
        
        # Rafraîchir périodiquement la fenêtre des 7 prochains jours pour alimenter le dashboard
        if [ $((iteration % 60)) -eq 0 ]; then
            echo "  📅 Mise à jour des 7 prochains jours..."
            # --days 8 pour couvrir aujourd'hui + 7 jours
            if python /app/crawler/fetch_upcoming.py --date $current_date --days 8 > /dev/null 2>&1; then
                echo "  ✅ Fenetre 8 jours (J à J+7) mise à jour"
            else
                echo "  ⚠️  Erreur mise à jour 7 jours"
            fi
        fi
        
        # Toutes les 10 itérations, scraper aussi les matchs terminés
        if [ $((iteration % 10)) -eq 0 ]; then
            echo "  📊 Mise à jour des matchs terminés..."
            if python /app/crawler/fetch_finished.py --date $current_date > /dev/null 2>&1; then
                echo "  ✅ Matchs terminés mis à jour"
            else
                echo "  ⚠️  Erreur matchs terminés"
            fi
        fi
        
        iteration=$((iteration + 1))
    done
}

# Lancer le scraping continu
continuous_scraping
