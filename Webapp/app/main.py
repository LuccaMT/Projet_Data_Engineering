"""
Serveur principal du dashboard Flashscore Football
Lance l'application Dash avec support CSS externe et routing multi-pages
"""
from dash import Dash, html, dcc, Input, Output
from pages import home, leagues


# Initialiser l'app Dash
app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="Flashscore Football Dashboard"
)

# Configurer le layout principal avec routing
app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


# Callback pour gérer le routing
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    """
    Affiche la page correspondant au chemin URL
    """
    if pathname == '/leagues':
        return leagues.layout
    else:  # Par défaut, afficher la page home
        return home.layout


def run():
    """Lance le serveur Dash"""
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    run()
