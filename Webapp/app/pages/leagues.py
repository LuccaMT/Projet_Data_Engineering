"""
Page de sélection et recherche de ligues
"""
from dash import html, dcc, Input, Output, State, callback
import pandas as pd

from database import get_db_connection
from components.navbar import create_navbar


def get_all_leagues():
    """
    Récupère toutes les ligues disponibles depuis MongoDB
    """
    db = get_db_connection()
    
    try:
        # Récupérer toutes les ligues uniques depuis les deux collections
        leagues_upcoming = db.db['matches_upcoming'].distinct('league')
        leagues_finished = db.db['matches_finished'].distinct('league')
        
        # Fusionner et supprimer les doublons
        all_leagues = list(set(leagues_upcoming + leagues_finished))
        all_leagues.sort()
        
        return all_leagues
    except Exception as e:
        print(f"Erreur lors de la récupération des ligues: {e}")
        return []


def create_layout():
    """Crée le layout de la page des ligues"""
    return html.Div(
        className="app-wrapper",
        children=[
            # Header
            html.Div(
                className="header-container",
                children=[
                    html.Div(
                        className="header-content",
                        children=[
                            html.Img(
                                src="/assets/logo.png",
                                className="header-logo",
                                style={
                                    "height": "50px",
                                    "width": "auto",
                                    "maxWidth": "150px",
                                    "objectFit": "contain",
                                    "flexShrink": "0",
                                },
                            ),
                            html.Div(
                                className="header-text",
                                children=[
                                    html.H1("Flashscore Football Dashboard"),
                                    html.P("Données en temps réel via Scrapy"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            
            # Navbar
            create_navbar(current_page="leagues"),
            
            # Main content
            html.Div(
                className="main-content",
                children=[
                    # En-tête de la page
                    html.Div(
                        style={
                            "textAlign": "center",
                            "marginBottom": "40px",
                        },
                        children=[
                            html.H1(
                                "🏆 Sélection de Ligues",
                                style={
                                    "fontSize": "36px",
                                    "fontWeight": "800",
                                    "color": "#1e40af",
                                    "marginBottom": "12px",
                                    "letterSpacing": "-1px",
                                },
                            ),
                            html.P(
                                "Recherchez et sélectionnez vos ligues favorites",
                                style={
                                    "fontSize": "16px",
                                    "color": "#6b7280",
                                    "fontWeight": "500",
                                },
                            ),
                        ],
                    ),
                    
                    # Panneau de recherche
                    html.Div(
                        className="control-panel",
                        children=[
                            html.H3("Recherche de ligues"),
                            
                            # Barre de recherche
                            html.Div(
                                style={"marginBottom": "24px"},
                                children=[
                                    html.Label(
                                        "🔍 Rechercher une ligue",
                                        style={
                                            "marginBottom": "12px",
                                            "display": "block",
                                            "fontWeight": "600",
                                            "fontSize": "15px",
                                        },
                                    ),
                                    html.Div(
                                        style={"position": "relative"},
                                        children=[
                                            dcc.Input(
                                                id="league-search-input",
                                                type="text",
                                                placeholder="Tapez le nom d'une ligue (ex: Premier League, Ligue 1, Champions League...)",
                                                list="leagues-datalist",
                                                autoComplete="off",
                                                style={
                                                    "width": "100%",
                                                    "padding": "14px 20px",
                                                    "border": "2px solid #e5e7eb",
                                                    "borderRadius": "12px",
                                                    "fontSize": "15px",
                                                    "fontFamily": "'Inter', sans-serif",
                                                },
                                                debounce=300,
                                            ),
                                            # Suggestions dropdown
                                            html.Div(
                                                id="league-suggestions",
                                                style={
                                                    "position": "absolute",
                                                    "top": "100%",
                                                    "left": "0",
                                                    "right": "0",
                                                    "backgroundColor": "white",
                                                    "border": "2px solid #e5e7eb",
                                                    "borderTop": "none",
                                                    "borderRadius": "0 0 12px 12px",
                                                    "maxHeight": "300px",
                                                    "overflowY": "auto",
                                                    "display": "none",
                                                    "zIndex": "1000",
                                                    "boxShadow": "0 10px 30px rgba(0, 0, 0, 0.15)",
                                                },
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            
                            # Statistiques
                            html.Div(
                                id="leagues-stats",
                                style={
                                    "backgroundColor": "#f0f9ff",
                                    "padding": "16px 20px",
                                    "borderRadius": "10px",
                                    "border": "2px solid #bfdbfe",
                                    "marginBottom": "20px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "display": "flex",
                                            "alignItems": "center",
                                            "gap": "10px",
                                        },
                                        children=[
                                            html.Span("📊", style={"fontSize": "20px"}),
                                            html.Span(
                                                "Chargement des statistiques...",
                                                id="leagues-stats-text",
                                                style={
                                                    "fontSize": "14px",
                                                    "color": "#1e40af",
                                                    "fontWeight": "600",
                                                },
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    
                    # Liste des ligues
                    html.Div(
                        className="table-container",
                        children=[
                            html.H3("Liste des ligues"),
                            html.Div(
                                id="leagues-list",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(auto-fill, minmax(300px, 1fr))",
                                    "gap": "16px",
                                    "marginTop": "20px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "textAlign": "center",
                                            "padding": "40px",
                                            "color": "#9ca3af",
                                        },
                                        children=["Chargement des ligues..."],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )


# Callbacks
@callback(
    [
        Output("leagues-list", "children"),
        Output("leagues-stats-text", "children"),
        Output("league-suggestions", "children"),
        Output("league-suggestions", "style"),
    ],
    [Input("league-search-input", "value")],
)
def update_leagues_list(search_value):
    """
    Filtre et affiche la liste des ligues selon la recherche
    Affiche aussi les suggestions d'autocomplétion
    """
    all_leagues = get_all_leagues()
    
    # Style de base pour le dropdown de suggestions
    suggestions_style = {
        "position": "absolute",
        "top": "100%",
        "left": "0",
        "right": "0",
        "backgroundColor": "white",
        "border": "2px solid #e5e7eb",
        "borderTop": "none",
        "borderRadius": "0 0 12px 12px",
        "maxHeight": "300px",
        "overflowY": "auto",
        "zIndex": "1000",
        "boxShadow": "0 10px 30px rgba(0, 0, 0, 0.15)",
        "display": "none",
    }
    
    # Filtrer selon la recherche
    if search_value:
        filtered_leagues = [
            league for league in all_leagues
            if search_value.lower() in league.lower()
        ]
        
        # Créer les suggestions (max 10)
        suggestions = []
        if len(filtered_leagues) > 0 and search_value:
            suggestions_style["display"] = "block"
            for league in filtered_leagues[:10]:
                # Mettre en surbrillance la partie recherchée
                idx = league.lower().find(search_value.lower())
                if idx != -1:
                    before = league[:idx]
                    match = league[idx:idx+len(search_value)]
                    after = league[idx+len(search_value):]
                    
                    suggestion_item = html.Div(
                        [
                            html.Span(before),
                            html.Span(match, style={"fontWeight": "700", "color": "#2563eb", "backgroundColor": "#dbeafe"}),
                            html.Span(after),
                        ],
                        className="suggestion-item",
                        style={
                            "padding": "12px 20px",
                            "cursor": "pointer",
                            "transition": "all 0.2s ease",
                            "borderBottom": "1px solid #f3f4f6",
                            "fontSize": "14px",
                        },
                        n_clicks=0,
                    )
                else:
                    suggestion_item = html.Div(
                        league,
                        className="suggestion-item",
                        style={
                            "padding": "12px 20px",
                            "cursor": "pointer",
                            "transition": "all 0.2s ease",
                            "borderBottom": "1px solid #f3f4f6",
                            "fontSize": "14px",
                        },
                        n_clicks=0,
                    )
                suggestions.append(suggestion_item)
        else:
            suggestions = []
    else:
        filtered_leagues = all_leagues
        suggestions = []
    
    # Statistiques
    stats_text = f"{len(filtered_leagues)} ligue(s) trouvée(s) sur {len(all_leagues)} au total"
    
    # Créer les cards pour chaque ligue
    if not filtered_leagues:
        league_cards = [
            html.Div(
                style={
                    "gridColumn": "1 / -1",
                    "textAlign": "center",
                    "padding": "60px 20px",
                    "backgroundColor": "#f9fafb",
                    "borderRadius": "12px",
                    "border": "2px dashed #d1d5db",
                },
                children=[
                    html.Div(
                        "🔍",
                        style={"fontSize": "48px", "marginBottom": "16px", "opacity": "0.5"},
                    ),
                    html.P(
                        "Aucune ligue trouvée",
                        style={
                            "fontSize": "18px",
                            "color": "#6b7280",
                            "fontWeight": "600",
                            "marginBottom": "8px",
                        },
                    ),
                    html.P(
                        "Essayez une autre recherche",
                        style={"fontSize": "14px", "color": "#9ca3af"},
                    ),
                ],
            ),
        ]
    else:
        league_cards = []
        for league in filtered_leagues:
            card = html.Div(
                className="league-card",
                children=[
                    html.Div(
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "gap": "12px",
                            "marginBottom": "12px",
                        },
                        children=[
                            html.Span("🏆", style={"fontSize": "28px"}),
                            html.H4(
                                league,
                                style={
                                    "margin": "0",
                                    "fontSize": "16px",
                                    "fontWeight": "700",
                                    "color": "#1f2937",
                                    "lineHeight": "1.4",
                                },
                            ),
                        ],
                    ),
                    html.Button(
                        "Voir les matchs →",
                        className="league-button",
                        style={
                            "width": "100%",
                            "padding": "8px 16px",
                            "backgroundColor": "#eff6ff",
                            "color": "#2563eb",
                            "border": "2px solid #bfdbfe",
                            "borderRadius": "8px",
                            "fontSize": "13px",
                            "fontWeight": "600",
                            "cursor": "pointer",
                            "transition": "all 0.2s ease",
                        },
                    ),
                ],
            )
            league_cards.append(card)
    
    return league_cards, stats_text, suggestions, suggestions_style


# Layout pour l'export
layout = create_layout()
