"""
Page de comparaison entre deux clubs avec graphiques
"""
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
                    ], xs=12, md=5),
                    dbc.Col([
                        html.Div(
                            "VS",
                            style={
                                'textAlign': 'center',
                                'fontSize': '1.5rem',
                                'fontWeight': '800',
                                'color': '#2563eb',
                                'padding': '1rem 0'
                            }
                        )
                    ], xs=12, md=2),
                    dbc.Col([
                        html.Label("🏆 Second club", style={'fontWeight': '600', 'color': '#2d3748', 'marginBottom': '0.8rem', 'fontSize': '1.1rem'}),
                        dbc.Input(
                            id="compare-club2-input",
                            placeholder="Ex: Real Madrid, Barcelona...",
                            type="text",
                            className="modern-search-input"
                        ),
                    ], xs=12, md=5)
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
            marker=dict(color='#2563eb', cornerradius=6),
            text=[club1_data['wins'], club1_data['draws'], club1_data['losses']],
            textposition='outside', textfont=dict(size=13, family='Inter')
        ),
        go.Bar(
            name=club2,
            x=['Victoires', 'Nuls', 'Défaites'],
            y=[club2_data['wins'], club2_data['draws'], club2_data['losses']],
            marker=dict(color='#7c3aed', cornerradius=6),
            text=[club2_data['wins'], club2_data['draws'], club2_data['losses']],
            textposition='outside', textfont=dict(size=13, family='Inter')
        )
    ])
    results_comparison.update_layout(
        title=dict(text='Comparaison des résultats', font=dict(size=16, family='Inter', color='#0f172a')),
        barmode='group',
        height=420,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='rgba(0,0,0,0.04)', zeroline=False),
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5, font=dict(size=12)),
        margin=dict(t=50, b=50, l=40, r=20),
        bargap=0.25
    )
    
    # 2. Bar chart buts marqués vs encaissés
    goals_comparison = go.Figure(data=[
        go.Bar(
            name=f'{club1} – Marqués', x=[club1], y=[club1_data['goals_for']],
            marker=dict(color='#10b981', cornerradius=6),
            text=[club1_data['goals_for']], textposition='outside'
        ),
        go.Bar(
            name=f'{club1} – Encaissés', x=[club1], y=[club1_data['goals_against']],
            marker=dict(color='#ef4444', cornerradius=6),
            text=[club1_data['goals_against']], textposition='outside'
        ),
        go.Bar(
            name=f'{club2} – Marqués', x=[club2], y=[club2_data['goals_for']],
            marker=dict(color='#06b6d4', cornerradius=6),
            text=[club2_data['goals_for']], textposition='outside'
        ),
        go.Bar(
            name=f'{club2} – Encaissés', x=[club2], y=[club2_data['goals_against']],
            marker=dict(color='#f59e0b', cornerradius=6),
            text=[club2_data['goals_against']], textposition='outside'
        )
    ])
    goals_comparison.update_layout(
        title=dict(text='Buts marqués vs encaissés', font=dict(size=16, family='Inter', color='#0f172a')),
        barmode='group',
        height=420,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='rgba(0,0,0,0.04)', zeroline=False),
        legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5, font=dict(size=11)),
        margin=dict(t=50, b=60, l=40, r=20),
        bargap=0.2
    )
    
    # 3. Radar chart comparatif (taux de victoire, buts marqués, défense)
    categories = ['Taux de victoire', 'Attaque', 'Défense', 'Efficacité']
    
    # Normaliser les données pour le radar (échelle 0-100 pour chaque métrique)
    # 1. Taux de victoire: déjà en pourcentage
    # 2. Attaque: buts par match (normalisé sur 0-100, max = 4 buts/match = 100%)
    # 3. Défense: inverse des buts encaissés par match (normalisé sur 0-100, 0 buts encaissés = 100%)
    # 4. Efficacité: différence de buts par match (normalisé sur 0-100, +3 = 100%, -3 = 0%)
    
    # Calcul des moyennes par match
    club1_matches = max(club1_data['total_matches'], 1)
    club2_matches = max(club2_data['total_matches'], 1)
    
    club1_goals_per_match = club1_data['goals_for'] / club1_matches
    club2_goals_per_match = club2_data['goals_for'] / club2_matches
    
    club1_against_per_match = club1_data['goals_against'] / club1_matches
    club2_against_per_match = club2_data['goals_against'] / club2_matches
    
    club1_diff_per_match = club1_data['goal_difference'] / club1_matches
    club2_diff_per_match = club2_data['goal_difference'] / club2_matches
    
    # Normalisation intelligente
    # Attaque: 4 buts/match = 100%, 0 = 0%
    club1_attack_score = min((club1_goals_per_match / 4) * 100, 100)
    club2_attack_score = min((club2_goals_per_match / 4) * 100, 100)
    
    # Défense: 0 buts encaissés/match = 100%, 4 buts = 0%
    club1_defense_score = max(100 - (club1_against_per_match / 4) * 100, 0)
    club2_defense_score = max(100 - (club2_against_per_match / 4) * 100, 0)
    
    # Efficacité: +3 buts de diff/match = 100%, 0 = 50%, -3 = 0%
    club1_efficiency_score = min(max(((club1_diff_per_match + 3) / 6) * 100, 0), 100)
    club2_efficiency_score = min(max(((club2_diff_per_match + 3) / 6) * 100, 0), 100)
    
    club1_radar = [
        club1_data['win_rate'],
        club1_attack_score,
        club1_defense_score,
        club1_efficiency_score
    ]
    
    club2_radar = [
        club2_data['win_rate'],
        club2_attack_score,
        club2_defense_score,
        club2_efficiency_score
    ]
    
    radar_chart = go.Figure()
    radar_chart.add_trace(go.Scatterpolar(
        r=club1_radar,
        theta=categories,
        fill='toself',
        name=club1,
        line=dict(color='#2563eb', width=2),
        fillcolor='rgba(37, 99, 235, 0.12)',
        marker=dict(size=6)
    ))
    radar_chart.add_trace(go.Scatterpolar(
        r=club2_radar,
        theta=categories,
        fill='toself',
        name=club2,
        line=dict(color='#7c3aed', width=2),
        fillcolor='rgba(124, 58, 237, 0.12)',
        marker=dict(size=6)
    ))
    radar_chart.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], gridcolor='rgba(0,0,0,0.06)', tickfont=dict(size=10)),
            angularaxis=dict(tickfont=dict(size=12, family='Inter'))
        ),
        title=dict(text="Vue d'ensemble comparative", font=dict(size=16, family='Inter', color='#0f172a')),
        height=500,
        paper_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5, font=dict(size=13)),
        margin=dict(t=60, b=50)
    )
    
    # ========== LAYOUT ==========
    
    return club1, club2, html.Div([
        # Bannière de comparaison moderne
        html.Div([
            html.Div([
                html.Img(
                    src=club1_data.get('logo', ''),
                    className="compare-club-logo"
                ) if club1_data.get('logo') else None,
                html.H2(club1, className="compare-club-name"),
                html.P(' | '.join(club1_data.get('leagues', [])), className="compare-club-league")
            ], className="compare-club-side"),
            html.Div([
                html.Div("VS", className="vs-badge")
            ], style={'display': 'flex', 'alignItems': 'center', 'justifyContent': 'center', 'padding': '0 1.5rem'}),
            html.Div([
                html.Img(
                    src=club2_data.get('logo', ''),
                    className="compare-club-logo"
                ) if club2_data.get('logo') else None,
                html.H2(club2, className="compare-club-name"),
                html.P(' | '.join(club2_data.get('leagues', [])), className="compare-club-league")
            ], className="compare-club-side")
        ], className="compare-banner", style={'marginBottom': '2.5rem'}),
        
        # Statistiques comparatives
        html.Div([
            create_compare_stat_card(
                "📊", "Matchs joués",
                club1_data['total_matches'], club2_data['total_matches']
            ),
            create_compare_stat_card(
                "🏆", "Taux de victoire",
                f"{club1_data['win_rate']:.1f}%", f"{club2_data['win_rate']:.1f}%"
            ),
            create_compare_stat_card(
                "⚽", "Buts marqués",
                club1_data['goals_for'], club2_data['goals_for']
            ),
            create_compare_stat_card(
                "🛡️", "Buts encaissés",
                club1_data['goals_against'], club2_data['goals_against'],
                lower_is_better=True
            ),
            create_compare_stat_card(
                "📈", "Différence de buts",
                f"{club1_data['goal_difference']:+d}",
                f"{club2_data['goal_difference']:+d}"
            )
        ], className="stats-grid", style={'gap': '1rem', 'margin': '0 0 2.5rem 0'}),
        
        # Graphiques
        html.Div([
            html.Div([
                dcc.Graph(figure=results_comparison, config={'displayModeBar': False, 'responsive': True})
            ], className="modern-chart-container"),
            html.Div([
                dcc.Graph(figure=goals_comparison, config={'displayModeBar': False, 'responsive': True})
            ], className="modern-chart-container")
        ], className="charts-flex-row", style={'marginBottom': '1.5rem'}),
        
        html.Div([
            dcc.Graph(figure=radar_chart, config={'displayModeBar': False, 'responsive': True})
        ], className="modern-chart-container", style={'marginBottom': '2.5rem'}),
        
        # Confrontations directes
        html.Div([
            html.H3("🏆 Confrontations directes", className="chart-title"),
            html.Div([
                html.Div([
                    create_modern_h2h_row(match, club1) for match in head_to_head
                ] if head_to_head else [
                    html.Div([
                        html.Div("🏃", style={'fontSize': '3rem', 'marginBottom': '1rem'}),
                        html.P(
                            "Ces deux clubs ne se sont pas encore affrontés dans notre base de données.",
                            style={'color': '#64748b', 'textAlign': 'center', 'fontSize': '1.05rem', 'maxWidth': '400px', 'margin': '0 auto'}
                        )
                    ], style={'textAlign': 'center', 'padding': '3rem'})
                ])
            ])
        ], className="modern-chart-container", style={'marginBottom': '2rem'})
    ])


