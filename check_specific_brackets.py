from pymongo import MongoClient
import json

client = MongoClient('mongodb://admin:admin123@mongodb:27017/')
db = client['flashscore']

# Tester plusieurs coupes
test_leagues = [
    "FRANCE: Coupe De France",
    "ENGLAND: FA Cup",
    "SPAIN: Copa del Rey",
    "EUROPE: UEFA Champions League"
]

for league in test_leagues:
    print(f"\n{'='*60}")
    print(f"🏆 {league}")
    print('='*60)
    bracket = db['cup_brackets'].find_one({"league": league})
    if bracket:
        rounds = bracket.get('rounds', [])
        print(f"Nombre de tours: {len(rounds)}")
        if rounds:
            print(f"Premier tour:")
            print(f"  - round_name: {rounds[0].get('round_name', 'N/A')}")
            print(f"  - matches: {len(rounds[0].get('matches', []))}")
    else:
        print("❌ Pas de bracket trouvé")
