"""
Configuration Scrapy pour le projet Flashscore
"""
import os

# Scrapy settings for flashscore project

BOT_NAME = 'flashscore'

SPIDER_MODULES = ['crawler']
NEWSPIDER_MODULE = 'crawler'

# Respecter robots.txt (désactivé pour les endpoints feed)
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy
CONCURRENT_REQUESTS = 16

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 0.5

# Disable cookies (enabled by default)
COOKIES_ENABLED = False

# Disable Telnet Console (enabled by default)
TELNETCONSOLE_ENABLED = False

# Override the default request headers
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'fr',
}

# Enable or disable spider middlewares
# SPIDER_MIDDLEWARES = {
#    'crawler.middlewares.FlashscoreSpiderMiddleware': 543,
# }

# Enable or disable downloader middlewares
# DOWNLOADER_MIDDLEWARES = {
#    'crawler.middlewares.FlashscoreDownloaderMiddleware': 543,
# }

# Enable or disable extensions
# EXTENSIONS = {
#    'scrapy.extensions.telnet.TelnetConsole': None,
# }

# Configure item pipelines
ITEM_PIPELINES = {
    'crawler.pipelines.MongoDBBulkPipeline': 300,  # Utiliser la version bulk pour de meilleures performances
}

# Configuration MongoDB
# Important: Ces valeurs sont lues au démarrage et peuvent être surchargées par les variables d'environnement
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB = os.getenv('MONGO_DB', 'flashscore')
MONGODB_BULK_SIZE = 100  # Nombre d'items à accumuler avant écriture bulk

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.5
AUTOTHROTTLE_MAX_DELAY = 3
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = '2.7'
TWISTED_REACTOR = 'twisted.internet.asyncioreactor.AsyncioSelectorReactor'
FEED_EXPORT_ENCODING = 'utf-8'

# Log level
LOG_LEVEL = 'INFO'
