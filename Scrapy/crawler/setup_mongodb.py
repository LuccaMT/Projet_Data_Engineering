"""MongoDB initialization (indexes) for project collections.

This script is useful in setup/debug to create required indexes.
"""

import os

from pymongo import MongoClient


def setup_mongodb() -> None:
    """Create necessary MongoDB indexes and display some statistics.

    Returns:
        None
    """
    
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
    mongo_db = os.getenv('MONGO_DB', 'flashscore')
    
    print(f"Connecting to MongoDB: {mongo_uri}")
    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    
    upcoming = db.matches_upcoming
    print("Configuration de la collection 'matches_upcoming'...")
    upcoming.create_index([("id", 1)], unique=True)
    upcoming.create_index([("start_timestamp", -1)])
    upcoming.create_index([("status_code", 1)])
    upcoming.create_index([("scraped_at", -1)])
    print("✅ Indexes created for matches_upcoming")
    
    finished = db.matches_finished
    print("Configuration de la collection 'matches_finished'...")
    finished.create_index([("id", 1), ("target_date", 1)], unique=True)
    finished.create_index([("start_timestamp", -1)])
    finished.create_index([("target_date", -1)])
    finished.create_index([("scraped_at", -1)])
    finished.create_index([("league", 1)])
    finished.create_index([("country", 1)])
    print("✅ Indexes created for matches_finished")
    
    collections = db.list_collection_names()
    print(f"\nCollections dans la base '{mongo_db}': {collections}")
    
    # Afficher le nombre de documents
    print(f"\nNombre de documents:")
    print(f"  - matches_upcoming: {upcoming.count_documents({})}")
    print(f"  - matches_finished: {finished.count_documents({})}")
    
    client.close()
    print("\n✅ MongoDB configuration completed")


if __name__ == "__main__":
    setup_mongodb()
