"""Analyze league distribution in database."""
from pymongo import MongoClient

client = MongoClient('mongodb://admin:admin123@mongodb:27017/')
db = client['flashscore']

# Count matches per league
result = list(db.matches_upcoming.aggregate([
    {'$group': {'_id': '$league', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}}
]))

print("📊 Répartition des ligues dans matches_upcoming:\n")
for r in result:
    print(f"  {r['_id']}: {r['count']} matchs")

# Count Unknown League
unknown_count = db.matches_upcoming.count_documents({'league': 'Unknown League'})
total_count = db.matches_upcoming.count_documents({})

print(f"\n📈 Stats:")
print(f"  Total matchs: {total_count}")
print(f"  Unknown League: {unknown_count} ({100*unknown_count/total_count:.1f}%)")
print(f"  Ligues connues: {total_count - unknown_count} ({100*(total_count - unknown_count)/total_count:.1f}%)")

client.close()
