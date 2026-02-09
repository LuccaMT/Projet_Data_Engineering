"""
Page de détail d'un club avec statistiques et graphiques
"""
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from urllib.parse import parse_qs
from components.navbar import create_navbar
from database import get_db_connection


def layout():
    """Layout de la page de détail d'un club."""
    return html.Div(
        className="club-page-wrapper detail",
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
                                html.P("Statistiques détaillées", style={"color": "rgba(255,255,255,0.9)"}),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        
        create_navbar(current_page="clubs"),
        
        dcc.Location(id='club-detail-url', refresh=False),
        
        dbc.Container([
            dcc.Loading(
                id="club-detail-loading",
                type="circle",
                color="#4facfe",
                children=html.Div(id="club-detail-content")
            )
        ], fluid=True, className="px-4 py-5")
    ])


@callback(
    Output("club-detail-content", "children"),
    Input("club-detail-url", "search")
)
def display_club_detail(search):
    """Affiche les détails complets d'un club."""
    if not search:
        return dbc.Alert(
            "Aucun club sélectionné. Veuillez rechercher un club d'abord.",
            color="warning",
            className="text-center mt-5"
        )
    
    # Extraire le nom du club depuis l'URL
    params = parse_qs(search.lstrip('?'))
    club_name = params.get('name', [None])[0]
    
    if not club_name:
        return dbc.Alert(
            "Nom de club invalide.",
            color="danger",
            className="text-center mt-5"
        )
    
    # Récupérer les données du club
    db = get_db_connection()
    club = db.get_club_by_name(club_name)
    
    if not club:
        return dbc.Alert([
            html.H4("Club non trouvé", className="alert-heading"),
            html.P(f"Le club « {club_name} » n'existe pas dans notre base de données."),
            dbc.Button("Retour à la recherche", href="/clubs/search", color="primary")
        ], color="danger", className="text-center mt-5")
    
    # Récupérer l'historique des matchs
    matches_history = db.get_club_matches_history(club_name, limit=20)
    
    # Statistiques
    total = club.get('total_matches', 0)
    wins = club.get('wins', 0)
    draws = club.get('draws', 0)
    losses = club.get('losses', 0)
    goals_for = club.get('goals_for', 0)
    goals_against = club.get('goals_against', 0)
    goal_diff = club.get('goal_difference', 0)
    win_rate = club.get('win_rate', 0)
    recent_form = club.get('recent_form', '')
    leagues = club.get('leagues', [])
    
    # ========== GRAPHIQUES ==========
    
    # 1. Pie chart des résultats
    results_pie = go.Figure(data=[go.Pie(
        labels=['Victoires', 'Nuls', 'Défaites'],
        values=[wins, draws, losses],
        marker=dict(colors=['#10b981', '#64748b', '#ef4444']),
        hole=0.4
    )])
    results_pie.update_layout(
        title="Répartition des résultats",
        height=350,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # 2. Bar chart buts pour/contre
    goals_bar = go.Figure(data=[
        go.Bar(name='Buts marqués', x=['Attaque'], y=[goals_for], marker_color='#10b981'),
        go.Bar(name='Buts encaissés', x=['Défense'], y=[goals_against], marker_color='#ef4444')
    ])
    goals_bar.update_layout(
        title="Buts marqués vs Buts encaissés",
        yaxis_title="Nombre de buts",
        height=350,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # 3. Line chart forme récente (derniers 20 matchs)
    form_data = []
    form_labels = []
    for i, match in enumerate(matches_history[::-1]):  # Du plus ancien au plus récent
        home = match.get('home')
        away = match.get('away')
        home_score = match.get('home_score')
        away_score = match.get('away_score')
        
        if home == club_name:
            if home_score > away_score:
                result = 3  # Victoire
                opponent = away
            elif home_score == away_score:
                result = 1  # Nul
                opponent = away
            else:
                result = 0  # Défaite
                opponent = away
        else:
            if away_score > home_score:
                result = 3  # Victoire
                opponent = home
            elif away_score == home_score:
                result = 1  # Nul
                opponent = home
            else:
                result = 0  # Défaite
                opponent = home
        
        form_data.append(result)
        form_labels.append(f"vs {opponent}")
    
    form_line = go.Figure()
    form_line.add_trace(go.Scatter(
        x=list(range(len(form_data))),
        y=form_data,
        mode='lines+markers',
        line=dict(color='#007bff', width=3),
        marker=dict(size=10),
        text=form_labels,
        hovertemplate='<b>%{text}</b><br>Points: %{y}<extra></extra>'
    ))
    form_line.update_layout(
        title="Évolution de la forme (derniers matchs)",
        xaxis_title="Matchs",
        yaxis_title="Points (V=3, N=1, D=0)",
        height=350,
        yaxis=dict(tickmode='array', tickvals=[0, 1, 3], ticktext=['Défaite', 'Nul', 'Victoire']),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x'
    )
    
    # ========== LAYOUT ==========
    
    # ========== INTERFACE MODERNE ==========
    return html.Div([
        # Header moderne avec le nom du club
        html.Div([
            html.Div([
                html.Img(
                    src=club.get('logo', ''),
                    className="club-logo",
                    style={'width': '100px', 'height': '100px', 'marginRight': '2rem'}
                ) if club.get('logo') else None,
                html.Div([
                    html.H1(club_name, className="club-detail-title"),
                    html.P(
                        ' • '.join(leagues),
                        style={'fontSize': '1.2rem', 'color': '#718096', 'fontWeight': '500'}
                    )
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'position': 'relative', 'zIndex': '1'})
        ], className="club-detail-header"),
        
        # Statistiques rapides en grille moderne
        html.Div([
            html.Div([
                html.Div("📊", style={'fontSize': '2.5rem', 'marginBottom': '1rem'}),
                html.Div(str(total), className="stat-value", style={'fontSize': '3rem'}),
                html.Div("Matchs joués", className="stat-label")
            ], className="stat-item", style={'padding': '2.5rem'}),
            html.Div([
                html.Div("🏆", style={'fontSize': '2.5rem', 'marginBottom': '1rem'}),
                html.Div(f"{win_rate:.1f}%", className="stat-value", style={'fontSize': '3rem', 'color': '#2563eb'}),
                html.Div("Taux de victoire", className="stat-label")
            ], className="stat-item", style={'padding': '2.5rem'}),
            html.Div([
                html.Div("⚽", style={'fontSize': '2.5rem', 'marginBottom': '1rem'}),
                html.Div(f"{goals_for}-{goals_against}", className="stat-value", style={'fontSize': '3rem', 'color': '#7c3aed'}),
                html.Div("Buts (pour-contre)", className="stat-label")
            ], className="stat-item", style={'padding': '2.5rem'}),
            html.Div([
                html.Div("📈", style={'fontSize': '2.5rem', 'marginBottom': '1rem'}),
                html.Div(f"{goal_diff:+d}", className="stat-value", style={'fontSize': '3rem', 'color': '#10b981' if goal_diff >= 0 else '#ef4444'}),
                html.Div("Différence de buts", className="stat-label")
            ], className="stat-item", style={'padding': '2.5rem'}),
        ], className="stats-grid", style={'gridTemplateColumns': 'repeat(auto-fit, minmax(180px, 1fr))', 'gap': '1.5rem', 'margin': '2rem 0'}),
        
        # Bilan détaillé avec forme récente
        html.Div([
            html.Div([
                html.H3("📊 Bilan complet", className="chart-title"),
                html.Div([
                    html.Div([
                        html.Div("🏆", style={'fontSize': '2rem', 'marginBottom': '0.5rem'}),
                        html.Div(str(wins), className="stat-value", style={'fontSize': '2.5rem', 'color': '#10b981'}),
                        html.Div("Victoires", className="stat-label")
                    ], className="stat-item"),
                    html.Div([
                        html.Div("🤝", style={'fontSize': '2rem', 'marginBottom': '0.5rem'}),
                        html.Div(str(draws), className="stat-value", style={'fontSize': '2.5rem', 'color': '#64748b'}),
                        html.Div("Nuls", className="stat-label")
                    ], className="stat-item"),
                    html.Div([
                        html.Div("❌", style={'fontSize': '2rem', 'marginBottom': '0.5rem'}),
                        html.Div(str(losses), className="stat-value", style={'fontSize': '2.5rem', 'color': '#ef4444'}),
                        html.Div("Défaites", className="stat-label")
                    ], className="stat-item")
                ], className="stats-grid", style={'gridTemplateColumns': '1fr 1fr 1fr'})
            ], style={'flex': '1'}),
            html.Div([
                html.H3("🔥 Forme récente", className="chart-title"),
                html.Div([
                    html.Span(
                        result,
                        className=f"form-indicator {'win' if result == 'W' else 'draw' if result == 'D' else 'loss'}",
                        title=f"{'Victoire' if result == 'W' else 'Nul' if result == 'D' else 'Défaite'}"
                    ) for result in recent_form
                ] if recent_form else [html.P("Pas de données disponibles", className="text-muted")],
                    className="form-indicators",
                    style={'justifyContent': 'center', 'padding': '2rem'}
                )
            ], style={'flex': '1'})
        ], style={'display': 'flex', 'gap': '2rem', 'marginBottom': '2rem', 'flexWrap': 'wrap'}, className="modern-chart-container"),
        
        # Graphiques interactifs
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Graph(figure=results_pie, config={'displayModeBar': False})
                ], className="modern-chart-container")
            ], md=4),
            dbc.Col([
                html.Div([
                    dcc.Graph(figure=goals_bar, config={'displayModeBar': False})
                ], className="modern-chart-container")
            ], md=4),
            dbc.Col([
                html.Div([
                    dcc.Graph(figure=form_line, config={'displayModeBar': False})
                ], className="modern-chart-container")
            ], md=4)
        ], className="mb-4"),
        
        # Historique des matchs moderne
        html.Div([
            html.H3("📅 Historique des matchs récents", className="chart-title"),
            html.Div([
                create_match_row(match, club_name) for match in matches_history[:10]
            ] if matches_history else [
                html.P("Aucun match disponible", className="text-muted text-center", style={'padding': '3rem'})
            ])
        ], className="modern-chart-container"),
        
        # Bouton de comparaison moderne
        html.Div([
            dbc.Button(
                ["⚖️ Comparer avec un autre club"],
                href=f"/clubs/compare?club1={club_name}",
                className="modern-btn modern-btn-primary",
                style={'width': '100%', 'maxWidth': '400px', 'margin': '0 auto', 'display': 'block', 'fontSize': '1.1rem', 'padding': '1rem'}
            )
        ], style={'marginTop': '3rem', 'textAlign': 'center'})
    ])


