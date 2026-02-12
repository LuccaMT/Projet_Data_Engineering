"""
MongoDB connection and query management module for Flashscore Dashboard.

This module provides a singleton class to interact with the MongoDB database
containing football matches and league standings.
"""

# Standard library
import os
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

# Third-party
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from elasticsearch import Elasticsearch


class MongoDBConnection:
    """
    MongoDB connection and database operations management class.
    
    This class handles the MongoDB connection and provides methods to retrieve
    matches (upcoming and finished), standings, and statistics.
    
    Attributes:
        mongo_uri (str): MongoDB connection URI (from environment variable).
        mongo_db (str): Database name (from environment variable).
        client (MongoClient): MongoDB client.
        db (Database): MongoDB database instance.
    """
    
    def __init__(self):
        """Initialise la connexion avec les paramètres d'environnement."""
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
        self.mongo_db = os.getenv('MONGO_DB', 'flashscore')
        self.client = None
        self.db = None
        
        # Connexion Elasticsearch
        self.es_host = os.getenv('ELASTICSEARCH_HOST', 'http://localhost:9200')
        self.es_client = None
        
    def connect(self) -> bool:
        """
        Establish MongoDB connection with availability check.
        
        Returns:
            bool: True if connection is successfully established, False otherwise.
            
        Note:
            Timeouts are configured to 5 seconds to avoid blocking.
        """
        try:
            self.client = MongoClient(
                self.mongo_uri,
                serverSelectionTimeoutMS=5000,  # Timeout de 5 secondes
                connectTimeoutMS=5000
            )
            self.client.admin.command('ping')
            self.db = self.client[self.mongo_db]
            
            # Connexion à Elasticsearch (retry si non connecté)
            if self.es_client is None:
                try:
                    self.es_client = Elasticsearch([self.es_host], request_timeout=5)
                    if self.es_client.ping():
                        print("✅ Elasticsearch connecté")
                    else:
                        print("⚠️ Elasticsearch ping échoué")
                        self.es_client = None
                except Exception as es_error:
                    print(f"Elasticsearch non disponible: {es_error}")
                    # MongoDB peut fonctionner sans Elasticsearch
            
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"Erreur de connexion MongoDB: {e}")
            return False
        except Exception as e:
            print(f"Erreur inattendue lors de la connexion: {e}")
            return False
    
    def close(self) -> None:
        """
        Ferme la connexion MongoDB et libère les ressources.
        
        Note:
            Met à None les attributs client et db après fermeture.
        """
        if self.client:
            self.client.close()
            self.client = None
            self.db = None
        if self.es_client:
            self.es_client.close()
            self.es_client = None
    
    def get_upcoming_matches(self, target_date: Optional[str] = None) -> List[Dict]:
        """
        Récupère les matches à venir depuis la collection matches_upcoming.
        
        Args:
            target_date (Optional[str]): Date cible au format ISO (YYYY-MM-DD).
                                        Si None, récupère tous les matches à venir.
        
        Returns:
            List[Dict]: Liste de dictionnaires contenant les données des matches.
                       Chaque dictionnaire contient: league, home, away, score, status, etc.
                       Retourne une liste vide en cas d'erreur ou si aucun match trouvé.
        
        Note:
            Les matches sont triés par start_timestamp décroissant.
            Le champ '_id' MongoDB est supprimé des résultats.
        """
        if self.db is None:
            if not self.connect():
                return []
        
        try:
            collection = self.db.matches_upcoming
            
            query = {}
            if target_date:
                query['target_date'] = target_date
            
            matches = list(collection.find(query).sort('start_timestamp', -1))
            
            for match in matches:
                if '_id' in match:
                    del match['_id']
            
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération des matchs à venir: {e}")
            return []

    def get_league_upcoming_matches(self, league: str) -> List[Dict]:
        """Récupère les matches à venir pour une ligue.

        Args:
            league (str): Nom exact de la ligue (ex: "FRANCE: Ligue 1").

        Returns:
            List[Dict]: Matches triés par start_timestamp croissant.
        """
        if not league:
            return []

        if self.db is None:
            if not self.connect():
                return []

        try:
            matches = list(
                self.db.matches_upcoming.find({"league": league}).sort("start_timestamp", 1)
            )
            for match in matches:
                if "_id" in match:
                    del match["_id"]
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération des matchs à venir pour {league}: {e}")
            return []

    def get_finished_matches(
        self,
        target_date: Optional[str] = None,
        month: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """Récupère les matches terminés selon un filtre de période.

        Args:
            target_date (Optional[str]): Date ISO (YYYY-MM-DD) exacte.
            month (Optional[str]): Mois au format YYYY-MM (filtre par préfixe).
            start_date (Optional[str]): Date ISO de début (>=).
            end_date (Optional[str]): Date ISO de fin (<=).

        Returns:
            List[Dict]: Matches terminés triés par start_timestamp décroissant.

        Note:
            Le champ '_id' MongoDB est supprimé des résultats.
        """
        if self.db is None:
            if not self.connect():
                return []
        
        try:
            collection = self.db.matches_finished
            
            query = {}
            
            if target_date:
                query['target_date'] = target_date
            elif month:
                query['target_date'] = {'$regex': f'^{month}'}
            elif start_date and end_date:
                query['target_date'] = {'$gte': start_date, '$lte': end_date}
            elif start_date:
                query['target_date'] = {'$gte': start_date}
            elif end_date:
                query['target_date'] = {'$lte': end_date}
            
            matches = list(collection.find(query).sort('start_timestamp', -1))
            
            for match in matches:
                if '_id' in match:
                    del match['_id']
            
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération des matchs terminés: {e}")
            return []

    def get_league_finished_matches(self, league: str) -> List[Dict]:
        """Récupère les matches terminés pour une ligue.

        Args:
            league (str): Nom exact de la ligue.

        Returns:
            List[Dict]: Matches triés par start_timestamp croissant.
        """
        if not league:
            return []

        if self.db is None:
            if not self.connect():
                return []

        try:
            matches = list(
                self.db.matches_finished.find({"league": league}).sort("start_timestamp", 1)
            )
            for match in matches:
                if "_id" in match:
                    del match["_id"]
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération des matchs terminés pour {league}: {e}")
            return []

    def get_league_recent_finished(self, league: str, since_date: Optional[str] = None, days: int = 9999) -> List[Dict]:
        """Récupère les derniers matches terminés d'une ligue.

        Args:
            league (str): Nom exact de la ligue.
            since_date (Optional[str]): Date ISO minimale (>=). Si None, calcule via `days`.
            days (int): Fenêtre en jours si `since_date` est None.

        Returns:
            List[Dict]: Matches triés par start_timestamp croissant.
        """
        if not league:
            return []

        if self.db is None:
            if not self.connect():
                return []

        try:
            query: Dict = {"league": league}
            if since_date:
                query["target_date"] = {"$gte": since_date}
            else:
                days = max(1, days)
                cutoff = (date.today() - timedelta(days=days)).isoformat()
                query["target_date"] = {"$gte": cutoff}

            matches = list(
                self.db.matches_finished.find(query).sort("start_timestamp", 1)
            )
            for match in matches:
                if "_id" in match:
                    del match["_id"]
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération des matchs terminés récents pour {league}: {e}")
            return []

    def get_matches_count(self, collection_name: str) -> int:
        """Compte le nombre de documents dans une collection.

        Args:
            collection_name (str): Nom de la collection (ex: "matches_upcoming").

        Returns:
            int: Nombre de documents, 0 en cas d'erreur.
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
        """Retourne la date/heure du dernier scraping pour une collection.

        Args:
            collection_name (str): Nom de la collection.

        Returns:
            Optional[str]: Timestamp ISO 8601 si trouvé, sinon None.
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
    
    def get_all_leagues(self) -> List[str]:
        """Récupère la liste de toutes les ligues connues (upcoming + finished).
        
        Exclut 'Unknown League' de la liste des ligues affichées.

        Returns:
            List[str]: Ligues distinctes triées (sans Unknown League).
        """
        if self.db is None:
            if not self.connect():
                return []
        
        try:
            leagues_upcoming = self.db['matches_upcoming'].distinct('league')
            leagues_finished = self.db['matches_finished'].distinct('league')
            
            all_leagues = list(set(leagues_upcoming + leagues_finished))
            
            # Exclure "Unknown League" de la liste
            all_leagues = [league for league in all_leagues if league != "Unknown League"]
            
            all_leagues.sort()
            
            return all_leagues
        except Exception as e:
            print(f"Erreur lors de la récupération des ligues: {e}")
            return []

    def get_league_standings(self, league_name: str) -> Optional[Dict]:
        """Récupère le classement (standings) d'une ligue.

        Args:
            league_name (str): Nom exact de la ligue.

        Returns:
            Optional[Dict]: Document standings sans `_id`, ou None si absent/erreur.
        """
        if not league_name:
            return None

        if self.db is None:
            if not self.connect():
                return None

        try:
            standing = self.db.standings.find_one({"league_name": league_name})
            if standing and "_id" in standing:
                del standing["_id"]
            return standing
        except Exception as e:
            print(f"Erreur lors de la récupération du classement pour {league_name}: {e}")
            return None

    def get_cup_brackets(self, league_name: str) -> Optional[Dict]:
        """Récupère les brackets d'une coupe.

        Args:
            league_name (str): Nom exact de la coupe.

        Returns:
            Optional[Dict]: Document cup_brackets sans `_id`, ou None si absent/erreur.
        """
        if not league_name:
            return None

        if self.db is None:
            if not self.connect():
                return None

        try:
            bracket = self.db.cup_brackets.find_one({"league": league_name})
            if bracket and "_id" in bracket:
                del bracket["_id"]
            return bracket
        except Exception as e:
            print(f"Erreur lors de la récupération des brackets pour {league_name}: {e}")
            return None

    def get_all_standings(self) -> List[Dict]:
        """Récupère tous les classements disponibles.

        Returns:
            List[Dict]: Liste des documents standings sans `_id`.
        """
        if self.db is None:
            if not self.connect():
                return []

        try:
            standings = list(self.db.standings.find({}))
            for standing in standings:
                if "_id" in standing:
                    del standing["_id"]
            return standings
        except Exception as e:
            print(f"Erreur lors de la récupération des classements: {e}")
            return []

    # ========== CLUB SEARCH & STATISTICS ==========
    
    def search_clubs(self, query: str, size: int = 10) -> List[Dict]:
        """Recherche des clubs par nom avec fuzzy matching via Elasticsearch.
        
        Args:
            query (str): Terme de recherche (nom du club).
            size (int): Nombre maximum de résultats à retourner.
            
        Returns:
            List[Dict]: Liste des clubs correspondants avec leurs statistiques.
        """
        if not query or not query.strip():
            return []
        
        if self.es_client is None:
            # Tenter de se connecter automatiquement si ES n'est pas encore initialisé
            self.connect()
        
        if self.es_client is None:
            print("Elasticsearch non connecté")
            return []
        
        try:
            body = {
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "name.suggest"],
                        "fuzziness": "AUTO"
                    }
                },
                "size": size
            }
            
            results = self.es_client.search(index="clubs", body=body)
            clubs = []
            
            for hit in results['hits']['hits']:
                club_data = hit['_source']
                club_data['_score'] = hit['_score']  # Score de pertinence
                clubs.append(club_data)
            
            return clubs
        except Exception as e:
            print(f"Erreur lors de la recherche de clubs: {e}")
            return []
    
    def get_club_by_name(self, club_name: str) -> Optional[Dict]:
        """Récupère les statistiques complètes d'un club par son nom exact.
        
        Args:
            club_name (str): Nom exact du club.
            
        Returns:
            Optional[Dict]: Statistiques du club ou None si non trouvé.
        """
        if not club_name:
            return None
        
        if self.es_client is None:
            # Tenter de se connecter automatiquement si ES n'est pas encore initialisé
            self.connect()
        
        if self.es_client is None:
            print("Elasticsearch non connecté")
            return None
        
        club_name = club_name.strip()
        if not club_name:
            return None
        
        try:
            result = self.es_client.get(index="clubs", id=club_name)
            return result['_source']
        except Exception as e:
            print(f"Club {club_name} non trouvé: {e}")
            return None

    @staticmethod
    def _normalize_club_name(name: str) -> str:
        """Normalise un nom de club pour comparaison souple."""
        return " ".join(name.strip().split()).casefold()

    def resolve_club(self, club_name: str) -> Optional[Dict]:
        """Résout un nom de club vers un document indexé (exact ou fuzzy).

        Tente d'abord un match exact, puis fallback sur une recherche fuzzy
        et retourne le meilleur candidat.
        """
        if not club_name or not club_name.strip():
            return None
        
        cleaned_name = " ".join(club_name.strip().split())
        
        # 1) Match exact
        club = self.get_club_by_name(cleaned_name)
        if club:
            return club
        
        # 2) Fallback fuzzy via Elasticsearch
        candidates = self.search_clubs(cleaned_name, size=5)
        if not candidates:
            return None
        
        normalized_input = self._normalize_club_name(cleaned_name)
        for candidate in candidates:
            candidate_name = candidate.get("name", "")
            if candidate_name and self._normalize_club_name(candidate_name) == normalized_input:
                return candidate
        
        # Sinon retourner le meilleur résultat
        return candidates[0]
    
    def get_club_matches_history(self, club_name: str, limit: int = 20) -> List[Dict]:
        """Récupère l'historique des matchs d'un club depuis MongoDB.
        
        Args:
            club_name (str): Nom du club.
            limit (int): Nombre maximum de matchs à retourner.
            
        Returns:
            List[Dict]: Liste des matchs (les plus récents en premier).
        """
        if not club_name:
            return []
        
        if self.db is None:
            if not self.connect():
                return []
        
        try:
            matches = list(
                self.db.matches_finished.find({
                    "$or": [
                        {"home": club_name},
                        {"away": club_name}
                    ],
                    "status_code": {"$in": [100, "100"]},
                    "home_score": {"$exists": True, "$ne": None},
                    "away_score": {"$exists": True, "$ne": None}
                }).sort("start_timestamp", -1).limit(limit)
            )
            
            for match in matches:
                if '_id' in match:
                    del match['_id']
            
            return matches
        except Exception as e:
            print(f"Erreur lors de la récupération de l'historique de {club_name}: {e}")
            return []
    
    def compare_clubs(self, club1_name: str, club2_name: str) -> Optional[Dict]:
        """Compare deux clubs et retourne leurs statistiques côte à côte.
        
        Args:
            club1_name (str): Nom du premier club.
            club2_name (str): Nom du second club.
            
        Returns:
            Optional[Dict]: Dictionnaire avec les stats des deux clubs et leur comparaison.
        """
        club1 = self.resolve_club(club1_name)
        club2 = self.resolve_club(club2_name)
        
        if not club1 or not club2:
            return None
        
        # Normaliser les noms (utile si fuzzy match)
        club1_name = club1.get("name", club1_name)
        club2_name = club2.get("name", club2_name)
        
        # Vérifier s'ils ont joué l'un contre l'autre
        head_to_head = []
        if self.db is not None:
            try:
                h2h_matches = list(
                    self.db.matches_finished.find({
                        "$or": [
                            {"home": club1_name, "away": club2_name},
                            {"home": club2_name, "away": club1_name}
                        ],
                        "status_code": {"$in": [100, "100"]},
                        "home_score": {"$exists": True, "$ne": None}
                    }).sort("first_created", -1).limit(10)
                )
                
                for match in h2h_matches:
                    if '_id' in match:
                        del match['_id']
                    head_to_head.append(match)
            except Exception as e:
                print(f"Erreur lors de la récupération des confrontations directes: {e}")
        
        return {
            "club1": club1,
            "club2": club2,
            "head_to_head": head_to_head
        }


_db_connection = None


def get_db_connection() -> MongoDBConnection:
    global _db_connection
    if _db_connection is None:
        _db_connection = MongoDBConnection()
    return _db_connection
