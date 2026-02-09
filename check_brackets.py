from pymongo import MongoClient

client = MongoClient('mongodb://admin:admin123@mongodb:27017/')
db = client['flashscore']
brackets = list(db['cup_brackets'].find())

print(f'Nombre de brackets: {len(brackets)}')
for b in brackets:
    league = b.get('league', 'N/A')
    rounds = b.get('rounds', [])
    print(f'- {league}: {len(rounds)} tours')