def create_match_row(match, club_name):
    """Crée une ligne pour afficher un match dans l'historique."""
    home = match.get('home')
    away = match.get('away')
    home_score = match.get('home_score')
    away_score = match.get('away_score')
    league = match.get('league', 'N/A')
    
    is_home = (home == club_name)
    opponent = away if is_home else home
    
    # Déterminer le résultat
    if is_home:
        if home_score > away_score:
            result_class = "win"
            result_symbol = "W"
        elif home_score == away_score:
            result_class = "draw"
            result_symbol = "D"
        else:
            result_class = "loss"
            result_symbol = "L"
        score_text = f"{home_score} - {away_score}"
    else:
        if away_score > home_score:
            result_class = "win"
            result_symbol = "W"
        elif away_score == home_score:
            result_class = "draw"
            result_symbol = "D"
        else:
            result_class = "loss"
            result_symbol = "L"
        score_text = f"{away_score} - {home_score}"
    
    return html.Div([
        html.Div([
            html.Span(
                result_symbol,
                className=f"form-indicator {result_class}",
                style={'marginRight': '1rem', 'width': '40px', 'height': '40px', 'fontSize': '1rem'}
            ),
            html.Div([
                html.Span(f"vs {opponent}", style={'fontWeight': '600', 'fontSize': '1.1rem', 'color': '#2d3748'}),
                html.Span(league, className="text-muted", style={'fontSize': '0.85rem', 'marginLeft': '1rem'})
            ], style={'flex': '1'}),
            html.Span(
                score_text,
                style={
                    'fontSize': '1.3rem',
                    'fontWeight': '700',
                    'color': '#2563eb',
                    'padding': '0.5rem 1.2rem',
                    'background': '#f8fafc',
                    'borderRadius': '12px',
                    'border': '1px solid #e2e8f0'
                }
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '1rem'})
    ], style={
        'padding': '1.2rem',
        'marginBottom': '0.8rem',
        'background': 'white',
        'borderRadius': '12px',
        'border': '1px solid #e2e8f0',
        'transition': 'all 0.2s ease'
    }, className="match-row-hover")