def create_compare_stat_card(icon, title, value1, value2, lower_is_better=False):
    """Crée une carte de statistique comparative moderne."""
    try:
        val1_num = float(str(value1).replace('%', '').replace('+', ''))
        val2_num = float(str(value2).replace('%', '').replace('+', ''))
        if lower_is_better:
            better1 = val1_num < val2_num
            better2 = val2_num < val1_num
        else:
            better1 = val1_num > val2_num
            better2 = val2_num > val1_num
    except Exception:
        better1 = better2 = False

    return html.Div([
        html.Div(icon, className="stat-compare-icon"),
        html.Div(title, className="stat-compare-label"),
        html.Div([
            html.Div(
                str(value1),
                className=f"stat-compare-val {'better' if better1 else 'normal'}"
            ),
            html.Div("vs", className="stat-compare-vs"),
            html.Div(
                str(value2),
                className=f"stat-compare-val {'better' if better2 else 'normal'}"
            )
        ], className="stat-compare-values")
    ], className="stat-compare-card")


def create_modern_h2h_row(match, club1):
    """Crée une ligne moderne pour afficher une confrontation directe."""
    home = match.get('home')
    away = match.get('away')
    home_score = match.get('home_score')
    away_score = match.get('away_score')
    league = match.get('league', 'N/A')
    
    # Déterminer le gagnant et les styles
    if home_score > away_score:
        winner = home
        home_style = {'fontWeight': '700', 'color': '#059669', 'fontSize': '1rem'}  # Gagnant en vert foncé et gras
        away_style = {'fontWeight': '500', 'color': '#94a3b8', 'fontSize': '0.9rem'}  # Perdant en gris
        score_home_style = {'background': '#d1fae5', 'color': '#059669', 'fontWeight': '700'}  # Score gagnant
        score_away_style = {'background': '#f1f5f9', 'color': '#94a3b8', 'fontWeight': '500'}  # Score perdant
    elif away_score > home_score:
        winner = away
        home_style = {'fontWeight': '500', 'color': '#94a3b8', 'fontSize': '0.9rem'}  # Perdant en gris
        away_style = {'fontWeight': '700', 'color': '#059669', 'fontSize': '1rem'}  # Gagnant en vert foncé et gras
        score_home_style = {'background': '#f1f5f9', 'color': '#94a3b8', 'fontWeight': '500'}  # Score perdant
        score_away_style = {'background': '#d1fae5', 'color': '#059669', 'fontWeight': '700'}  # Score gagnant
    else:
        winner = None
        home_style = {'fontWeight': '600', 'color': '#0f172a', 'fontSize': '0.95rem'}  # Nul - style normal
        away_style = {'fontWeight': '600', 'color': '#0f172a', 'fontSize': '0.95rem'}  # Nul - style normal
        score_home_style = {'background': '#fef3c7', 'color': '#d97706', 'fontWeight': '600'}  # Nul - jaune
        score_away_style = {'background': '#fef3c7', 'color': '#d97706', 'fontWeight': '600'}  # Nul - jaune
    
    # Ajouter un badge de résultat pour club1
    if winner == club1:
        result_badge = html.Span("✓ Victoire", className="form-indicator win",
                                 style={'padding': '0.4rem 0.8rem', 'fontSize': '0.8rem', 'width': 'auto', 'height': 'auto', 'flexShrink': '0'})
    elif winner and winner != club1:
        result_badge = html.Span("✗ Défaite", className="form-indicator loss",
                                 style={'padding': '0.4rem 0.8rem', 'fontSize': '0.8rem', 'width': 'auto', 'height': 'auto', 'flexShrink': '0'})
    else:
        result_badge = html.Span("= Nul", className="form-indicator draw",
                                 style={'padding': '0.4rem 0.8rem', 'fontSize': '0.8rem', 'width': 'auto', 'height': 'auto', 'flexShrink': '0'})
    
    return html.Div([
        result_badge,
        html.Span(home, style={
            **home_style,
            'flex': '1',
            'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap', 'minWidth': '0',
            'textAlign': 'left'
        }),
        html.Div([
            html.Span(str(home_score), className="score-bubble", style={
                **score_home_style,
                'padding': '0.3rem 0.7rem',
                'borderRadius': '6px',
                'minWidth': '32px',
                'textAlign': 'center'
            }),
            html.Span("–", style={'margin': '0 0.5rem', 'color': '#cbd5e1', 'fontWeight': '600', 'fontSize': '1.2rem'}),
            html.Span(str(away_score), className="score-bubble", style={
                **score_away_style,
                'padding': '0.3rem 0.7rem',
                'borderRadius': '6px',
                'minWidth': '32px',
                'textAlign': 'center'
            })
        ], style={'display': 'flex', 'alignItems': 'center', 'flexShrink': '0'}),
        html.Span(away, style={
            **away_style,
            'flex': '1',
            'textAlign': 'right',
            'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap', 'minWidth': '0'
        }),
        html.Span(
            league,
            style={
                'color': '#64748b', 'fontSize': '0.75rem', 'flexShrink': '0',
                'padding': '0.3rem 0.7rem', 'background': '#f8fafc',
                'borderRadius': '9999px', 'whiteSpace': 'nowrap', 'fontWeight': '500',
                'border': '1px solid #e2e8f0'
            }
        )
    ], className="detail-match-row")
