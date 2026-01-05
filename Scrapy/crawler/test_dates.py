from datetime import datetime
from fetch_top5_full_season import parse_date_from_list

print(f"Date actuelle: {datetime.now()}")
print(f"Mois actuel: {datetime.now().month}")
print(f"Jour actuel: {datetime.now().day}")
print("\n=== TESTS PAGE CALENDRIER (matchs à venir) ===")
print(f"10.01. 20:00 (upcoming): {parse_date_from_list('10.01. 20:00', is_upcoming=True)}")
print(f"03.01. 20:00 (upcoming): {parse_date_from_list('03.01. 20:00', is_upcoming=True)}")
print(f"25.12. 20:00 (upcoming): {parse_date_from_list('25.12. 20:00', is_upcoming=True)}")
print(f"15.05. 20:00 (upcoming): {parse_date_from_list('15.05. 20:00', is_upcoming=True)}")

print("\n=== TESTS PAGE RESULTATS (matchs terminés) ===")
print(f"03.01. 20:00 (finished): {parse_date_from_list('03.01. 20:00', is_upcoming=False)}")
print(f"25.12. 20:00 (finished): {parse_date_from_list('25.12. 20:00', is_upcoming=False)}")
print(f"15.05. 20:00 (finished): {parse_date_from_list('15.05. 20:00', is_upcoming=False)}")
