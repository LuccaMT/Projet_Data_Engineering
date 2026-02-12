"""
Page de recherche de clubs avec Elasticsearch
"""
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from components.navbar import create_navbar
from database import get_db_connection


def layout():
    """Layout de la page de recherche de clubs."""
    return html.Div(
        className="club-page-wrapper search",
        children=[
        # Header avec logo
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
                                html.H1("Flashscore Football Dashboard", style={"color": "white"}),
                                html.P("Recherche de clubs", style={"color": "rgba(255,255,255,0.9)"}),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        
        # Navbar
        create_navbar(current_page="clubs"),
        
        dbc.Container([
            # Modern search container
            html.Div([
                html.Div([
                    html.Div("🔍", className="search-title-icon"),
                    html.H1("Recherche de Clubs", className="search-title"),
                    html.P(
                        "Découvrez les statistiques détaillées de plus de 1000 clubs de football",
                        className="search-subtitle"
                    )
                ], className="search-title-container"),
                
                # Barre de recherche moderne
                html.Div([
                    dbc.Input(
                        id="club-search-input",
                        placeholder="🏟️  Entrez le nom d'un club (ex: Manchester, PSG, Barcelona)...",
                        type="text",
                        className="modern-search-input mb-3",
                        debounce=True
                    ),
                    dbc.Button(
                        ["✨ Rechercher"],
                        id="club-search-button",
                        className="modern-search-button w-100"
                    )
                ])
            ], className="modern-search-container"),
            
            # Loading indicator
            dcc.Loading(
                id="club-search-loading",
                type="circle",
                color="#667eea",
                children=html.Div(id="club-search-results")
            )
        ], fluid=True, className="px-4")
    ])


@callback(
    Output("club-search-results", "children"),
    [Input("club-search-button", "n_clicks"),
     Input("club-search-input", "n_submit")],
    State("club-search-input", "value"),
    prevent_initial_call=True
)
def search_clubs(_n_clicks, _n_submit, search_query):
    """Recherche des clubs et affiche les résultats."""
    if not search_query or not search_query.strip():
        return dbc.Alert(
            "Veuillez entrer un nom de club pour rechercher.",
            color="warning",
            className="text-center"
        )
    
    # Recherche dans Elasticsearch
    db = get_db_connection()
    clubs = db.search_clubs(search_query.strip(), size=20)
    
    if not clubs:
        return dbc.Alert([
            html.H4("Aucun club trouvé", className="alert-heading"),
            html.P(f"Aucun résultat pour « {search_query} ». Essayez avec un autre nom.")
        ], color="info", className="text-center mt-4")
    
    # Afficher les résultats sous forme de cartes
    club_cards = []
    for club in clubs:
        # Calculer les statistiques pour les badges
        total = club.get('total_matches', 0)
        wins = club.get('wins', 0)
        draws = club.get('draws', 0)
        losses = club.get('losses', 0)
        goals_for = club.get('goals_for', 0)
        goals_against = club.get('goals_against', 0)
        win_rate = club.get('win_rate', 0)
        recent_form = club.get('recent_form', '')
        
        # Badge de couleur selon le taux de victoire
        if win_rate >= 60:
            badge_color = "success"
        elif win_rate >= 40:
            badge_color = "primary"
        else:
            badge_color = "secondary"
        
        # Créer les badges pour la forme récente
        form_badges = []
        for result in recent_form:
            form_badges.append(
                html.Span(
                    result,
                    className=f"form-indicator {'win' if result == 'W' else 'draw' if result == 'D' else 'loss'}",
                    title="Victoire" if result == 'W' else "Nul" if result == 'D' else "Défaite"
                )
            )
        
        card = dbc.Col([
            html.Div([
                # Header avec logo
                html.Div([
                    html.Div([
                        html.Img(
                            src=club.get('logo', ''),
                            className="club-logo"
                        ) if club.get('logo') else None,
                    ], style={'marginRight': '1.5rem'}),
                    html.Div([
                        html.H3(club.get('name', 'N/A'), className="club-name"),
                        html.P(
                            ' • '.join(club.get('leagues', ['N/A'])[:2]),
                            className="text-muted mb-0",
                            style={'fontSize': '0.95rem'}
                        )
                    ], style={'flex': '1'})
                ], className="club-card-header"),
                
                # Statistiques en grille
                html.Div([
                    html.Div([
                        html.Span(str(total), className="stat-value"),
                        html.Span("Matchs", className="stat-label")
                    ], className="stat-item"),
                    html.Div([
                        html.Span(str(wins), className="stat-value", style={'color': '#11998e'}),
                        html.Span("Victoires", className="stat-label")
                    ], className="stat-item"),
                    html.Div([
                        html.Span(str(draws), className="stat-value", style={'color': '#f2c94c'}),
                        html.Span("Nuls", className="stat-label")
                    ], className="stat-item"),
                    html.Div([
                        html.Span(str(losses), className="stat-value", style={'color': '#eb3349'}),
                        html.Span("Défaites", className="stat-label")
                    ], className="stat-item"),
                ], className="stats-grid", style={'gridTemplateColumns': 'repeat(2, 1fr)', 'gap': '0.5rem', 'marginBottom': '1rem'}),
                
                # Badges de stats
                html.Div([
                    html.Span(f"⚽ {goals_for} marqués", className="stat-badge success"),
                    html.Span(f"🛡️ {goals_against} encaissés", className="stat-badge warning"),
                    html.Span(f"📊 {win_rate:.0f}% victoires", className=f"stat-badge {badge_color}"),
                    html.Span(
                        f"📈 {goals_for - goals_against:+d}",
                        className=f"stat-badge {'success' if goals_for - goals_against >= 0 else 'secondary'}"
                    ),
                ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '0.4rem', 'marginBottom': '1rem'}),
                
                # Forme récente
                html.Div([
                    html.Strong("Forme récente: ", style={'color': '#718096', 'marginRight': '1rem'}),
                    html.Div(form_badges, className="form-indicators d-inline-flex")
                ], className="mb-3") if recent_form else None,
                
                # Boutons d'action
                html.Div([
                    dbc.Button(
                        ["📊 Voir détails"],
                        href=f"/clubs/detail?name={club.get('name', '')}",
                        className="modern-btn modern-btn-primary"
                    ),
                    dbc.Button(
                        ["⚖️ Comparer"],
                        href=f"/clubs/compare?club1={club.get('name', '')}",
                        className="modern-btn modern-btn-secondary"
                    )
                ], className="modern-action-buttons")
            ], className="modern-club-card")
        ], md=6, lg=4, className="mb-4")
        
        club_cards.append(card)
    
    return html.Div([
        html.Div([
            html.Div([
                html.Span(str(len(clubs)), style={
                    'fontSize': '2.5rem', 'fontWeight': '800',
                    'background': 'linear-gradient(135deg, #2563eb, #7c3aed)',
                    'WebkitBackgroundClip': 'text',
                    'WebkitTextFillColor': 'transparent',
                    'marginRight': '0.75rem'
                }),
                html.Span("club(s) trouvé(s)", style={
                    'fontSize': '1.3rem', 'fontWeight': '600',
                    'color': '#475569'
                })
            ], style={'textAlign': 'center', 'marginBottom': '2rem', 'padding': '1.25rem',
                      'background': 'white', 'borderRadius': '16px',
                      'boxShadow': '0 2px 8px rgba(0,0,0,0.06)',
                      'border': '1px solid #e2e8f0',
                      'overflow': 'hidden', 'wordBreak': 'break-word'}),
            dbc.Row(club_cards, className="g-4")
        ])
    ])
