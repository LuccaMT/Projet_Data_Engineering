"""
Page de comparaison entre deux clubs avec graphiques
"""
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from urllib.parse import parse_qs
from components.navbar import create_navbar
from database import get_db_connection


def layout():
    """Layout de la page de comparaison de clubs."""
    return html.Div(
        className="club-page-wrapper compare",
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
                                html.P("Comparaison de clubs", style={"color": "rgba(255,255,255,0.9)"}),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        
        create_navbar(current_page="clubs"),
        
        dcc.Location(id='club-compare-url', refresh=False),
        
        dbc.Container([
            # Header moderne
            html.Div([
                html.Div("⚖️", className="search-title-icon"),
                html.H1("Comparaison de Clubs", className="search-title"),
                html.P(
                    "Comparez les performances de deux clubs côte à côte",
                    className="search-subtitle"
                )
            ], className="search-title-container", style={'marginTop': '2rem'}),
            
            # Formulaire de sélection moderne
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Label("⚽ Premier club", style={'fontWeight': '600', 'color': '#2d3748', 'marginBottom': '0.8rem', 'fontSize': '1.1rem'}),
                        dbc.Input(
                            id="compare-club1-input",
                            placeholder="Ex: Manchester City, PSG...",
                            type="text",
                            className="modern-search-input"
                        ),
                    ], md=5),
                    dbc.Col([
                        html.Div(
                            "VS",
                            style={
                                'textAlign': 'center',
                                'fontSize': '2rem',
                                'fontWeight': '800',
                                'color': '#2563eb',
                                'marginTop': '3rem'
                            }
                        )
                    ], md=2),
                    dbc.Col([
                        html.Label("🏆 Second club", style={'fontWeight': '600', 'color': '#2d3748', 'marginBottom': '0.8rem', 'fontSize': '1.1rem'}),
                        dbc.Input(
                            id="compare-club2-input",
                            placeholder="Ex: Real Madrid, Barcelona...",
                            type="text",
                            className="modern-search-input"
                        ),
                    ], md=5)
                ], className="align-items-end mb-4"),
                dbc.Button(
                    ["✨ Comparer les clubs"],
                    id="compare-button",
                    className="modern-search-button",
                    style={'width': '100%', 'maxWidth': '400px', 'margin': '0 auto', 'display': 'block'}
                )
            ], className="modern-search-container"),
            
            # Résultats de la comparaison
            dcc.Loading(
                id="club-compare-loading",
                type="circle",
                color="#2563eb",
                children=html.Div(id="club-compare-content")
            )
        ], fluid=True, className="px-4")
    ])


