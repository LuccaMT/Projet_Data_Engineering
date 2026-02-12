#!/usr/bin/env python3
"""
Scraper simple pour récupérer les brackets des coupes.
Utilise des données statiques pour éviter les problèmes de scraping Flashscore.
"""

import os
import time
from typing import Dict
from pymongo import MongoClient

# Données statiques pour les principaux brackets
STATIC_BRACKETS = {
    "FRANCE: Coupe de France": {
        "rounds": [
            {
                "round_name": "QUARTS DE FINALE",
                "matches": [
                    {"home": "PSG", "away": "Nice", "home_score": None, "away_score": None},
                    {"home": "Rennes", "away": "Lyon", "home_score": None, "away_score": None},
                    {"home": "Marseille", "away": "Strasbourg", "home_score": None, "away_score": None},
                    {"home": "Toulouse", "away": "Nantes", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "DEMI-FINALES",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "FINALE",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
        ]
    },
    "EUROPE: UEFA Champions League": {
        "rounds": [
            {
                "round_name": "QUARTS DE FINALE",
                "matches": [
                    {"home": "Real Madrid", "away": "Chelsea", "home_score": None, "away_score": None},
                    {"home": "Bayern", "away": "Arsenal", "home_score": None, "away_score": None},
                    {"home": "Man City", "away": "Inter", "home_score": None, "away_score": None},
                    {"home": "PSG", "away": "Barcelona", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "DEMI-FINALES",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "FINALE",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
        ]
    },
    "ANGLETERRE: FA Cup": {
        "rounds": [
            {
                "round_name": "QUARTS DE FINALE",
                "matches": [
                    {"home": "Man United", "away": "Liverpool", "home_score": None, "away_score": None},
                    {"home": "Chelsea", "away": "Newcastle", "home_score": None, "away_score": None},
                    {"home": "Man City", "away": "Brighton", "home_score": None, "away_score": None},
                    {"home": "Tottenham", "away": "Wolves", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "DEMI-FINALES",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "FINALE",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
        ]
    },
    "ESPAGNE: Copa del Rey": {
        "rounds": [
            {
                "round_name": "QUARTS DE FINALE",
                "matches": [
                    {"home": "Real Madrid", "away": "Atletico Madrid", "home_score": None, "away_score": None},
                    {"home": "Barcelona", "away": "Athletic Bilbao", "home_score": None, "away_score": None},
                    {"home": "Real Sociedad", "away": "Mallorca", "home_score": None, "away_score": None},
                    {"home": "Valencia", "away": "Osasuna", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "DEMI-FINALES",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
            {
                "round_name": "FINALE",
                "matches": [
                    {"home": "TBD", "away": "TBD", "home_score": None, "away_score": None},
                ]
            },
        ]
    },
}


def save_bracket_to_mongodb(bracket_data: Dict) -> bool:
    """Sauvegarde un bracket dans MongoDB."""
    
    mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
    mongo_db = os.getenv('MONGO_DB', 'flashscore')
    
    try:
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        collection = db.cup_brackets
        
        collection.create_index([("league", 1)], unique=True)
        
        result = collection.update_one(
            {"league": bracket_data["league"]},
            {"$set": bracket_data},
            upsert=True
        )
        
        client.close()
        
        if result.upserted_id:
            print(f"   💾 Nouveau bracket inséré")
        else:
            print(f"   💾 Bracket mis à jour")
        
        return True
    
    except Exception as e:
        print(f"   ❌ Erreur MongoDB: {e}")
        return False


def scrape_all_major_cups():
    """Insère les brackets statiques dans MongoDB."""
    
    print(f"\n{'='*60}")
    print(f"🏆 INSERTION DES BRACKETS STATIQUES")
    print(f"{'='*60}\n")
    
    success_count = 0
    
    for league, rounds_data in STATIC_BRACKETS.items():
        print(f"📋 {league}...")
        
        bracket_data = {
            "league": league,
            "rounds": rounds_data["rounds"],
            "total_rounds": len(rounds_data["rounds"]),
            "total_matches": sum(len(r["matches"]) for r in rounds_data["rounds"]),
            "scraped_at": time.time(),
            "static_data": True,
        }
        
        if save_bracket_to_mongodb(bracket_data):
            success_count += 1
            print(f"   ✅ {bracket_data['total_rounds']} rounds, {bracket_data['total_matches']} matchs\n")
    
    print(f"{'='*60}")
    print(f"✅ {success_count}/{len(STATIC_BRACKETS)} brackets insérés")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    scrape_all_major_cups()
