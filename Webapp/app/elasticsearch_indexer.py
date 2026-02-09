"""
Service d'indexation automatique des clubs dans Elasticsearch
Lance au démarrage du webapp et met à jour le statut dans MongoDB
"""
import os
import time
import threading
from pymongo import MongoClient
from elasticsearch import Elasticsearch
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AutoClubIndexer:
    """Indexe automatiquement les clubs au démarrage"""
    
    def __init__(self):
        # Connexion MongoDB
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://admin:admin123@mongodb:27017/')
        self.mongo_client = MongoClient(mongo_uri)
        self.db = self.mongo_client["flashscore"]
        
        # Connexion Elasticsearch
        es_host = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
        self.es = Elasticsearch([es_host])
        
        self.index_name = "clubs"
    
    def update_status(self, status: str, progress: int, message: str = ""):
        """Met à jour le statut de l'indexation dans MongoDB"""
        try:
            self.db.initialization_status.update_one(
                {},
                {
                    "$set": {
                        f"steps.elasticsearch_indexing.status": status,
                        f"steps.elasticsearch_indexing.progress": progress,
                        "current_step": message or f"Indexation Elasticsearch: {progress}%"
                    }
                },
                upsert=True
            )
            logger.info(f"Elasticsearch indexing: {status} - {progress}% - {message}")
        except Exception as e:
            logger.error(f"Erreur mise à jour statut: {e}")
    
    def check_if_already_indexed(self) -> bool:
        """Vérifie si l'indexation a déjà été faite"""
        try:
            if not self.es.indices.exists(index=self.index_name):
                return False
            
            # Vérifier s'il y a des documents
            count = self.es.count(index=self.index_name)
            doc_count = count.get('count', 0)
            
            logger.info(f"Index existe avec {doc_count} clubs")
            return doc_count > 0
        except Exception as e:
            logger.error(f"Erreur vérification index: {e}")
            return False
    
    def wait_for_services(self):
        """Attend que MongoDB et Elasticsearch soient prêts"""
        max_retries = 60
        retry_delay = 3
        
        # Attendre MongoDB
        for i in range(max_retries):
            try:
                self.mongo_client.admin.command('ping')
                logger.info("✅ MongoDB prêt")
                break
            except Exception as e:
                if i == max_retries - 1:
                    logger.error(f"MongoDB non disponible après {max_retries} tentatives")
                    return False
                if i % 10 == 0:
                    logger.info(f"Attente MongoDB... ({i+1}/{max_retries})")
                time.sleep(retry_delay)
        
        # Attendre Elasticsearch
        for i in range(max_retries):
            try:
                if self.es.ping():
                    logger.info("✅ Elasticsearch prêt")
                    return True
            except Exception as e:
                if i == max_retries - 1:
                    logger.error(f"Elasticsearch non disponible après {max_retries} tentatives")
                    return False
                if i % 10 == 0:
                    logger.info(f"Attente Elasticsearch... ({i+1}/{max_retries})")
                time.sleep(retry_delay)
        
        return False
    
    def create_index(self):
        """Crée l'index Elasticsearch"""
        try:
            if self.es.indices.exists(index=self.index_name):
                logger.info(f"Index {self.index_name} existe déjà")
                return True
            
            mappings = {
                "mappings": {
                    "properties": {
                        "name": {
                            "type": "text",
                            "fields": {
                                "keyword": {"type": "keyword"},
                                "suggest": {"type": "search_as_you_type"}
                            }
                        },
                        "logo": {"type": "keyword"},
                        "leagues": {"type": "keyword"},
                        "total_matches": {"type": "integer"},
                        "wins": {"type": "integer"},
                        "draws": {"type": "integer"},
                        "losses": {"type": "integer"},
                        "goals_for": {"type": "integer"},
                        "goals_against": {"type": "integer"},
                        "goal_difference": {"type": "integer"},
                        "win_rate": {"type": "float"},
                        "recent_form": {"type": "keyword"}
                    }
                }
            }
            
            self.es.indices.create(index=self.index_name, body=mappings)
            logger.info(f"✅ Index {self.index_name} créé")
            return True
        except Exception as e:
            logger.error(f"Erreur création index: {e}")
            return False
    
    def aggregate_and_index_clubs(self):
        """Agrège et indexe tous les clubs"""
        try:
            self.update_status("in_progress", 10, "Récupération des matchs...")
            
            clubs = defaultdict(lambda: {
                'name': '',
                'logo': '',
                'leagues': set(),
                'total_matches': 0,
                'wins': 0,
                'draws': 0,
                'losses': 0,
                'goals_for': 0,
                'goals_against': 0,
                'matches': []
            })
            
            # Récupérer tous les matchs terminés
            matches = list(self.db.matches_finished.find({
                "status_code": {"$in": [100, "100"]},
                "home_score": {"$exists": True, "$ne": None},
                "away_score": {"$exists": True, "$ne": None}
            }))
            
            total_matches = len(matches)
            logger.info(f"📊 {total_matches} matchs à traiter")
            
            self.update_status("in_progress", 30, f"Traitement de {total_matches} matchs...")
            
            # Traiter chaque match
            for match in matches:
                home = match.get('home')
                away = match.get('away')
                home_score = match.get('home_score')
                away_score = match.get('away_score')
                league = match.get('league', 'Unknown')
                home_logo = match.get('home_logo', '')
                away_logo = match.get('away_logo', '')
                
                if not all([home, away, home_score is not None, away_score is not None]):
                    continue
                
                # Mise à jour stats équipe domicile
                clubs[home]['name'] = home
                clubs[home]['logo'] = home_logo
                clubs[home]['leagues'].add(league)
                clubs[home]['total_matches'] += 1
                clubs[home]['goals_for'] += home_score
                clubs[home]['goals_against'] += away_score
                
                if home_score > away_score:
                    clubs[home]['wins'] += 1
                elif home_score == away_score:
                    clubs[home]['draws'] += 1
                else:
                    clubs[home]['losses'] += 1
                
                # Mise à jour stats équipe extérieur
                clubs[away]['name'] = away
                clubs[away]['logo'] = away_logo
                clubs[away]['leagues'].add(league)
                clubs[away]['total_matches'] += 1
                clubs[away]['goals_for'] += away_score
                clubs[away]['goals_against'] += home_score
                
                if away_score > home_score:
                    clubs[away]['wins'] += 1
                elif away_score == home_score:
                    clubs[away]['draws'] += 1
                else:
                    clubs[away]['losses'] += 1
            
            self.update_status("in_progress", 60, f"Indexation de {len(clubs)} clubs...")
            
            # Indexer chaque club
            indexed_count = 0
            for club_name, club_data in clubs.items():
                try:
                    # Calculer les statistiques finales
                    total = club_data['total_matches']
                    wins = club_data['wins']
                    win_rate = (wins / total * 100) if total > 0 else 0
                    goal_diff = club_data['goals_for'] - club_data['goals_against']
                    
                    doc = {
                        "name": club_name,
                        "logo": club_data['logo'],
                        "leagues": list(club_data['leagues']),
                        "total_matches": total,
                        "wins": wins,
                        "draws": club_data['draws'],
                        "losses": club_data['losses'],
                        "goals_for": club_data['goals_for'],
                        "goals_against": club_data['goals_against'],
                        "goal_difference": goal_diff,
                        "win_rate": round(win_rate, 2),
                        "recent_form": ""
                    }
                    
                    self.es.index(index=self.index_name, id=club_name, body=doc)
                    indexed_count += 1
                    
                    # Mise à jour progressive
                    if indexed_count % 100 == 0:
                        progress = 60 + int((indexed_count / len(clubs)) * 35)
                        self.update_status("in_progress", progress, f"Indexé {indexed_count}/{len(clubs)} clubs")
                
                except Exception as e:
                    logger.error(f"Erreur indexation club {club_name}: {e}")
            
            logger.info(f"✅ {indexed_count} clubs indexés avec succès")
            self.update_status("completed", 100, f"✅ {indexed_count} clubs indexés")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur indexation: {e}")
            self.update_status("error", 0, f"Erreur: {str(e)}")
            return False
    
    def run(self):
        """Lance l'indexation complète"""
        try:
            logger.info("🚀 Démarrage indexation Elasticsearch...")
            self.update_status("in_progress", 0, "Démarrage de l'indexation...")
            
            # Vérifier si déjà indexé
            if self.check_if_already_indexed():
                logger.info("✅ Clubs déjà indexés, skip")
                self.update_status("completed", 100, "✅ Clubs déjà indexés")
                return True
            
            # Attendre les services
            self.update_status("in_progress", 5, "Attente des services...")
            if not self.wait_for_services():
                self.update_status("error", 0, "Services non disponibles")
                return False
            
            # Créer l'index
            self.update_status("in_progress", 8, "Création de l'index...")
            if not self.create_index():
                self.update_status("error", 0, "Erreur création index")
                return False
            
            # Indexer les clubs
            return self.aggregate_and_index_clubs()
            
        except Exception as e:
            logger.error(f"❌ Erreur fatale: {e}")
            self.update_status("error", 0, str(e))
            return False
        finally:
            self.mongo_client.close()


def start_indexing_in_background():
    """Lance l'indexation dans un thread séparé"""
    def run_indexer():
        # Attendre que le webapp et les services démarrent
        logger.info("⏳ Attente de 15 secondes avant indexation...")
        time.sleep(15)
        indexer = AutoClubIndexer()
        indexer.run()
    
    thread = threading.Thread(target=run_indexer, daemon=True)
    thread.start()
    logger.info("🔄 Thread d'indexation Elasticsearch lancé")


if __name__ == "__main__":
    indexer = AutoClubIndexer()
    indexer.run()
