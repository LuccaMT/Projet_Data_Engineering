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
from pages import cups, home, league_detail, leagues, loading


def is_initialized(
    mongo_uri: str | None = None,
    mongo_db: str | None = None,
    required_step: str = "top5_leagues",
) -> bool:
    """Vérifie si l'initialisation du projet est terminée.

    L'accès à l'application (hors page /loading) est autorisé uniquement si l'étape
    `required_step` est marquée comme `completed` dans `initialization_status`.

    Args:
        mongo_uri (str | None): URI MongoDB. Si None, utilise la variable d'env `MONGO_URI`.
        mongo_db (str | None): Nom de la base. Si None, utilise la variable d'env `MONGO_DB`.
        required_step (str): Nom de l'étape à vérifier dans le tracker.

    Returns:
        bool: True si l'initialisation est terminée, False sinon.
    """
    client = None
    try:
        mongo_uri = mongo_uri or os.getenv("MONGO_URI", "mongodb://admin:admin123@mongodb:27017/")
        mongo_db = mongo_db or os.getenv("MONGO_DB", "flashscore")

        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        db = client[mongo_db]

        status = db.initialization_status.find_one({}) or {}
        steps = status.get("steps", {})
        step = steps.get(required_step, {})
        return step.get("status") == "completed"
    except Exception as exc:
        # On reste permissif ici: si MongoDB n'est pas joignable, on bloque l'accès
        print(f"Erreur is_initialized: {exc}")
        return False
    finally:
        if client is not None:
            client.close()


# Initialiser l'app Dash
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="Flashscore Football Dashboard"
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
    return home.layout


def run() -> None:
    """Démarre l'application Dash."""
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    run()
