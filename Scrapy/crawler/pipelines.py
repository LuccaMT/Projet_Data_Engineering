"""Scrapy pipelines for MongoDB persistence.

Two pipelines are provided:
- `MongoDBPipeline`: item-by-item writing (simple, robust)
- `MongoDBBulkPipeline`: batch writing (faster)
"""

from datetime import datetime

from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from scrapy import Spider
from scrapy.exceptions import NotConfigured


class MongoDBPipeline:

    def __init__(self, mongo_uri: str, mongo_db: str):
        """Initialize the MongoDB pipeline.

        Args:
            mongo_uri (str): MongoDB connection URI.
            mongo_db (str): MongoDB database name.
        """
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.client = None
        self.db = None
        
    @classmethod
    def from_crawler(cls, crawler):
        """Build the pipeline from Scrapy config.

        Args:
            crawler: Scrapy instance providing `settings`.

        Returns:
            MongoDBPipeline: Configured instance.

        Raises:
            NotConfigured: If `MONGO_URI` is not defined.
        """
        mongo_uri = crawler.settings.get('MONGO_URI')
        mongo_db = crawler.settings.get('MONGO_DB', 'flashscore')
        
        if not mongo_uri:
            raise NotConfigured('MONGO_URI not configured')
        
        return cls(mongo_uri=mongo_uri, mongo_db=mongo_db)
    
    def open_spider(self, spider: Spider):
        """Open MongoDB connection and create indexes based on the spider.

        Args:
            spider (Spider): Current Scrapy spider.
        """
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        spider.logger.info(f"Connected to MongoDB: {self.mongo_db}")
        
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
        elif spider.name == "flashscore_standings":
            collection = self.db.standings
            collection.create_index([("league_name", 1)], unique=True)
            collection.create_index([("league_id", 1)])
            spider.logger.info("Indexes created for standings")
        elif spider.name == "flashscore_smart_historical":
            # Create indexes for both collections as the spider routes via item["collection"]
            upcoming = self.db.matches_upcoming
            finished = self.db.matches_finished
            upcoming.create_index([("id", 1)], unique=True)
            upcoming.create_index([("start_timestamp", -1)])
            upcoming.create_index([("status_code", 1)])
            finished.create_index([("id", 1), ("target_date", 1)], unique=True)
            finished.create_index([("start_timestamp", -1)])
            finished.create_index([("target_date", -1)])
            spider.logger.info("Indexes created for smart historical spider")
    
    def close_spider(self, spider: Spider):
        """Close the MongoDB connection.

        Args:
            spider (Spider): Current Scrapy spider.
        """
        if self.client:
            self.client.close()
            spider.logger.info("MongoDB connection closed")
    
    def process_item(self, item: dict, spider: Spider) -> dict:
        """Persist an item into the appropriate MongoDB collection.

        Args:
            item (dict): Scrapy item (match/standing) to store.
            spider (Spider): Current spider, used to route the collection.

        Returns:
            dict: Unchanged item (Scrapy convention).
        """
        item['scraped_at'] = datetime.utcnow()
        
        target_collection = None
        if spider.name == "flashscore_upcoming":
            target_collection = "matches_upcoming"
            filter_query = {"id": item["id"]}
        elif spider.name == "flashscore_finished":
            target_collection = "matches_finished"
            filter_query = {"id": item["id"], "target_date": item.get("target_date")}
        elif spider.name == "flashscore_standings":
            target_collection = "standings"
            filter_query = {"league_name": item["league_name"]}
        elif spider.name == "flashscore_smart_historical":
            target_collection = item.get("collection")
            if target_collection == "matches_finished":
                filter_query = {"id": item["id"], "target_date": item.get("target_date")}
            else:
                target_collection = "matches_upcoming"
                filter_query = {"id": item["id"]}
        else:
            spider.logger.warning(f"Unknown spider name: {spider.name}")
            return item

        collection = self.db[target_collection]
        
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

    def __init__(self, mongo_uri: str, mongo_db: str, bulk_size: int = 100):
        """Initialise la pipeline MongoDB en mode batch.

        Args:
            mongo_uri (str): URI de connexion MongoDB.
            mongo_db (str): Nom de la base MongoDB.
            bulk_size (int): Taille du buffer avant flush (default: 100).
        """
        self.mongo_uri = mongo_uri
        self.mongo_db = mongo_db
        self.bulk_size = bulk_size
        self.client = None
        self.db = None
        self.items_buffer = []
        
    @classmethod
    def from_crawler(cls, crawler):
        """Construit la pipeline depuis la config Scrapy.

        Args:
            crawler: Instance Scrapy fournissant `settings`.

        Returns:
            MongoDBBulkPipeline: Instance configurée.

        Raises:
            NotConfigured: Si `MONGO_URI` n'est pas défini.
        """
        mongo_uri = crawler.settings.get('MONGO_URI')
        mongo_db = crawler.settings.get('MONGO_DB', 'flashscore')
        bulk_size = crawler.settings.get('MONGODB_BULK_SIZE', 100)
        
        if not mongo_uri:
            raise NotConfigured('MONGO_URI not configured')
        
        return cls(mongo_uri=mongo_uri, mongo_db=mongo_db, bulk_size=bulk_size)
    
    def open_spider(self, spider: Spider):
        """Ouvre la connexion MongoDB et initialise le buffer.

        Args:
            spider (Spider): Spider Scrapy courant.
        """
        self.client = MongoClient(self.mongo_uri)
        self.db = self.client[self.mongo_db]
        self.items_buffer = []
        spider.logger.info(f"Connected to MongoDB: {self.mongo_db}")
        
        if spider.name == "flashscore_upcoming":
            collection = self.db.matches_upcoming
            collection.create_index([("id", 1)], unique=True)
            collection.create_index([("start_timestamp", -1)])
        elif spider.name == "flashscore_finished":
            collection = self.db.matches_finished
            collection.create_index([("id", 1), ("target_date", 1)], unique=True)
            collection.create_index([("start_timestamp", -1)])
            collection.create_index([("target_date", -1)])
        elif spider.name == "flashscore_smart_historical":
            upcoming = self.db.matches_upcoming
            finished = self.db.matches_finished
            upcoming.create_index([("id", 1)], unique=True)
            upcoming.create_index([("start_timestamp", -1)])
            finished.create_index([("id", 1), ("target_date", 1)], unique=True)
            finished.create_index([("start_timestamp", -1)])
            finished.create_index([("target_date", -1)])
    
    def close_spider(self, spider: Spider):
        """Flush le buffer restant et ferme la connexion.

        Args:
            spider (Spider): Spider Scrapy courant.
        """
        if self.items_buffer:
            self._flush_buffer(spider)
        
        if self.client:
            self.client.close()
            spider.logger.info(f"MongoDB connection closed. Total items processed: {getattr(self, 'total_items', 0)}")
    
    def process_item(self, item: dict, spider: Spider) -> dict:
        """Ajoute l'item au buffer puis flush si nécessaire.

        Args:
            item (dict): Item Scrapy.
            spider (Spider): Spider courant.

        Returns:
            dict: Item inchangé.
        """
        item['scraped_at'] = datetime.utcnow()
        self.items_buffer.append(item)
        
        if len(self.items_buffer) >= self.bulk_size:
            self._flush_buffer(spider)
        
        return item
    
    def _flush_buffer(self, spider: Spider):
        """Écrit le buffer en batch dans MongoDB.

        Args:
            spider (Spider): Spider courant.

        Returns:
            None
        """

        if not self.items_buffer:
            return
        
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
        elif spider.name == "flashscore_smart_historical":
            ops_finished = []
            ops_upcoming = []
            for item in self.items_buffer:
                target = item.get("collection")
                if target == "matches_finished" or (target is None and str(item.get("status_code")) == "3"):
                    ops_finished.append(
                        UpdateOne(
                            {
                                "id": item["id"],
                                "target_date": item.get("target_date")
                            },
                            {"$set": item},
                            upsert=True
                        )
                    )
                else:
                    ops_upcoming.append(
                        UpdateOne(
                            {"id": item["id"]},
                            {"$set": item},
                            upsert=True
                        )
                    )
            if ops_upcoming:
                self.db.matches_upcoming.bulk_write(ops_upcoming, ordered=False)
            if ops_finished:
                self.db.matches_finished.bulk_write(ops_finished, ordered=False)
            self.items_buffer = []
            return
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
        
        self.items_buffer = []
