"""
Script to synchronize past matches from matches_upcoming to matches_finished.

This script finds matches in matches_upcoming with past dates and moves them
to matches_finished after verifying their final status.
"""

import os
from datetime import date, datetime
from pymongo import MongoClient
import sys
sys.path.insert(0, os.path.dirname(__file__))

def sync_past_upcoming_matches():
    """Find and sync past matches from upcoming to finished collection."""
    
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
    mongo_db = os.getenv('MONGO_DB', 'flashscore')
    
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    db = client[mongo_db]
    
    today_str = date.today().isoformat()
    
    print(f"[sync] Looking for matches in matches_upcoming with target_date < {today_str}")
    
    # Find upcoming matches with past dates
    past_matches = list(db.matches_upcoming.find({
        'target_date': {'$lt': today_str}
    }))
    
    print(f"[sync] Found {len(past_matches)} matches with past dates in upcoming collection")
    
    if not past_matches:
        print("[sync] No matches to sync")
        client.close()
        return
    
    moved_count = 0
    skipped_count = 0
    
    for match in past_matches:
        match_id = match.get('id')
        home = match.get('home')
        away = match.get('away')
        target_date = match.get('target_date')
        
        # Check if already in finished collection
        existing = db.matches_finished.find_one({'id': match_id})
        if existing:
            print(f"[sync] Match {match_id} ({home} vs {away}) already in finished, removing from upcoming")
            db.matches_upcoming.delete_one({'_id': match['_id']})
            skipped_count += 1
            continue
        
        # For past matches without scores, we assume they were cancelled/postponed
        # Set appropriate status
        if match.get('home_score') is None or match.get('away_score') is None:
            # Match has passed but no scores - likely postponed or cancelled
            print(f"[sync] Match {match_id} ({home} vs {away} on {target_date}) - no scores, skipping (likely postponed)")
            skipped_count += 1
            continue
        
        # Match has scores - move to finished
        match['status'] = 'finished'
        match['status_code'] = 100
        match['collection'] = 'matches_finished'
        match['scraped_at'] = datetime.utcnow()
        
        # Insert into finished
        db.matches_finished.insert_one(match)
        # Remove from upcoming
        db.matches_upcoming.delete_one({'_id': match['_id']})
        
        print(f"[sync] Moved {match_id} ({home} vs {away} on {target_date}) to finished")
        moved_count += 1
    
    print(f"\n[sync] Summary:")
    print(f"  - Moved to finished: {moved_count}")
    print(f"  - Skipped (no scores/already exists): {skipped_count}")
    print(f"  - Total processed: {len(past_matches)}")
    
    client.close()

if __name__ == '__main__':
    sync_past_upcoming_matches()
