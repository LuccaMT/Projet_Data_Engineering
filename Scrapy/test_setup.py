#!/usr/bin/env python3
"""
Script de test simple pour vérifier que Scrapy fonctionne avec MongoDB
À exécuter DANS le conteneur scrapy
"""
import os
import sys
from datetime import date

# Ajouter le dossier crawler au path
sys.path.insert(0, '/app/crawler')

def test_mongodb_connection():
    """Test de connexion à MongoDB"""
    print("🔍 Test de connexion MongoDB...")
    try:
        from pymongo import MongoClient
        
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
        mongo_db = os.getenv('MONGO_DB', 'flashscore')
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        
        db = client[mongo_db]
        collections = db.list_collection_names()
        
        print(f"✅ Connexion MongoDB OK")
        print(f"   Base: {mongo_db}")
        print(f"   Collections: {collections}")
        
        # Compter les documents
        if 'matches_upcoming' in collections:
            count = db.matches_upcoming.count_documents({})
            print(f"   Matchs à venir: {count}")
        
        if 'matches_finished' in collections:
            count = db.matches_finished.count_documents({})
            print(f"   Matchs terminés: {count}")
        
        client.close()
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_scrapy_settings():
    """Test des settings Scrapy"""
    print("\n🔍 Test des settings Scrapy...")
    try:
        from scrapy.utils.project import get_project_settings
        
        settings = get_project_settings()
        
        print(f"✅ Settings Scrapy chargés")
        print(f"   MONGO_URI: {settings.get('MONGO_URI')}")
        print(f"   MONGO_DB: {settings.get('MONGO_DB')}")
        print(f"   ITEM_PIPELINES: {settings.get('ITEM_PIPELINES')}")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False


def test_feed_parsing():
    """Test du parsing du feed Flashscore"""
    print("\n🔍 Test du parsing du feed...")
    try:
        from flashscore_feed import fetch_feed_for_date, parse_feed
        
        today = date.today()
        print(f"   Récupération du feed pour {today}...")
        
        feed_text = fetch_feed_for_date(today)
        matches = list(parse_feed(feed_text))
        
        print(f"✅ Feed parsé avec succès")
        print(f"   Nombre de matchs trouvés: {len(matches)}")
        
        if matches:
            match = matches[0]
            print(f"   Exemple: {match.home} vs {match.away} ({match.status})")
        
        return True
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("TEST DE CONFIGURATION SCRAPY + MONGODB")
    print("=" * 60)
    
    results = []
    
    # Test 1: MongoDB
    results.append(test_mongodb_connection())
    
    # Test 2: Scrapy settings
    results.append(test_scrapy_settings())
    
    # Test 3: Feed parsing
    results.append(test_feed_parsing())
    
    print("\n" + "=" * 60)
    if all(results):
        print("✅ TOUS LES TESTS PASSÉS")
        print("=" * 60)
        return 0
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
