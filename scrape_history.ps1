# Script PowerShell pour récupérer l'historique et maximiser le nombre de ligues
# Usage: .\scrape_history.ps1 [nombre_de_mois]

param(
    [int]$Months = 6
)

Write-Host "🎯 Objectif: Maximiser le nombre de ligues dans la base de données" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  IMPORTANT: Flashscore limite l'accès à ±7 jours autour d'aujourd'hui" -ForegroundColor Yellow
Write-Host "   Les données historiques peuvent être incomplètes ou vides." -ForegroundColor Yellow
Write-Host "   Pour un historique complet, le scraper doit tourner en continu." -ForegroundColor Yellow
Write-Host ""
Write-Host "📋 Options:" -ForegroundColor Green
Write-Host "   1. Scraper les 7 derniers jours (données complètes garanties)" -ForegroundColor White
Write-Host "   2. Scraper $Months mois (peut être incomplet)" -ForegroundColor White
Write-Host "   3. Vérifier les statistiques actuelles" -ForegroundColor White
Write-Host "   4. Annuler" -ForegroundColor White
Write-Host ""

$choice = Read-Host "Votre choix (1-4)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        Write-Host "🚀 Scraping des 7 derniers jours" -ForegroundColor Cyan
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        Write-Host ""
        
        $startDate = (Get-Date).AddDays(-7).ToString("yyyy-MM-dd")
        $endDate = (Get-Date).ToString("yyyy-MM-dd")
        
        docker exec flashscore-scrapy python /app/crawler/fetch_historical.py --start-date $startDate --end-date $endDate
    }
    "2" {
        Write-Host ""
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        Write-Host "🚀 Scraping de $Months mois (peut être incomplet)" -ForegroundColor Cyan
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        Write-Host ""
        
        docker exec flashscore-scrapy python /app/crawler/fetch_historical.py --months $Months
    }
    "3" {
        Write-Host ""
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        Write-Host "📊 Statistiques actuelles" -ForegroundColor Cyan
        Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
        Write-Host ""
        
        docker exec flashscore-scrapy python -c @"
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
    
    # Top 20 ligues
    print('   Top 20 ligues:')
    for i, league in enumerate(sorted(total_leagues)[:20], 1):
        print(f'      {i:2}. {league}')
    if len(total_leagues) > 20:
        print(f'      ... et {len(total_leagues) - 20} autres ligues')
    
    client.close()
except Exception as e:
    print(f'   ❌ Erreur: {e}')
"@
    }
    default {
        Write-Host ""
        Write-Host "❌ Annulé" -ForegroundColor Red
        exit 0
    }
}

Write-Host ""
Write-Host "✅ Terminé!" -ForegroundColor Green
Write-Host ""
