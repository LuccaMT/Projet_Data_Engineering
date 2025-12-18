"""
Page de sélection et recherche de ligues
"""
from dash import html, dcc, Input, Output, State, callback
import pandas as pd

from database import get_db_connection
from components.navbar import create_navbar


def get_flashscore_countries():
    """
    Extrait les pays uniques depuis les ligues en base de données MongoDB.
    Format des ligues: "COUNTRY: League Name"
    
    Returns:
        Liste des pays uniques triés par ordre alphabétique
    """
    db = get_db_connection()
    leagues = db.get_all_leagues()
    
    # Extraire les pays depuis le format "COUNTRY: League Name"
    countries = set()
    for league in leagues:
        if ":" in league:
            country = league.split(":")[0].strip()
            countries.add(country)
    
    return sorted(list(countries))


def get_all_leagues():
    """
    Récupère toutes les ligues disponibles depuis MongoDB
    """
    db = get_db_connection()
    return db.get_all_leagues()


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
                            html.H3("Filtres"),
                            
                            # Sélecteur de pays
                            html.Div(
                                style={"marginBottom": "24px"},
                                children=[
                                    html.Label(
                                        "🌍 Filtrer par pays",
                                        style={
                                            "marginBottom": "12px",
                                            "display": "block",
                                            "fontWeight": "600",
                                            "fontSize": "15px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="country-selector",
                                        options=[],  # Sera rempli dynamiquement
                                        value=None,
                                        placeholder="Tous les pays",
                                        clearable=True,
                                        style={
                                            "width": "100%",
                                            "fontSize": "15px",
                                        },
                                    ),
                                ],
                            ),
                            
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
                                    dcc.Dropdown(
                                        id="league-search-input",
                                        options=[],  # Sera rempli dynamiquement
                                        value=None,
                                        placeholder="Tapez pour rechercher une ligue...",
                                        clearable=True,
                                        searchable=True,
                                        style={
                                            "width": "100%",
                                            "fontSize": "15px",
                                        },
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
        Output("country-selector", "options"),
        Output("league-search-input", "options"),
        Output("leagues-list", "children"),
        Output("leagues-stats-text", "children"),
    ],
    [
        Input("league-search-input", "value"),
        Input("country-selector", "value"),
    ],
)
def update_leagues_list(search_value, selected_country):
    """
    Filtre et affiche la liste des ligues selon la recherche et le pays
    """
    print(f"[DEBUG] Recherche: {search_value}, Pays: {selected_country}")
    
    all_leagues = get_all_leagues()
    all_countries = get_flashscore_countries()
    
    # Options pour le sélecteur de pays
    country_options = [{"label": country, "value": country} for country in all_countries]
    
    # Filtrer par pays si sélectionné
    if selected_country:
        filtered_leagues = [
            league for league in all_leagues 
            if league.startswith(selected_country + ":")
        ]
    else:
        filtered_leagues = all_leagues
    
    # Filtrer par recherche si une ligue spécifique est sélectionnée
    if search_value:
        filtered_leagues = [league for league in filtered_leagues if league == search_value]
    
    # Options pour le dropdown de recherche (toujours toutes les ligues filtrées par pays)
    league_options = [
        {"label": league, "value": league} 
        for league in (
            [l for l in all_leagues if l.startswith(selected_country + ":")] 
            if selected_country 
            else all_leagues
        )
    ]
    
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
    
    return country_options, league_options, league_cards, stats_text


# Layout pour l'export
layout = create_layout()
