"""Point d'entrée de l'application Dash.

Ce module:
- Initialise l'app Dash
- Route les pages (home / leagues / cups / league)
- Bloque l'accès tant que l'initialisation (scraping Top 5) n'est pas terminée
"""

# Standard library
import os

# Third-party
from dash import Dash, dcc, html
from dash.dependencies import Input, Output
from pymongo import MongoClient

# Local
from pages import cups, home, league_detail, leagues, loading, club_search, club_detail, club_compare


def is_initialized(
    mongo_uri: str | None = None,
    mongo_db: str | None = None,
    required_step: str = "top5_leagues",
) -> bool:
    """Vérifie si l'initialisation du projet est terminée.

    L'accès à l'application est autorisé si:
    1. L'étape `required_step` est marquée comme `completed` dans le tracker, OU
    2. Des données sont déjà présentes dans les collections (fallback intelligent)

    Args:
        mongo_uri (str | None): URI MongoDB. Si None, utilise la variable d'env `MONGO_URI`.
        mongo_db (str | None): Nom de la base. Si None, utilise la variable d'env `MONGO_DB`.
        required_step (str): Nom de l'étape à vérifier dans le tracker.

    Returns:
        bool: True si l'initialisation est terminée ou si des données existent, False sinon.
    """
    client = None
    try:
        mongo_uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/")
        mongo_db = mongo_db or os.getenv("MONGO_DB", "flashscore")

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        db = client[mongo_db]

        # Vérifier d'abord le tracker (méthode principale)
        status = db.initialization_status.find_one({}) or {}
        steps = status.get("steps", {})
        step = steps.get(required_step, {})
        
        if step.get("status") == "completed":
            return True
        
        # Fallback intelligent: vérifier si des données existent déjà
        # Cela évite de bloquer l'utilisateur si le tracker n'est pas à jour
        upcoming_count = db.matches_upcoming.count_documents({})
        finished_count = db.matches_finished.count_documents({})
        standings_count = db.standings.count_documents({})
        
        # Si on a au moins 100 matchs et quelques classements, considérer comme initialisé
        has_sufficient_data = (upcoming_count + finished_count) >= 100 and standings_count >= 1
        
        if has_sufficient_data:
            print(f"[INFO] Fallback: données détectées ({upcoming_count} upcoming, {finished_count} finished, {standings_count} standings)")
            return True
        
        return False
    except Exception as exc:
        # En cas d'erreur, être permissif et bloquer l'accès par sécurité
        print(f"Erreur is_initialized: {exc}")
        return False
    finally:
        if client is not None:
            client.close()


# Initialiser l'app Dash
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="Flashscore Football Dashboard",
    external_stylesheets=[
        "https://cdn.jsdelivr.net/npm/brackets-viewer@2.3.1/dist/brackets-viewer.min.css"
    ],
    external_scripts=[
        "https://cdn.jsdelivr.net/npm/brackets-viewer@2.3.1/dist/brackets-viewer.min.js"
    ]
)

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname: str):
    """Route les pages de l'application.

    Args:
        pathname (str): Chemin courant (ex: "/", "/leagues", "/loading").

    Returns:
        Component: Layout Dash correspondant à la page demandée.
    """
    initialized = is_initialized()

    # Bloquer l'accès tant que le Top 5 n'est pas prêt
    if not initialized and pathname != "/loading":
        return loading.layout()

    if pathname == "/loading":
        if initialized:
            return dcc.Location(pathname="/", id="redirect-home", refresh=True)
        return loading.layout()

    if pathname == "/league":
        return league_detail.layout
    if pathname == "/leagues":
        return leagues.layout
    if pathname == "/cups":
        return cups.layout
    if pathname == "/clubs/search":
        return club_search.layout()
    if pathname and pathname.startswith("/clubs/detail"):
        return club_detail.layout()
    if pathname and pathname.startswith("/clubs/compare"):
        return club_compare.layout()
    return home.layout


def run() -> None:
    """Démarre l'application Dash."""
    # Lancer l'indexation Elasticsearch en arrière-plan
    try:
        from elasticsearch_indexer import start_indexing_in_background
        print("\n🔍 Lancement de l'indexation Elasticsearch en arrière-plan...")
        start_indexing_in_background()
    except Exception as e:
        print(f"⚠️  Avertissement: Impossible de lancer l'indexation Elasticsearch: {e}")
        print("   L'application va démarrer mais la recherche de clubs peut ne pas fonctionner.\n")
    
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    run()
