"""Page coupes : classifie et affiche les compétitions de coupes."""

from typing import Dict, List, Tuple

import urllib.parse
from dash import html, dcc, Input, Output, callback

from database import get_db_connection
from components.navbar import create_navbar
from text_utils import normalize_unicode_label, parse_league_country


CUP_RULES: List[Dict] = [
    {"keywords": ["world cup", "coupe du monde"], "category": "international"},
    {"keywords": ["champions league"], "category": "continental_clubs"},
    {"keywords": ["europa league"], "category": "continental_clubs"},
    {"keywords": ["conference league"], "category": "continental_clubs"},
    {"keywords": ["libertadores"], "category": "continental_clubs"},
    {"keywords": ["sudamericana"], "category": "continental_clubs"},
    {"keywords": ["caf champions"], "category": "continental_clubs"},
    {"keywords": ["confederation cup"], "category": "continental_clubs"},
    {"keywords": ["afc champions"], "category": "continental_clubs"},
    {"keywords": ["concacaf champions"], "category": "continental_clubs"},
    {"keywords": ["club world cup"], "category": "international"},
    {"keywords": ["euro"], "category": "continental_nations"},
    {"keywords": ["copa america"], "category": "continental_nations"},
    {"keywords": ["africa cup", "african cup", "can", "coupe d'afrique"], "category": "continental_nations"},
    {"keywords": ["asian cup"], "category": "continental_nations"},
    {"keywords": ["gold cup"], "category": "continental_nations"},
    {"keywords": ["arab cup"], "category": "continental_nations"},
    {"keywords": ["nations league"], "category": "international"},
    {"keywords": ["dfb pokal", "dfb-pokal"], "category": "national"},
    {"keywords": ["fa cup"], "category": "national"},
    {"keywords": ["coupe de france"], "category": "national"},
    {"keywords": ["copa del rey"], "category": "national"},
    {"keywords": ["coppa italia"], "category": "national"},
]

CUP_KEYWORDS = set(
    keyword
    for rule in CUP_RULES
    for keyword in rule["keywords"]
) | {
    "cup",
    "copa",
    "coupe",
    "coppa",
    "pokal",
    "taca",
    "taça",
    "ta�a",
    "taÃ§a",
    "taça de",
}

CATEGORY_LABELS: Dict[str, str] = {
    "international": "International (nations/clubs)",
    "continental_nations": "Continental - Nations",
    "continental_clubs": "Continental - Clubs",
    "national": "National / Domestique",
    "other": "Autre",
}

CATEGORY_ORDER = ["international", "continental_nations", "continental_clubs", "national", "other"]
CATEGORY_RANK = {cat: idx for idx, cat in enumerate(CATEGORY_ORDER)}


def _normalize_label(value: str) -> str:
    """Normalize a label for comparisons.

    Args:
        value: Raw label.

    Returns:
        ASCII-ish, lowercase, whitespace-normalized string.
    """
    normalized_ascii = normalize_unicode_label(value or "")
    return " ".join(normalized_ascii.lower().split())


def _split_league_parts(league_label: str) -> Tuple[str, str]:
    """Divise un label de ligue en parties normalisées (pays, ligue)."""
    country, name = parse_league_country(league_label)
    return _normalize_label(country), _normalize_label(name)


def is_cup(league_label: str) -> bool:
    """Vérifie si un label de ligue ressemble à une compétition de coupe."""
    _, league_name = _split_league_parts(league_label)
    return any(keyword in league_name for keyword in CUP_KEYWORDS)


def classify_cup(league_label: str) -> str:
    """Classifie une coupe dans l'une des catégories UI."""
    _, league_name = _split_league_parts(league_label)
    for rule in CUP_RULES:
        if any(keyword in league_name for keyword in rule["keywords"]):
            return rule["category"]
    if "cup" in league_name or "copa" in league_name or "coupe" in league_name:
        return "national"
    return "other"


def cup_priority(league_label: str) -> float:
    """Calcule la priorité de tri (plus bas = plus prestigieux)."""
    _, league_name = _split_league_parts(league_label)
    for idx, rule in enumerate(CUP_RULES):
        if any(keyword in league_name for keyword in rule["keywords"]):
            return float(idx)
    category = classify_cup(league_label)
    return float(len(CUP_RULES) + CATEGORY_RANK.get(category, len(CATEGORY_RANK)))


def get_all_cups() -> List[Dict]:
    """Récupère et pré-trie toutes les coupes trouvées dans la liste des ligues MongoDB."""
    db = get_db_connection()
    leagues = db.get_all_leagues()
    cups = []
    for league in leagues:
        if not is_cup(league):
            continue
        cups.append(
            {
                "name": league,
                "category": classify_cup(league),
                "priority": cup_priority(league),
            }
        )
    cups.sort(key=lambda c: (c["priority"], c["name"]))
    return cups


