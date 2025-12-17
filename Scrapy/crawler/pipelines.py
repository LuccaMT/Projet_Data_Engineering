"""
Pipeline MongoDB pour stocker les données scrapées dans MongoDB
"""
import os
from datetime import datetime
from typing import Any

from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from scrapy import Spider
from scrapy.exceptions import NotConfigured


class MongoDBPipeline:
    """
    Pipeline pour stocker les matches dans MongoDB.
    Crée deux collections:
    - matches_upcoming: pour les matches à venir ou en cours
    - matches_finished: pour les matches terminés
    """
    
    def __init__(self, mongo_uri: str, mongo_db: str):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = None
        self.db = None
        
    @classmethod
    def from_crawler(cls, crawler):
        """Initialise le pipeline depuis les settings Scrapy"""
        mongo_uri = crawler.settings.get('MONGO_URI')
        mongo_db = crawler.settings.get('MONGO_DB', 'flashscore')
        
        if not mongo_uri:
            raise NotConfigured('MONGO_URI not configured')
        
        return cls(mongo_uri=mongo_uri, mongo_db=mongo_db)
    
    def open_spider(self, spider: Spider):
        """Ouvre la connexion MongoDB au démarrage du spider"""
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        spider.logger.info(f"Connected to MongoDB: {self.mongo_db}")
        
        # Créer des index pour optimiser les requêtes
        if spider.name == "flashscore_upcoming":
            collection = self.db.matches_upcoming
            collection.create_index([("id", 1)], unique=True)
            collection.create_index([("start_timestamp", -1)])
            collection.create_index([("status_code", 1)])
            spider.logger.info("Indexes created for matches_upcoming")
        elif spider.name == "flashscore_finished":
            collection = self.db.matches_finished
            collection.create_index([("id", 1), ("target_date", 1)], unique=True)
            collection.create_index([("start_timestamp", -1)])
            collection.create_index([("target_date", -1)])
            spider.logger.info("Indexes created for matches_finished")
    
    def close_spider(self, spider: Spider):
        """Ferme la connexion MongoDB à la fin du spider"""
        if self.client:
            self.client.close()
            spider.logger.info("MongoDB connection closed")
    
    def process_item(self, item: dict, spider: Spider) -> dict:
        """
        Traite et stocke chaque match dans la collection appropriée.
        Utilise upsert pour éviter les doublons.
        """
        # Ajouter metadata
        item['scraped_at'] = datetime.utcnow()
        
        # Déterminer la collection selon le spider
        if spider.name == "flashscore_upcoming":
            collection = self.db.matches_upcoming
            # Pour upcoming, on utilise seulement l'ID comme clé unique
            filter_query = {"id": item["id"]}
        elif spider.name == "flashscore_finished":
            collection = self.db.matches_finished
            # Pour finished, on utilise ID + target_date comme clé composite
            filter_query = {
                "id": item["id"],
                "target_date": item.get("target_date")
            }
        else:
            spider.logger.warning(f"Unknown spider name: {spider.name}")
            return item
        
        # Upsert: update si existe, insert sinon
        try:
            collection.update_one(
                filter_query,
                {"$set": item},
                upsert=True
            )
            spider.logger.debug(f"Stored match {item.get('id')} in {collection.name}")
        except Exception as e:
            spider.logger.error(f"Error storing match {item.get('id')}: {e}")
        
        return item


class MongoDBBulkPipeline:
    """
    Version optimisée du pipeline qui fait des insertions en bulk.
    Plus performant pour de grandes quantités de données.
    """
    
    def __init__(self, mongo_uri: str, mongo_db: str, bulk_size: int = 100):
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.bulk_size = bulk_size
        self.client = None
        self.db = None
        self.items_buffer = []
        
    @classmethod
    def from_crawler(cls, crawler):
        mongo_uri = crawler.settings.get('MONGO_URI')
        mongo_db = crawler.settings.get('MONGO_DB', 'flashscore')
        bulk_size = crawler.settings.get('MONGODB_BULK_SIZE', 100)
        
        if not mongo_uri:
            raise NotConfigured('MONGO_URI not configured')
        
        return cls(mongo_uri=mongo_uri, mongo_db=mongo_db, bulk_size=bulk_size)
    
    def open_spider(self, spider: Spider):
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.items_buffer = []
        spider.logger.info(f"Connected to MongoDB: {self.mongo_db}")
        
        # Créer des index
        if spider.name == "flashscore_upcoming":
            collection = self.db.matches_upcoming
            collection.create_index([("id", 1)], unique=True)
            collection.create_index([("start_timestamp", -1)])
        elif spider.name == "flashscore_finished":
            collection = self.db.matches_finished
            collection.create_index([("id", 1), ("target_date", 1)], unique=True)
            collection.create_index([("start_timestamp", -1)])
            collection.create_index([("target_date", -1)])
    
    def close_spider(self, spider: Spider):
        # Vider le buffer restant
        if self.items_buffer:
            self._flush_buffer(spider)
        
        if self.client:
            self.client.close()
            spider.logger.info(f"MongoDB connection closed. Total items processed: {getattr(self, 'total_items', 0)}")
    
    def process_item(self, item: dict, spider: Spider) -> dict:
        item['scraped_at'] = datetime.utcnow()
        self.items_buffer.append(item)
        
        # Flush quand le buffer atteint la taille bulk_size
        if len(self.items_buffer) >= self.bulk_size:
            self._flush_buffer(spider)
        
        return item
    
    def _flush_buffer(self, spider: Spider):
        """Écrit tous les items du buffer en bulk dans MongoDB"""
        if not self.items_buffer:
            return
        
        # Déterminer la collection
        if spider.name == "flashscore_upcoming":
            collection = self.db.matches_upcoming
            operations = [
                UpdateOne(
                    {"id": item["id"]},
                    {"$set": item},
                    upsert=True
                )
                for item in self.items_buffer
            ]
        elif spider.name == "flashscore_finished":
            collection = self.db.matches_finished
            operations = [
                UpdateOne(
                    {
                        "id": item["id"],
                        "target_date": item.get("target_date")
                    },
                    {"$set": item},
                    upsert=True
                )
                for item in self.items_buffer
            ]
        else:
            spider.logger.warning(f"Unknown spider name: {spider.name}")
            self.items_buffer = []
            return
        
        try:
            result = collection.bulk_write(operations, ordered=False)
            total = getattr(self, 'total_items', 0) + len(self.items_buffer)
            setattr(self, 'total_items', total)
            spider.logger.info(
                f"Bulk write completed: {result.upserted_count} inserted, "
                f"{result.modified_count} updated from {len(self.items_buffer)} items"
            )
        except BulkWriteError as e:
            spider.logger.error(f"Bulk write error: {e.details}")
        except Exception as e:
            spider.logger.error(f"Error in bulk write: {e}")
        
        # Vider le buffer
        self.items_buffer = []