@callback(
    [Output("compare-club1-input", "value"),
     Output("compare-club2-input", "value"),
     Output("club-compare-content", "children")],
    [Input("club-compare-url", "search"),
     Input("compare-button", "n_clicks")],
    [State("compare-club1-input", "value"),
     State("compare-club2-input", "value")],
    prevent_initial_call=False
)
def display_comparison(search, n_clicks, club1_input, club2_input):
    """Affiche la comparaison entre deux clubs."""
    ctx = dash.callback_context
    
    # Si l'URL contient des paramètres, les utiliser
    club1 = club1_input
    club2 = club2_input
    
    if search and not n_clicks:
        params = parse_qs(search.lstrip('?'))
        club1 = params.get('club1', [club1_input])[0]
        club2 = params.get('club2', [club2_input])[0]
    
    # Vérifier si les clubs sont fournis
    if not club1 or not club2:
        return club1, club2, dbc.Alert(
            "Veuillez sélectionner deux clubs pour comparer.",
            color="info",
            className="text-center mt-4"
        )
    
    if club1 == club2:
        return club1, club2, dbc.Alert(
            "Veuillez sélectionner deux clubs différents.",
            color="warning",
            className="text-center mt-4"
        )
    
    # Récupérer les données de comparaison
    db = get_db_connection()
    comparison = db.compare_clubs(club1, club2)
    
    if not comparison:
        return club1, club2, dbc.Alert(
            f"Impossible de trouver les clubs « {club1} » ou « {club2} ».",
            color="danger",
            className="text-center mt-4"
        )
    
    club1_data = comparison['club1']
    club2_data = comparison['club2']
    head_to_head = comparison.get('head_to_head', [])
    
    # Utiliser le nom canonique renvoyé par l'index (utile en cas de fuzzy match)
    club1 = club1_data.get('name', club1)
    club2 = club2_data.get('name', club2)
    
    # ========== GRAPHIQUES COMPARATIFS ==========
    
    # 1. Bar chart comparatif des victoires/nuls/défaites
    results_comparison = go.Figure(data=[
        go.Bar(
            name=club1,
            x=['Victoires', 'Nuls', 'Défaites'],
            y=[club1_data['wins'], club1_data['draws'], club1_data['losses']],
            marker_color='#2563eb'
        ),
        go.Bar(
            name=club2,
            x=['Victoires', 'Nuls', 'Défaites'],
            y=[club2_data['wins'], club2_data['draws'], club2_data['losses']],
            marker_color='#7c3aed'
        )
    ])
    results_comparison.update_layout(
        title="Comparaison des résultats",
        barmode='group',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # 2. Bar chart buts marqués vs encaissés
    goals_comparison = go.Figure(data=[
        go.Bar(
            name=f'{club1} - Marqués',
            x=['Buts'],
            y=[club1_data['goals_for']],
            marker_color='#10b981'
        ),
        go.Bar(
            name=f'{club1} - Encaissés',
            x=['Buts'],
            y=[club1_data['goals_against']],
            marker_color='#ef4444'
        ),
        go.Bar(
            name=f'{club2} - Marqués',
            x=['Buts'],
            y=[club2_data['goals_for']],
            marker_color='#06b6d4'
        ),
        go.Bar(
            name=f'{club2} - Encaissés',
            x=['Buts'],
            y=[club2_data['goals_against']],
            marker_color='#f59e0b'
        )
    ])
    goals_comparison.update_layout(
        title="Comparaison des buts",
        barmode='group',
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    # 3. Radar chart comparatif (taux de victoire, buts marqués, défense)
    categories = ['Taux de victoire (%)', 'Buts marqués', 'Défense (buts encaissés inversé)', 'Différence de buts']
    
    # Normaliser les données pour le radar
    max_goals = max(club1_data['goals_for'], club2_data['goals_for'], 1)
    max_against = max(club1_data['goals_against'], club2_data['goals_against'], 1)
    max_diff = max(abs(club1_data['goal_difference']), abs(club2_data['goal_difference']), 1)
    
    club1_radar = [
        club1_data['win_rate'],
        (club1_data['goals_for'] / max_goals) * 100,
        ((max_against - club1_data['goals_against']) / max_against) * 100,
        ((club1_data['goal_difference'] + max_diff) / (2 * max_diff)) * 100
    ]
    
    club2_radar = [
        club2_data['win_rate'],
        (club2_data['goals_for'] / max_goals) * 100,
        ((max_against - club2_data['goals_against']) / max_against) * 100,
        ((club2_data['goal_difference'] + max_diff) / (2 * max_diff)) * 100
    ]
    
    radar_chart = go.Figure()
    radar_chart.add_trace(go.Scatterpolar(
        r=club1_radar,
        theta=categories,
        fill='toself',
        name=club1,
        line_color='#2563eb'
    ))
    radar_chart.add_trace(go.Scatterpolar(
        r=club2_radar,
        theta=categories,
        fill='toself',
        name=club2,
        line_color='#7c3aed'
    ))
    radar_chart.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="Vue d'ensemble comparative",
        height=500,
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    # ========== LAYOUT ==========
    
    return club1, club2, html.Div([
        # En-têtes des clubs
        html.Div([
            html.Div([
                html.Div([
                    html.Img(
                        src=club1_data.get('logo', ''),
                        style={'width': '100px', 'height': '100px', 'objectFit': 'contain', 'filter': 'drop-shadow(0 4px 6px rgba(0,0,0,0.1))'}
                    ) if club1_data.get('logo') else None,
                    html.H2(club1, style={'marginTop': '1rem', 'fontSize': '2rem', 'fontWeight': '700', 'color': '#2d3748'}),
                    html.P(' | '.join(club1_data.get('leagues', [])), style={'color': '#718096', 'fontSize': '0.95rem'})
                ], style={'textAlign': 'center'})
            ], style={'flex': '1'}),
            html.Div([
                html.Div("VS", className="vs-badge")
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 2rem'}),
            html.Div([
                html.Div([
                    html.Img(
                        src=club2_data.get('logo', ''),
                        style={'width': '100px', 'height': '100px', 'objectFit': 'contain', 'filter': 'drop-shadow(0 4px 6px rgba(0,0,0,0.1))'}
                    ) if club2_data.get('logo') else None,
                    html.H2(club2, style={'marginTop': '1rem', 'fontSize': '2rem', 'fontWeight': '700', 'color': '#2d3748'}),
                    html.P(' | '.join(club2_data.get('leagues', [])), style={'color': '#718096', 'fontSize': '0.95rem'})
                ], style={'textAlign': 'center'})
            ], style={'flex': '1'})
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'space-between', 'background': 'white', 'borderRadius': '20px', 'padding': '3rem 2rem', 'marginBottom': '3rem', 'boxShadow': '0 10px 30px rgba(0,0,0,0.1)'}),
        
        # Statistiques comparatives
        html.Div([
            create_modern_stat_card(
                "📊",
                "Matchs joués",
                club1_data['total_matches'],
                club2_data['total_matches']
            ),
            create_modern_stat_card(
                "🏆",
                "Taux de victoire",
                f"{club1_data['win_rate']:.1f}%",
                f"{club2_data['win_rate']:.1f}%"
            ),
            create_modern_stat_card(
                "⚽",
                "Buts marqués",
                club1_data['goals_for'],
                club2_data['goals_for']
            ),
            create_modern_stat_card(
                "📈",
                "Différence de buts",
                f"+{club1_data['goal_difference']}" if club1_data['goal_difference'] >= 0 else club1_data['goal_difference'],
                f"+{club2_data['goal_difference']}" if club2_data['goal_difference'] >= 0 else club2_data['goal_difference']
            )
        ], className="stats-grid", style={'gridTemplateColumns': 'repeat(auto-fit, minmax(200px, 1fr))', 'gap': '1.5rem', 'margin': '2rem 0 3rem 0'}),
        
        # Graphiques
        html.Div([
            html.Div([
                dcc.Graph(figure=results_comparison, config={'displayModeBar': False})
            ], className="modern-chart-container", style={'flex': '1'}),
            html.Div([
                dcc.Graph(figure=goals_comparison, config={'displayModeBar': False})
            ], className="modern-chart-container", style={'flex': '1'})
        ], style={'display': 'flex', 'gap': '2rem', 'marginBottom': '2rem'}),
        
        html.Div([
            dcc.Graph(figure=radar_chart, config={'displayModeBar': False})
        ], className="modern-chart-container", style={'marginBottom': '3rem'}),
        
        # Confrontations directes
        html.Div([
            html.H3("🏆 Confrontations directes", className="chart-title", style={'marginBottom': '1.5rem'}),
            html.Div([
                html.Div([
                    create_modern_h2h_row(match, club1, club2) for match in head_to_head
                ] if head_to_head else [
                    html.P(
                        "Ces deux clubs ne se sont pas encore affrontés dans notre base de données.",
                        style={'color': '#718096', 'textAlign': 'center', 'padding': '3rem', 'fontSize': '1.1rem'}
                    )
                ])
            ], style={'background': 'white', 'borderRadius': '15px', 'padding': '2rem', 'boxShadow': '0 4px 6px rgba(0,0,0,0.07)'})
        ], style={'marginBottom': '2rem'})
    ])


def create_modern_stat_card(icon, title, value1, value2):
    """Crée une carte de statistique comparative moderne."""
    # Déterminer quel club a le meilleur résultat
    try:
        val1_num = float(str(value1).replace('%', '').replace('+', ''))
        val2_num = float(str(value2).replace('%', '').replace('+', ''))
        better1 = val1_num > val2_num
        better2 = val2_num > val1_num
    except:
        better1 = better2 = False
    
    return html.Div([
        html.Div(icon, style={'fontSize': '2.5rem', 'marginBottom': '1rem', 'textAlign': 'center'}),
        html.Div(title, className="stat-label", style={'textAlign': 'center', 'marginBottom': '1rem'}),
        html.Div([
            html.Div([
                html.Div(
                    str(value1),
                    style={
                        'fontSize': '2rem',
                        'fontWeight': '700',
                        'color': '#2563eb' if better1 else '#2d3748'
                    }
                )
            ], style={'textAlign': 'center', 'flex': '1'}),
            html.Div(
                "vs",
                style={'fontSize': '1rem', 'color': '#a0aec0', 'padding': '0 1rem'}
            ),
            html.Div([
                html.Div(
                    str(value2),
                    style={
                        'fontSize': '2rem',
                        'fontWeight': '700',
                        'color': '#2563eb' if better2 else '#2d3748'
                    }
                )
            ], style={'textAlign': 'center', 'flex': '1'})
        ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center'})
    ], className="stat-item", style={'padding': '2rem', 'background': 'white', 'borderRadius': '15px', 'boxShadow': '0 4px 6px rgba(0,0,0,0.07)', 'transition': 'all 0.3s ease'})


def create_modern_h2h_row(match, club1, club2):
    """Crée une ligne moderne pour afficher une confrontation directe."""
    home = match.get('home')
    away = match.get('away')
    home_score = match.get('home_score')
    away_score = match.get('away_score')
    league = match.get('league', 'N/A')
    
    # Déterminer le gagnant
    if home_score > away_score:
        winner = home
        form_class = "win" if winner == club1 else "loss"
        form_letter = "V" if winner == club1 else "D"
    elif away_score > home_score:
        winner = away
        form_class = "win" if winner == club1 else "loss"
        form_letter = "V" if winner == club1 else "D"
    else:
        winner = None
        form_class = "draw"
        form_letter = "N"
    
    return html.Div([
        html.Span(form_letter, className=f"form-indicator {form_class}"),
        html.Span(home, style={'fontWeight': '600', 'flex': '1', 'color': '#2d3748'}),
        html.Div([
            html.Span(str(home_score), style={'fontSize': '1.2rem', 'fontWeight': '700', 'padding': '0.5rem 1rem', 'background': '#2563eb', 'color': 'white', 'borderRadius': '8px'}),
            html.Span("-", style={'margin': '0 0.5rem', 'color': '#a0aec0'}),
            html.Span(str(away_score), style={'fontSize': '1.2rem', 'fontWeight': '700', 'padding': '0.5rem 1rem', 'background': '#2563eb', 'color': 'white', 'borderRadius': '8px'})
        ], style={'display': 'flex', 'alignItems': 'center'}),
        html.Span(away, style={'fontWeight': '600', 'flex': '1', 'textAlign': 'right', 'color': '#2d3748'}),
        html.Span(f"({league})", style={'color': '#a0aec0', 'fontSize': '0.85rem', 'marginLeft': '1rem'})
    ], style={'display': 'flex', 'alignItems': 'center', 'gap': '1rem', 'padding': '1rem', 'borderBottom': '1px solid #e2e8f0', 'transition': 'all 0.2s ease'}, className="match-row-hover")
