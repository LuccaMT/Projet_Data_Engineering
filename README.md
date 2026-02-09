# Projet Data Engineering - Flashscore Football Dashboard

Application web affichant des données de matchs de football scrapées depuis [Flashscore.fr](https://www.flashscore.fr/), stockées dans MongoDB et visualisées via un dashboard Dash interactif.

## 🚀 Démarrage rapide

```bash
# Une seule commande pour tout lancer !
docker-compose up -d

# Suivre l'initialisation automatique (optionnel)
docker-compose logs -f scrapy

# Accéder au dashboard
# http://localhost:8050
```

**C'est tout !** 🎉 Le projet initialise automatiquement MongoDB et scrappe les données au démarrage.

## 📊 Architecture

- **MongoDB** : Base de données pour stocker les matchs
- **Scrapy** : Scraping automatique des données Flashscore
- **Dash/Plotly** : Dashboard web interactif

## 📖 Documentation complète

- 🚨 **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Guide de dépannage rapide (⭐ À lire en cas de problème)
- 🔧 **[INITIALIZATION_FIX.md](INITIALIZATION_FIX.md)** - Documentation technique de l'amélioration du système d'initialisation
- 📋 **[FIX_SUMMARY.md](FIX_SUMMARY.md)** - Récapitulatif de la correction du problème de page loading
- 📚 **[MONGODB_GUIDE.md](MONGODB_GUIDE.md)** - Commandes de scraping manuel, gestion MongoDB, structure des données

## 🛠️ Développement

```bash
# Voir les logs
docker-compose logs -f webapp
docker-compose logs -f scrapy

# Relancer un service
docker-compose restart scrapy

# Arrêter tout
docker-compose down
```

### 🔧 Scripts utilitaires

```bash
# Vérifier l'état complet du projet
docker exec flashscore-scrapy python /app/check_status.py

# Forcer l'initialisation à "completed" (si bloqué sur la page loading)
docker exec flashscore-scrapy python /app/crawler/force_initialization_complete.py
```

### ⚠️ Résolution de problèmes

**Problème : La page loading s'affiche en boucle**
- **Cause** : Le tracker d'initialisation n'est pas à jour
- **Solution** : Exécuter le script de force completion
  ```bash
  docker exec flashscore-scrapy python /app/crawler/force_initialization_complete.py
  docker-compose restart webapp
  ```

**Problème : Pas de données affichées**
- **Vérification** : Lancer le script de diagnostic
  ```bash
  docker exec flashscore-scrapy python /app/check_status.py
  ```
- **Solution** : Vérifier les logs du scraper
  ```bash
  docker-compose logs scrapy
  ```

## 📁 Structure du projet

```
.
├── Scrapy/
│   ├── crawler/
│   │   ├── fetch_finished.py    # Scraper matchs terminés
│   │   ├── fetch_upcoming.py    # Scraper matchs à venir
│   │   ├── flashscore_feed.py   # Parser de feed Flashscore
│   │   ├── pipelines.py         # Pipeline MongoDB
│   │   └── settings.py          # Configuration Scrapy
│   └── entrypoint.sh            # Script d'initialisation auto
├── Webapp/
│   └── app/
│       ├── database.py          # Module MongoDB
│       ├── main.py              # Serveur Dash
│       └── pages/
│           └── home.py          # Page d'accueil
└── docker-compose.yml           # Configuration Docker
```

## ✨ Fonctionnalités

✅ Scraping automatique au démarrage  
✅ Stockage MongoDB avec gestion des doublons  
✅ Dashboard interactif temps réel  
✅ Filtrage par date/mois  
✅ Statistiques en direct  
✅ Logos des équipes  
✅ Interface responsive  
✅ **Recherche de clubs avec Elasticsearch** 🔍 **NOUVEAU !**  
✅ **Comparaison de clubs avec graphiques** 📊 **NOUVEAU !**  
✅ **Statistiques détaillées par club** 📈 **NOUVEAU !**

## 🔍 Nouvelle fonctionnalité : Recherche de Clubs

Une nouvelle section complète permet de rechercher, analyser et comparer des clubs de football.

### Fonctionnalités de recherche :

- **Recherche intelligente** : Elasticsearch avec fuzzy matching (supporte les fautes de frappe)
- **Statistiques complètes** : Victoires, nuls, défaites, buts, taux de victoire, forme récente
- **Graphiques interactifs** : 
  - Pie chart des résultats
  - Bar chart buts marqués/encaissés
  - Line chart évolution de la forme
  - Radar chart comparatif
- **Comparaison** : Comparez 2 clubs côte à côte avec confrontations directes

### Accès rapide :

```bash
# Déploiement automatique complet (Windows)
.\deploy_club_search.ps1

# OU manuellement
docker-compose up -d --build
docker exec scrapy_flashscore python crawler/club_indexer.py

# Tester l'installation
docker exec scrapy_flashscore python crawler/test_club_search.py
```

### Pages disponibles :

- **`/clubs/search`** - Recherche de clubs
- **`/clubs/detail?name={nom}`** - Détails et statistiques d'un club
- **`/clubs/compare?club1={nom1}&club2={nom2}`** - Comparaison de clubs

📖 **Documentation complète** : [CLUB_SEARCH_FEATURE.md](CLUB_SEARCH_FEATURE.md)
