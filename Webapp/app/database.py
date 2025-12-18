"""
Module de gestion de la connexion MongoDB pour la webapp
"""
import os
from datetime import datetime
from typing import List, Dict, Optional

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError


class MongoDBConnection:
    """Gestionnaire de connexion MongoDB pour la webapp"""
    
    def __init__(self):
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
        self.mongo_db = os.getenv('MONGO_DB', 'flashscore')
        self.client = None
        self.db = None
        
    def connect(self) -> bool:
        """
        Établit la connexion à MongoDB.
        Retourne True si succès, False sinon.
        """
        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,  # Timeout de 5 secondes
                connectTimeoutMS=5000
            )
            # Test de connexion
            self.client.admin.command('ping')
            self.db = self.client[self.mongo_db]
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"Erreur de connexion MongoDB: {e}")
            return False
        except Exception as e:
            print(f"Erreur inattendue lors de la connexion: {e}")
            return False
    
    def close(self):
        """Ferme la connexion MongoDB"""
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
    
    def get_upcoming_matches(self, target_date: Optional[str] = None) -> List[Dict]:
        """
        Récupère les matchs à venir ou en cours.
        
        Args:
            target_date: Date au format YYYY-MM-DD (optionnel)
        
        Returns:
            Liste de dictionnaires contenant les matchs
        """
        if self.db is None:
            if not self.connect():
                return []
        
        try:
            collection = self.db.matches_upcoming
            
            # Construire le filtre
            query = {}
            if target_date:
                query['target_date'] = target_date
            
            # Trier par timestamp de début (les plus récents en premier)
            matches = list(collection.find(query).sort('start_timestamp', -1))
            
            # Supprimer le champ _id MongoDB pour faciliter la sérialisation
            for match in matches:
                if '_id' in match:
                    del match['_id']
            
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération des matchs à venir: {e}")
            return []
    
    def get_finished_matches(
        self,
        target_date: Optional[str] = None,
        month: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        Récupère les matchs terminés selon différents critères.
        
        Args:
            target_date: Date spécifique au format YYYY-MM-DD
            month: Mois au format YYYY-MM
            start_date: Date de début pour une plage (YYYY-MM-DD)
            end_date: Date de fin pour une plage (YYYY-MM-DD)
        
        Returns:
            Liste de dictionnaires contenant les matchs
        """
        if self.db is None:
            if not self.connect():
                return []
        
        try:
            collection = self.db.matches_finished
            
            # Construire le filtre
            query = {}
            
            if target_date:
                # Recherche pour une date spécifique
                query['target_date'] = target_date
            elif month:
                # Recherche pour un mois entier (YYYY-MM)
                query['target_date'] = {'$regex': f'^{month}'}
            elif start_date and end_date:
                # Recherche pour une plage de dates
                query['target_date'] = {'$gte': start_date, '$lte': end_date}
            elif start_date:
                query['target_date'] = {'$gte': start_date}
            elif end_date:
                query['target_date'] = {'$lte': end_date}
            
            # Trier par timestamp de début (les plus récents en premier)
            matches = list(collection.find(query).sort('start_timestamp', -1))
            
            # Supprimer le champ _id MongoDB
            for match in matches:
                if '_id' in match:
                    del match['_id']
            
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération des matchs terminés: {e}")
            return []
    
    def get_matches_count(self, collection_name: str) -> int:
        """
        Retourne le nombre total de matchs dans une collection.
        
        Args:
            collection_name: 'matches_upcoming' ou 'matches_finished'
        
        Returns:
            Nombre de documents
        """
        if self.db is None:
            if not self.connect():
                return 0
        
        try:
            return self.db[collection_name].count_documents({})
        except Exception as e:
            print(f"Erreur lors du comptage: {e}")
            return 0
    
    def get_latest_scrape_time(self, collection_name: str) -> Optional[str]:
        """
        Retourne l'heure du dernier scraping pour une collection.
        
        Args:
            collection_name: 'matches_upcoming' ou 'matches_finished'
        
        Returns:
            Datetime ISO string ou None
        """
        if self.db is None:
            if not self.connect():
                return None
        
        try:
            doc = self.db[collection_name].find_one(
                {},
                {'scraped_at': 1},
                sort=[('scraped_at', -1)]
            )
            if doc and 'scraped_at' in doc:
                return doc['scraped_at'].isoformat() if isinstance(doc['scraped_at'], datetime) else str(doc['scraped_at'])
            return None
        except Exception as e:
            print(f"Erreur lors de la récupération du dernier scrape: {e}")
            return None
    
    def delete_old_upcoming_matches(self, hours: int = 24) -> int:
        """
        Supprime les matchs à venir dont la date de début est dépassée depuis X heures.
        Utile pour nettoyer les données obsolètes.
        
        Args:
            hours: Nombre d'heures avant de considérer un match comme obsolète
        
        Returns:
            Nombre de documents supprimés
        """
        if self.db is None:
            if not self.connect():
                return 0
        
        try:
            from datetime import datetime, timedelta
            cutoff_timestamp = int((datetime.utcnow() - timedelta(hours=hours)).timestamp())
            
            result = self.db.matches_upcoming.delete_many({
                'start_timestamp': {'$lt': cutoff_timestamp}
            })
            return result.deleted_count
        except Exception as e:
            print(f"Erreur lors de la suppression des matchs obsolètes: {e}")
            return 0
    
    def get_all_leagues(self) -> List[str]:
        """
        Récupère toutes les ligues uniques depuis les deux collections.
        
        Returns:
            Liste des noms de ligues triés alphabétiquement
        """
        if self.db is None:
            if not self.connect():
                return []
        
        try:
            # Récupérer toutes les ligues uniques depuis les deux collections
            leagues_upcoming = self.db['matches_upcoming'].distinct('league')
            leagues_finished = self.db['matches_finished'].distinct('league')
            
            # Fusionner et supprimer les doublons
            all_leagues = list(set(leagues_upcoming + leagues_finished))
            all_leagues.sort()
            
            return all_leagues
        except Exception as e:
            print(f"Erreur lors de la récupération des ligues: {e}")
            return []


# Instance globale (singleton pattern)
_db_connection = None


def get_db_connection() -> MongoDBConnection:
    """Retourne l'instance globale de connexion MongoDB"""
    global _db_connection
    if _db_connection is None:
        _db_connection = MongoDBConnection()
    return _db_connection
