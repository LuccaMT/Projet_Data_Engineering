"""Page Ligues : parcourir et naviguer vers la vue détaillée d'une ligue."""

from typing import List

import urllib.parse
from dash import html, dcc, Input, Output, callback

from database import get_db_connection
from components.navbar import create_navbar
from text_utils import normalize_unicode_label, parse_league_country
from pages.cups import is_cup


TOP_5_LEAGUES = [
    "FRANCE: Ligue 1",
    "SPAIN: LaLiga",
    "ENGLAND: Premier League",
    "GERMANY: Bundesliga",
    "ITALY: Serie A",
]

LEAGUE_EMOJIS = {
    "FRANCE: Ligue 1": "🇫🇷",
    "SPAIN: LaLiga": "🇪🇸",
    "ENGLAND: Premier League": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "GERMANY: Bundesliga": "🇩🇪",
    "ITALY: Serie A": "🇮🇹",
}


def get_flashscore_countries() -> List[str]:
    """Retourne la liste triée des pays présents dans les ligues.

    Returns:
        List[str]: Pays distincts détectés via le préfixe "PAYS: Ligue".
    """
    db = get_db_connection()
    leagues = [league for league in db.get_all_leagues() if not is_cup(league)]
    
    countries = set()
    for league in leagues:
        if ":" in league:
            country = league.split(":")[0].strip()
            countries.add(country)
    
    return sorted(list(countries))


def get_all_leagues() -> List[str]:
    """Récupère toutes les ligues disponibles depuis MongoDB.

    Returns:
        List[str]: Liste des labels de ligues.
    """
    db = get_db_connection()
    return db.get_all_leagues()


# Classement custom pour mettre en avant les ligues les plus prestigieuses/populaires
PRESTIGE_RULES = [
    {"keywords": ["premier league"], "countries": {"england"}},
    {"keywords": ["laliga", "la liga"], "countries": {"spain"}},
    {"keywords": ["bundesliga"], "countries": {"germany"}},
    {"keywords": ["serie a"], "countries": {"italy"}},
    {"keywords": ["ligue 1"], "countries": {"france"}},
    {"keywords": ["eredivisie"], "countries": {"netherlands"}},
    {"keywords": ["primeira liga"], "countries": {"portugal"}},
    {"keywords": ["super lig"], "countries": {"turkey"}},
    {"keywords": ["jupiler pro league", "first division a"], "countries": {"belgium"}},
    {"keywords": ["liga mx"], "countries": {"mexico"}},
    {"keywords": ["mls", "major league soccer"], "countries": {"usa", "united states"}},
    {"keywords": ["serie a"], "countries": {"brazil"}},
    {"keywords": ["liga profesional", "liga profissional", "primera division"], "countries": {"argentina"}},
    {"keywords": ["pro league"], "countries": {"saudi arabia"}},
]

COUNTRY_PRIORITY = [
    "england",
    "spain",
    "germany",
    "italy",
    "france",
    "netherlands",
    "portugal",
    "turkey",
    "belgium",
    "brazil",
    "argentina",
    "mexico",
    "usa",
    "united states",
    "saudi arabia",
]
COUNTRY_RANK = {country: idx for idx, country in enumerate(COUNTRY_PRIORITY)}

SECONDARY_LEAGUE_MARKERS = [
    "championship",
    "league one",
    "league two",
    "segunda",
    "division 2",
    "division 3",
    "national league",
]

CUP_AND_FRIENDLY_MARKERS = [
    "cup",
    "friendly",
    "play-off",
    "play off",
    "playoff",
    "trophy",
]


def _normalize_label(value: str) -> str:
    """Normalise un label pour les comparaisons.

    Args:
        value: Label brut.

    Returns:
        Chaîne ASCII-isée, en minuscules, espaces normalisés.
    """
    normalized_ascii = normalize_unicode_label(value or "")
    return " ".join(normalized_ascii.lower().split())


def _split_league_parts(league_label: str) -> tuple[str, str]:
    """Divise un label de ligue en parties normalisées (pays, ligue)."""
    country, name = parse_league_country(league_label)
    return _normalize_label(country), _normalize_label(name)


def league_priority(league_label: str) -> float:
    """Calcule la priorité de tri (plus bas = plus prestigieux)."""
    country, league_name = _split_league_parts(league_label)
    
    for idx, rule in enumerate(PRESTIGE_RULES):
        if rule["countries"] and country not in rule["countries"]:
            continue
        if any(keyword in league_name for keyword in rule["keywords"]):
            return float(idx)
    
    country_score = COUNTRY_RANK.get(country, len(COUNTRY_RANK))
    penalty = 0.0
    if any(marker in league_name for marker in SECONDARY_LEAGUE_MARKERS):
        penalty += 0.75
    if any(marker in league_name for marker in CUP_AND_FRIENDLY_MARKERS):
        penalty += 1.5
    
    return float(len(PRESTIGE_RULES) + country_score) + penalty


def sort_leagues_by_prestige(leagues: List[str]) -> List[str]:
    """Trie les ligues par :func:`league_priority` puis ordre alphabétique."""
    return sorted(leagues, key=lambda league: (league_priority(league), league))


