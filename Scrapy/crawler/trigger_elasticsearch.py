"""
Trigger l'indexation Elasticsearch depuis le container Scrapy
Ce script demande à la webapp de lancer l'indexation
"""
import os
import sys
import time
from pymongo import MongoClient

def trigger_indexation():
    """Marque l'indexation comme nécessaire dans MongoDB pour que la webapp la lance"""
    try:
        # Connexion MongoDB
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
        client = MongoClient(mongo_uri)
        db = client["flashscore"]
        
        # Marquer qu'on a besoin d'une indexation
        db.initialization_status.update_one(
            {},
            {
                "$set": {
                    "steps.elasticsearch_indexing.status": "pending",
                    "steps.elasticsearch_indexing.progress": 0,
                    "elasticsearch_trigger": True,
                    "elasticsearch_trigger_time": time.time()
                }
            }
        )
        
        print("✅ Signal d'indexation Elasticsearch envoyé")
        print("ℹ️  La webapp va indexer les clubs automatiquement")
        
        # Attendre que l'indexation soit complétée (max 5 minutes)
        max_wait = 300
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_doc = db.initialization_status.find_one({})
            if status_doc:
                es_status = status_doc.get("steps", {}).get("elasticsearch_indexing", {})
                status = es_status.get("status", "pending")
                progress = es_status.get("progress", 0)
                
                if status == "completed":
                    print(f"✅ Indexation Elasticsearch terminée (100%)")
                    client.close()
                    return True
                elif status == "error":
                    print(f"❌ Erreur lors de l'indexation Elasticsearch")
                    client.close()
                    return False
                elif status == "in_progress":
                    print(f"⏳ Indexation en cours... {progress}%")
            
            time.sleep(5)
        
        print("⚠️ Timeout: l'indexation prend trop de temps")
        client.close()
        return False
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    success = trigger_indexation()
    sys.exit(0 if success else 1)
