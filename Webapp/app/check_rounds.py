#!/usr/bin/env python3
"""Check match structure for cup competitions."""
import sys
sys.path.append('/app')
from database import get_db_connection
import json

db = get_db_connection()
if not db.db:
    db.connect()

# Find cup match and show full structure
print("=== FULL MATCH STRUCTURE ===")
match = db.db.matches_upcoming.find_one(
    {"league": "ENGLAND: FA Cup"}
)
if match:
    # Remove _id for readability
    if '_id' in match:
        del match['_id']
    print(json.dumps(match, indent=2, default=str))

# Count all cups
print("\n=== ALL CUPS IN DATABASE ===")
from pages.cups import is_cup
all_leagues = db.db.matches_upcoming.distinct("league")
cups = [l for l in all_leagues if is_cup(l)]
print(f"Total: {len(cups)} cup competitions")