def create_layout():
    """Crée le layout de la page coupes."""
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
                                    html.P("Sélection des grandes coupes (clubs et nations)"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # Navbar
            create_navbar(current_page="cups"),
            # Main content
            html.Div(
                className="main-content",
                children=[
                    # En-tête
                    html.Div(
                        style={
                            "textAlign": "center",
                            "marginBottom": "32px",
                        },
                        children=[
                            html.H1(
                                "🏆 Coupes & Tournois",
                                style={
                                    "fontSize": "34px",
                                    "fontWeight": "800",
                                    "color": "#1e3a8a",
                                    "marginBottom": "10px",
                                    "letterSpacing": "-0.5px",
                                },
                            ),
                            html.P(
                                "Champions League, CAN, Coupe du Monde, Europa League, Copa America, etc.",
                                style={
                                    "fontSize": "16px",
                                    "color": "#4b5563",
                                    "fontWeight": "500",
                                },
                            ),
                        ],
                    ),
                    # Panneau de filtres
                    html.Div(
                        className="control-panel",
                        children=[
                            html.H3("Filtres"),
                            html.Div(
                                style={"marginBottom": "20px"},
                                children=[
                                    html.Label(
                                        "Type de coupe",
                                        style={
                                            "marginBottom": "10px",
                                            "display": "block",
                                            "fontWeight": "600",
                                            "fontSize": "15px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="cup-category-filter",
                                        options=[
                                            {"label": "Toutes", "value": "all"},
                                            {"label": CATEGORY_LABELS["international"], "value": "international"},
                                            {"label": CATEGORY_LABELS["continental_nations"], "value": "continental_nations"},
                                            {"label": CATEGORY_LABELS["continental_clubs"], "value": "continental_clubs"},
                                            {"label": CATEGORY_LABELS["national"], "value": "national"},
                                        ],
                                        value="all",
                                        clearable=False,
                                    ),
                                ],
                            ),
                            html.Div(
                                style={"marginBottom": "20px"},
                                children=[
                                    html.Label(
                                        "Rechercher une coupe",
                                        style={
                                            "marginBottom": "10px",
                                            "display": "block",
                                            "fontWeight": "600",
                                            "fontSize": "15px",
                                        },
                                    ),
                                    dcc.Dropdown(
                                        id="cup-search-input",
                                        options=[],
                                        value=None,
                                        placeholder="Tapez pour chercher une coupe (UEFA Champions League, Coupe du Monde...)",
                                        clearable=True,
                                        searchable=True,
                                    ),
                                ],
                            ),
                            html.Div(
                                id="cups-stats",
                                style={
                                    "backgroundColor": "#f8fafc",
                                    "padding": "14px 18px",
                                    "borderRadius": "10px",
                                    "border": "2px solid #e2e8f0",
                                    "marginBottom": "10px",
                                },
                                children=[
                                    html.Div(
                                        style={"display": "flex", "alignItems": "center", "gap": "8px"},
                                        children=[
                                            html.Span("📊", style={"fontSize": "20px"}),
                                            html.Span(
                                                "Chargement des coupes...",
                                                id="cups-stats-text",
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
                    # Liste
                    html.Div(
                        className="table-container",
                        children=[
                            html.H3("Coupes disponibles"),
                            html.Div(
                                id="cups-list",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(auto-fill, minmax(320px, 1fr))",
                                    "gap": "16px",
                                    "marginTop": "16px",
                                },
                                children=[
                                    html.Div(
                                        style={
                                            "textAlign": "center",
                                            "padding": "40px",
                                            "color": "#9ca3af",
                                        },
                                        children=["Chargement des coupes..."],
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
        Output("cup-search-input", "options"),
        Output("cups-list", "children"),
        Output("cups-stats-text", "children"),
    ],
    [
        Input("cup-search-input", "value"),
        Input("cup-category-filter", "value"),
    ],
)
def update_cups_list(search_value, selected_category):
    """Met à jour les options de recherche de coupes et les cartes affichées selon les filtres."""
    cups = get_all_cups()
    if selected_category and selected_category != "all":
        cups = [c for c in cups if c["category"] == selected_category]
    if search_value:
        cups = [c for c in cups if c["name"] == search_value]

    search_options = [{"label": c["name"], "value": c["name"]} for c in cups] or []

    if not cups:
        cards = [
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
                    html.Div("🔍", style={"fontSize": "48px", "marginBottom": "16px", "opacity": "0.5"}),
                    html.P(
                        "Aucune coupe trouvée",
                        style={
                            "fontSize": "18px",
                            "color": "#6b7280",
                            "fontWeight": "600",
                            "marginBottom": "6px",
                        },
                    ),
                    html.P("Essayez une autre recherche ou catégorie", style={"fontSize": "14px", "color": "#9ca3af"}),
                ],
            )
        ]
    else:
        cards = []
        for cup in cups:
            cards.append(
                html.Div(
                    className="league-card",
                    children=[
                        html.Div(
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "12px",
                                "marginBottom": "10px",
                            },
                            children=[
                                html.Span("🏆", style={"fontSize": "28px"}),
                                html.Div(
                                    children=[
                                        html.H4(
                                            cup["name"],
                                            style={
                                                "margin": "0",
                                                "fontSize": "16px",
                                                "fontWeight": "700",
                                                "color": "#1f2937",
                                                "lineHeight": "1.4",
                                            },
                                        ),
                                        html.Span(
                                            CATEGORY_LABELS.get(cup["category"], "Autre"),
                                            style={
                                                "display": "inline-block",
                                                "marginTop": "4px",
                                                "fontSize": "12px",
                                                "color": "#2563eb",
                                                "backgroundColor": "#eff6ff",
                                                "padding": "4px 8px",
                                                "borderRadius": "8px",
                                                "fontWeight": "600",
                                            },
                                        ),
                                    ]
                                ),
                            ],
                        ),
                        dcc.Link(
                            "Voir les matchs →",
                            href=f"/league?name={urllib.parse.quote_plus(cup['name'])}",
                            className="league-button",
                            style={
                                "display": "block",
                                "width": "100%",
                                "padding": "8px 16px",
                                "backgroundColor": "#ecfdf3",
                                "color": "#166534",
                                "border": "2px solid #bbf7d0",
                                "borderRadius": "8px",
                                "fontSize": "13px",
                                "fontWeight": "700",
                                "cursor": "pointer",
                                "transition": "all 0.2s ease",
                                "textDecoration": "none",
                                "textAlign": "center",
                            },
                        ),
                    ],
                )
            )

    stats_text = f"{len(cups)} coupe(s) trouvée(s) (ordre = prestige/importance)"
    return search_options, cards, stats_text


layout = create_layout()
