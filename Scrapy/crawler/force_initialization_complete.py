#!/usr/bin/env python3
"""Script utilitaire pour forcer le tracker d'initialisation à 'completed'.

Usage:
    python force_initialization_complete.py

Ce script est utile lorsque:
- L'initialisation a échoué mais les données sont présentes
- Le tracker est bloqué en 'in_progress'
- Vous voulez débloquer l'accès à l'application immédiatement
"""

import os
import sys
from pymongo import MongoClient
from datetime import datetime


def force_complete():
    """Force tous les steps à 'completed' et marque l'initialisation comme terminée."""
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
    mongo_db = os.getenv('MONGO_DB', 'flashscore')
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client[mongo_db]
        
        # Vérifier les données présentes
        upcoming_count = db.matches_upcoming.count_documents({})
        finished_count = db.matches_finished.count_documents({})
        standings_count = db.standings.count_documents({})
        
        print(f"📊 Données actuelles dans MongoDB:")
        print(f"  - Matchs à venir: {upcoming_count}")
        print(f"  - Matchs terminés: {finished_count}")
        print(f"  - Classements: {standings_count}")
        print()
        
        if (upcoming_count + finished_count) < 10:
            print("⚠️  ATTENTION: Très peu de données détectées!")
            print("   Il est recommandé de laisser le scraping initial se terminer.")
            response = input("   Forcer quand même le statut à 'completed'? (oui/non): ")
            if response.lower() not in ['oui', 'yes', 'o', 'y']:
                print("❌ Opération annulée.")
                return
        
        # Mettre à jour le tracker
        result = db.initialization_status.update_one(
            {},
            {
                "$set": {
                    "status": "completed",
                    "current_step": "Initialisation forcée manuellement",
                    "overall_progress": 100,
                    "completed_at": datetime.utcnow().isoformat(),
                    "steps.mongodb_setup": {"status": "completed", "progress": 100},
                    "steps.classements": {"status": "completed", "progress": 100},
                    "steps.top5_leagues": {"status": "completed", "progress": 100},
                    "steps.other_leagues_upcoming": {"status": "completed", "progress": 100},
                    "steps.finished_matches": {"status": "completed", "progress": 100},
                    "steps.season_history": {"status": "completed", "progress": 100},
                    "steps.smart_catalog": {"status": "completed", "progress": 100},
                }
            },
            upsert=True
        )
        
        if result.modified_count > 0 or result.upserted_id:
            print("✅ Tracker d'initialisation forcé à 'completed'")
            print("✅ L'application est maintenant accessible sans page de loading")
            print()
            print("💡 Vous pouvez vérifier l'état avec:")
            print("   docker exec flashscore-mongodb mongosh \"mongodb://admin:admin123@localhost:27017/flashscore?authSource=admin\" --eval \"db.initialization_status.findOne()\"")
        else:
            print("⚠️  Aucune modification effectuée (peut-être déjà à jour)")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("🔧 Forçage du statut d'initialisation à 'completed'")
    print("=" * 60)
    force_complete()
