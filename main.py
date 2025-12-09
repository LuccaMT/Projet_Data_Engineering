"""
Serveur principal du dashboard Flashscore Football
Lance l'application Dash avec support CSS externe
"""
from dash import Dash
from src.pages import home


# Initialiser l'app Dash
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="Flashscore Football Dashboard"
)

# Configurer le layout depuis la page home
app.layout = home.layout


def run():
    """Lance le serveur Dash"""
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    run()