def create_league_card(league: str, emoji: str = "🏆", is_top_5: bool = False):
    """Crée un bloc UI de carte de ligue.

    Args:
        league: Label de la ligue.
        emoji: Emoji affiché à côté de la ligue.
        is_top_5: Si True, met en évidence comme ligue Top 5.

    Returns:
        Conteneur HTML Dash pour la carte.
    """
    bg_color = "#fffbeb" if is_top_5 else "#ffffff"
    border_color = "#fbbf24" if is_top_5 else "#e5e7eb"
    
    return html.Div(
        className="league-card",
        style={
            "backgroundColor": bg_color,
            "border": f"2px solid {border_color}",
        },
        children=[
            html.Div(
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "gap": "12px",
                    "marginBottom": "12px",
                },
                children=[
                    html.Span(emoji, style={"fontSize": "28px"}),
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
            dcc.Link(
                "Voir les matchs & classement →",
                href=f"/league?name={urllib.parse.quote_plus(league)}",
                className="league-button",
                style={
                    "display": "block",
                    "width": "100%",
                    "padding": "8px 16px",
                    "backgroundColor": "#eff6ff",
                    "color": "#2563eb",
                    "border": "1px solid #bfdbfe",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                    "transition": "all 0.2s",
                    "fontWeight": "600",
                    "textDecoration": "none",
                    "textAlign": "center",
                },
            ),
        ],
    )


def create_layout():
    """Crée le layout de la page ligues."""
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
                                        "🌍 Pays et Continent",
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
                                        placeholder="Tous les pays et continents",
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
    """Met à jour les options de pays, options de recherche et cartes de ligues affichées."""
    print(f"[DEBUG] Recherche: {search_value}, Pays: {selected_country}")
    
    # La page Ligues n'affiche que les championnats (les coupes restent sur /cups)
    all_leagues = [league for league in get_all_leagues() if not is_cup(league)]
    
    print(f"[DEBUG] Total ligues (hors coupes): {len(all_leagues)}")
    
    sorted_leagues = sort_leagues_by_prestige(all_leagues)
    all_countries = get_flashscore_countries()
    
    country_options = [{"label": country, "value": country} for country in all_countries]
    
    if selected_country:
        filtered_leagues = [
            league for league in sorted_leagues 
            if league.startswith(selected_country + ":")
        ]
    else:
        filtered_leagues = sorted_leagues
    
    if search_value:
        filtered_leagues = [league for league in filtered_leagues if league == search_value]
    
    league_options_source = (
        [l for l in sorted_leagues if l.startswith(selected_country + ":")]
        if selected_country
        else sorted_leagues
    )
    league_options = [{"label": league, "value": league} for league in league_options_source]
    
    top_preview = ", ".join(filtered_leagues[:3]) if filtered_leagues else "aucune"
    stats_text = (
        f"{len(filtered_leagues)} ligue(s) triées par prestige/popularité "
        f"(top: {top_preview})"
    )
    
    top_5_filtered = [l for l in filtered_leagues if l in TOP_5_LEAGUES]
    other_leagues = [l for l in filtered_leagues if l not in TOP_5_LEAGUES]
    
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
        
        if top_5_filtered:
            league_cards.append(
                html.Div(
                    style={
                        "gridColumn": "1 / -1",
                        "marginBottom": "12px",
                        "padding": "16px 20px",
                        "backgroundColor": "#fef3c7",
                        "borderRadius": "12px",
                        "border": "2px solid #fbbf24",
                    },
                    children=[
                        html.H3(
                            "🌟 Top 5 Grands Championnats",
                            style={
                                "margin": "0",
                                "fontSize": "22px",
                                "fontWeight": "800",
                                "color": "#92400e",
                            },
                        ),
                        html.P(
                            f"Calendrier étendu : 6 mois de matchs • {len(top_5_filtered)} ligue(s)",
                            style={
                                "margin": "4px 0 0 0",
                                "fontSize": "14px",
                                "color": "#78350f",
                                "fontWeight": "600",
                            },
                        ),
                    ],
                ),
            )
            
            for league in top_5_filtered:
                emoji = LEAGUE_EMOJIS.get(league, "🏆")
                league_cards.append(create_league_card(league, emoji, is_top_5=True))
        
        if other_leagues:
            league_cards.append(
                html.Div(
                    style={
                        "gridColumn": "1 / -1",
                        "marginTop": "32px",
                        "marginBottom": "12px",
                        "padding": "16px 20px",
                        "backgroundColor": "#f0f9ff",
                        "borderRadius": "12px",
                        "border": "2px solid #bfdbfe",
                    },
                    children=[
                        html.H3(
                            "🏆 Autres Championnats",
                            style={
                                "margin": "0",
                                "fontSize": "20px",
                                "fontWeight": "700",
                                "color": "#1e40af",
                            },
                        ),
                        html.P(
                            f"{len(other_leagues)} championnat(s)",
                            style={
                                "margin": "4px 0 0 0",
                                "fontSize": "14px",
                                "color": "#1e40af",
                                "fontWeight": "600",
                            },
                        ),
                    ],
                ),
            )
            
            for league in other_leagues:
                league_cards.append(create_league_card(league, "🏆", is_top_5=False))
    
    return country_options, league_options, league_cards, stats_text


layout = create_layout()
