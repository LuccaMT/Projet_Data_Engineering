"""
Script de test pour vérifier que le scraping fonctionne
"""
import sys
sys.path.insert(0, '/app/app')

from datetime import date
from scraper import scrape_upcoming_matches
from database import get_db_connection

# Test scraping
print("=== Test scraping upcoming matches ===")
target_date = "2025-12-18"
print(f"Target date: {target_date}")

success, message = scrape_upcoming_matches(target_date)
print(f"Success: {success}")
print(f"Message: {message}")

# Vérifier dans MongoDB
print("\n=== Vérification MongoDB ===")
db = get_db_connection()
if db.connect():
    count = db.get_matches_count('matches_upcoming')
    print(f"Total matches in DB: {count}")
    
    matches = db.get_upcoming_matches(target_date)
    print(f"Matches for {target_date}: {len(matches)}")
    
    if matches:
        print(f"\nSample match: {matches[0]}")
else:
    print("Failed to connect to MongoDB")
