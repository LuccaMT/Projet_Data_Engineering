"""
Page de détail d'un club avec statistiques et graphiques
"""
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
        marker=dict(
            colors=['#10b981', '#94a3b8', '#ef4444'],
            line=dict(color='#ffffff', width=2)
        ),
        hole=0.45,
        textinfo='percent+label',
        textfont=dict(size=13, family='Inter'),
        hoverinfo='label+value+percent',
        pull=[0.03, 0, 0.03]
    )])
    results_pie.update_layout(
        title=dict(text='Répartition des résultats', font=dict(size=16, family='Inter', color='#0f172a')),
        height=370,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5, font=dict(size=12)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=40, l=20, r=20)
    )
    
    # 2. Bar chart buts pour/contre
    goals_bar = go.Figure(data=[
        go.Bar(
            name='Buts marqués', x=['Bilan'], y=[goals_for],
            marker=dict(color='#10b981', cornerradius=6),
            text=[str(goals_for)], textposition='outside',
            textfont=dict(size=14, family='Inter', color='#10b981')
        ),
        go.Bar(
            name='Buts encaissés', x=['Bilan'], y=[goals_against],
            marker=dict(color='#ef4444', cornerradius=6),
            text=[str(goals_against)], textposition='outside',
            textfont=dict(size=14, family='Inter', color='#ef4444')
        )
    ])
    goals_bar.update_layout(
        title=dict(text='Attaque vs Défense', font=dict(size=16, family='Inter', color='#0f172a')),
        yaxis=dict(title='Nombre de buts', gridcolor='rgba(0,0,0,0.04)', zeroline=False),
        xaxis=dict(showticklabels=False),
        height=370,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=-0.15, xanchor='center', x=0.5, font=dict(size=12)),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=40, l=50, r=20),
        barmode='group',
        bargap=0.35
    )
    
    # 3. Line chart forme récente (derniers 20 matchs) + calcul forme séparée (championnat vs coupes)
    form_data_all = []
    form_labels_all = []
    
    # Séparer les matchs par type
    form_data_league = []  # Championnat
    form_labels_league = []
    recent_form_league = []
    
    form_data_cups = []  # Coupes
    form_labels_cups = []
    recent_form_cups = []
    
    # Mots-clés pour identifier les championnats vs coupes
    league_keywords = ['Premier League', 'LaLiga', 'Serie A', 'Bundesliga', 'Ligue 1']
    cup_keywords = ['Cup', 'Coupe', 'Copa', 'Coppa', 'Pokal', 'Champions League', 'Europa League', 'Conference League']
    
    for match in matches_history[::-1]:  # Du plus ancien au plus récent
        home = match.get('home')
        away = match.get('away')
        home_score = match.get('home_score')
        away_score = match.get('away_score')
        league = match.get('league', '')
        
        # Déterminer si c'est un championnat ou une coupe
        is_league_match = any(keyword in league for keyword in league_keywords)
        is_cup_match = any(keyword in league for keyword in cup_keywords)
        
        if home == club_name:
            if home_score > away_score:
                result = 3  # Victoire
                result_letter = 'W'
                opponent = away
            elif home_score == away_score:
                result = 1  # Nul
                result_letter = 'D'
                opponent = away
            else:
                result = 0  # Défaite
                result_letter = 'L'
                opponent = away
        else:
            if away_score > home_score:
                result = 3  # Victoire
                result_letter = 'W'
                opponent = home
            elif away_score == home_score:
                result = 1  # Nul
                result_letter = 'D'
                opponent = home
            else:
                result = 0  # Défaite
                result_letter = 'L'
                opponent = home
        
        # Ajouter aux données globales
        form_data_all.append(result)
        form_labels_all.append(f"vs {opponent}")
        
        # Ajouter aux données spécifiques
        if is_league_match:
            form_data_league.append(result)
            form_labels_league.append(f"vs {opponent}")
            recent_form_league.append(result_letter)
        elif is_cup_match:
            form_data_cups.append(result)
            form_labels_cups.append(f"vs {opponent}")
            recent_form_cups.append(result_letter)
    
    # Fonction helper pour calculer les métriques
    def calculate_form_metrics(form_points, form_results, max_matches=5):
        """Calcule les métriques de forme pour un ensemble de matchs."""
        last_n_form = form_results[-max_matches:] if len(form_results) >= max_matches else form_results
        last_n_points = form_points[-max_matches:] if len(form_points) >= max_matches else form_points
        
        if last_n_points:
            avg_points = sum(last_n_points) / len(last_n_points)
            max_possible = len(last_n_points) * 3
            percentage = (sum(last_n_points) / max_possible * 100) if max_possible > 0 else 0
            
            # Déterminer l'état de forme
            if percentage >= 80:
                status = "Excellente"
                emoji = "🔥"
                color = "#10b981"
            elif percentage >= 60:
                status = "Bonne"
                emoji = "✅"
                color = "#059669"
            elif percentage >= 40:
                status = "Moyenne"
                emoji = "➖"
                color = "#f59e0b"
            elif percentage >= 20:
                status = "Difficile"
                emoji = "⚠️"
                color = "#ef4444"
            else:
                status = "Critique"
                emoji = "🚨"
                color = "#dc2626"
        else:
            avg_points = 0
            percentage = 0
            status = "N/A"
            emoji = "❓"
            color = "#94a3b8"
            last_n_form = []
        
        return {
            'form': last_n_form,
            'points': last_n_points,
            'avg': avg_points,
            'percentage': percentage,
            'status': status,
            'emoji': emoji,
            'color': color
        }
    
    # Calculer les métriques pour championnat et coupes
    league_metrics = calculate_form_metrics(form_data_league, recent_form_league, 5)
    cups_metrics = calculate_form_metrics(form_data_cups, recent_form_cups, 5)
    
    # Couleurs par résultat pour les marqueurs
    marker_colors = ['#10b981' if v == 3 else '#94a3b8' if v == 1 else '#ef4444' for v in form_data_all]
    
    form_line = go.Figure()
    form_line.add_trace(go.Scatter(
        x=list(range(len(form_data_all))),
        y=form_data_all,
        mode='lines+markers',
        line=dict(color='#2563eb', width=3, shape='spline'),
        marker=dict(size=12, color=marker_colors, line=dict(width=2, color='white')),
        text=form_labels_all,
        hovertemplate='<b>%{text}</b><br>Points: %{y}<extra></extra>',
        fill='tozeroy',
        fillcolor='rgba(37, 99, 235, 0.06)'
    ))
    form_line.update_layout(
        title=dict(text='Courbe de forme (20 derniers matchs)', font=dict(size=16, family='Inter', color='#0f172a')),
        xaxis=dict(title='Matchs', showgrid=False),
        yaxis=dict(
            title='Résultat',
            tickmode='array', tickvals=[0, 1, 3],
            ticktext=['Défaite', 'Nul', 'Victoire'],
            gridcolor='rgba(0,0,0,0.04)', zeroline=False
        ),
        height=370,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        hovermode='x unified',
        margin=dict(t=50, b=40, l=60, r=20)
    )
    
    # ========== LAYOUT ==========
    
    # ========== INTERFACE MODERNE ==========
    return html.Div([
        # Header moderne avec le nom du club
        html.Div([
            html.Div([
                html.Div([
                    html.Img(
                        src=club.get('logo', ''),
                        className="compare-club-logo",
                        style={'width': '100px', 'height': '100px', 'maxWidth': '100%'}
                    )
                ]) if club.get('logo') else None,
                html.Div([
                    html.H1(club_name, className="club-detail-title", style={'marginBottom': '0.5rem'}),
                    html.Div([
                        html.Span(
                            league,
                            style={
                                'display': 'inline-block',
                                'padding': '0.35rem 1rem',
                                'borderRadius': '9999px',
                                'background': '#eff6ff',
                                'color': '#1e40af',
                                'fontSize': '0.9rem',
                                'fontWeight': '600',
                                'marginRight': '0.5rem',
                                'marginBottom': '0.25rem'
                            }
                        ) for league in leagues
                    ], style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '0.25rem'})
                ])
            ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'justifyContent': 'center', 'gap': '1rem', 'position': 'relative', 'zIndex': '1'})
        ], className="club-detail-header"),
        
        # Statistiques rapides en grille moderne
        html.Div([
            create_detail_stat_card("📊", str(total), "Matchs joués", None),
            create_detail_stat_card("🏆", f"{win_rate:.1f}%", "Taux de victoire", '#2563eb'),
            create_detail_stat_card("⚽", f"{goals_for}", "Buts marqués", '#10b981'),
            create_detail_stat_card("🛡️", f"{goals_against}", "Buts encaissés", '#f59e0b'),
            create_detail_stat_card("📈", f"{goal_diff:+d}", "Différence de buts", '#10b981' if goal_diff >= 0 else '#ef4444'),
        ], className="stats-grid", style={'gap': '1rem', 'margin': '2rem 0'}),
        
        # Bilan détaillé avec forme récente séparée (Championnat vs Coupes)
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H3("📊 Bilan complet", className="chart-title"),
                    html.Div([
                        html.Div([
                            html.Div(str(wins), className="stat-value", style={'fontSize': '2.5rem', 'color': '#10b981', 'marginBottom': '0.25rem'}),
                            html.Div("Victoires", className="stat-label")
                        ], className="stat-item", style={'background': '#f0fdf4', 'border': '1px solid #bbf7d0'}),
                        html.Div([
                            html.Div(str(draws), className="stat-value", style={'fontSize': '2.5rem', 'color': '#64748b', 'marginBottom': '0.25rem'}),
                            html.Div("Nuls", className="stat-label")
                        ], className="stat-item", style={'background': '#f8fafc', 'border': '1px solid #e2e8f0'}),
                        html.Div([
                            html.Div(str(losses), className="stat-value", style={'fontSize': '2.5rem', 'color': '#ef4444', 'marginBottom': '0.25rem'}),
                            html.Div("Défaites", className="stat-label")
                        ], className="stat-item", style={'background': '#fef2f2', 'border': '1px solid #fecaca'})
                    ], className="stats-grid", style={'gridTemplateColumns': '1fr 1fr 1fr'})
                ], className="modern-chart-container", style={'height': '100%'})
            ], md=12)
        ], className="mb-4"),
        
        # Forme récente séparée : Championnat vs Coupes (même ligne, responsive)
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H3("🏆 Forme Championnat", className="chart-title", style={'fontSize': '1.1rem'}),
                    # Indicateurs de résultats
                    html.Div([
                        html.Span(
                            result,
                            className=f"form-indicator {'win' if result == 'W' else 'draw' if result == 'D' else 'loss'}",
                            title=f"{'Victoire' if result == 'W' else 'Nul' if result == 'D' else 'Défaite'}"
                        ) for result in league_metrics['form']
                    ] if league_metrics['form'] else [html.P("Aucun match", className="text-muted", style={'fontSize': '0.9rem', 'textAlign': 'center', 'margin': '1rem 0'})],
                        className="form-indicators",
                        style={'justifyContent': 'center', 'padding': '0.8rem 0.5rem', 'gap': '0.4rem', 'marginBottom': '1rem'}
                    ),
                    # Métriques de forme
                    html.Div([
                        html.Div([
                            html.Div(league_metrics['emoji'], style={'fontSize': '2rem', 'marginBottom': '0.4rem'}),
                            html.Div(league_metrics['status'], style={
                                'fontSize': '1.2rem',
                                'fontWeight': '700',
                                'color': league_metrics['color'],
                                'marginBottom': '0.2rem'
                            }),
                            html.Div(f"{league_metrics['percentage']:.0f}% efficacité", style={
                                'fontSize': '0.85rem',
                                'color': '#64748b',
                                'fontWeight': '500'
                            })
                        ], style={'textAlign': 'center'}),
                        html.Div([
                            html.Div([
                                html.Span(f"{league_metrics['avg']:.1f}", style={
                                    'fontSize': '1.6rem',
                                    'fontWeight': '700',
                                    'color': '#2563eb'
                                }),
                                html.Span(" / 3", style={
                                    'fontSize': '0.9rem',
                                    'color': '#94a3b8',
                                    'fontWeight': '500'
                                })
                            ], style={'marginBottom': '0.2rem'}),
                            html.Div("Points moyens", style={
                                'fontSize': '0.8rem',
                                'color': '#64748b',
                                'fontWeight': '500'
                            })
                        ], style={'textAlign': 'center', 'marginTop': '0.8rem'})
                    ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'padding': '0.5rem 0'})
                ], className="modern-chart-container", style={'height': '100%', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})
            ], width=12, md=6, className="mb-3", style={'flex': '1 1 420px', 'maxWidth': '100%', 'padding': '0'}),
            dbc.Col([
                html.Div([
                    html.H3("🏅 Forme Coupes", className="chart-title", style={'fontSize': '1.1rem'}),
                    # Indicateurs de résultats
                    html.Div([
                        html.Span(
                            result,
                            className=f"form-indicator {'win' if result == 'W' else 'draw' if result == 'D' else 'loss'}",
                            title=f"{'Victoire' if result == 'W' else 'Nul' if result == 'D' else 'Défaite'}"
                        ) for result in cups_metrics['form']
                    ] if cups_metrics['form'] else [html.P("Aucun match", className="text-muted", style={'fontSize': '0.9rem', 'textAlign': 'center', 'margin': '1rem 0'})],
                        className="form-indicators",
                        style={'justifyContent': 'center', 'padding': '0.8rem 0.5rem', 'gap': '0.4rem', 'marginBottom': '1rem'}
                    ),
                    # Métriques de forme
                    html.Div([
                        html.Div([
                            html.Div(cups_metrics['emoji'], style={'fontSize': '2rem', 'marginBottom': '0.4rem'}),
                            html.Div(cups_metrics['status'], style={
                                'fontSize': '1.2rem',
                                'fontWeight': '700',
                                'color': cups_metrics['color'],
                                'marginBottom': '0.2rem'
                            }),
                            html.Div(f"{cups_metrics['percentage']:.0f}% efficacité", style={
                                'fontSize': '0.85rem',
                                'color': '#64748b',
                                'fontWeight': '500'
                            })
                        ], style={'textAlign': 'center'}),
                        html.Div([
                            html.Div([
                                html.Span(f"{cups_metrics['avg']:.1f}", style={
                                    'fontSize': '1.6rem',
                                    'fontWeight': '700',
                                    'color': '#7c3aed'
                                }),
                                html.Span(" / 3", style={
                                    'fontSize': '0.9rem',
                                    'color': '#94a3b8',
                                    'fontWeight': '500'
                                })
                            ], style={'marginBottom': '0.2rem'}),
                            html.Div("Points moyens", style={
                                'fontSize': '0.8rem',
                                'color': '#64748b',
                                'fontWeight': '500'
                            })
                        ], style={'textAlign': 'center', 'marginTop': '0.8rem'})
                    ], style={'display': 'flex', 'flexDirection': 'column', 'alignItems': 'center', 'padding': '0.5rem 0'})
                ], className="modern-chart-container", style={'height': '100%', 'display': 'flex', 'flexDirection': 'column', 'justifyContent': 'center'})
            ], width=12, md=6, className="mb-3", style={'flex': '1 1 420px', 'maxWidth': '100%', 'padding': '0'})
        ], className="mb-4", style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '1rem', 'margin': '0'}),
        
        # Graphiques interactifs
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Graph(figure=results_pie, config={'displayModeBar': False, 'responsive': True})
                ], className="modern-chart-container")
            ], width=12, md=6, className="mb-3", style={'flex': '1 1 520px', 'maxWidth': '100%', 'padding': '0'}),
            dbc.Col([
                html.Div([
                    dcc.Graph(figure=goals_bar, config={'displayModeBar': False, 'responsive': True})
                ], className="modern-chart-container")
            ], width=12, md=6, className="mb-3", style={'flex': '1 1 520px', 'maxWidth': '100%', 'padding': '0'})
        ], className="mb-3", style={'display': 'flex', 'flexWrap': 'wrap', 'gap': '1rem', 'margin': '0'}),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Graph(figure=form_line, config={'displayModeBar': False, 'responsive': True})
                ], className="modern-chart-container")
            ], width=12, className="mb-3")
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
            html.Div(className="section-separator"),
            dbc.Button(
                ["⚖️  Comparer avec un autre club"],
                href=f"/clubs/compare?club1={club_name}",
                className="modern-btn modern-btn-primary",
                style={
                    'width': '100%', 'maxWidth': '420px',
                    'margin': '0 auto', 'display': 'block',
                    'fontSize': '1.1rem', 'padding': '1.1rem 2rem',
                    'borderRadius': '14px',
                    'background': 'linear-gradient(135deg, #2563eb 0%, #7c3aed 100%)',
                    'boxShadow': '0 8px 30px rgba(37, 99, 235, 0.2)'
                }
            )
        ], style={'marginTop': '3rem', 'textAlign': 'center', 'paddingBottom': '2rem'})
    ])


def create_detail_stat_card(icon, value, label, color):
    """Crée une carte de stat moderne pour la page de détail."""
    return html.Div([
        html.Div(icon, style={'fontSize': '2rem', 'marginBottom': '0.75rem'}),
        html.Div(
            str(value), className="stat-value",
            style={
                'fontSize': '2.5rem',
                'color': color if color else '#0f172a',
                'marginBottom': '0.25rem'
            }
        ),
        html.Div(label, className="stat-label")
    ], className="stat-item", style={'padding': '1.5rem'})


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
                style={'width': '38px', 'height': '38px', 'fontSize': '0.9rem', 'flexShrink': '0'}
            ),
            html.Div([
                html.Span(f"vs {opponent}", style={
                    'fontWeight': '600', 'fontSize': '1rem', 'color': '#0f172a',
                    'overflow': 'hidden', 'textOverflow': 'ellipsis', 'whiteSpace': 'nowrap'
                }),
                html.Span(
                    league,
                    style={
                        'fontSize': '0.75rem', 'flexShrink': '0',
                        'padding': '0.2rem 0.6rem', 'background': '#f1f5f9',
                        'borderRadius': '9999px', 'color': '#64748b', 'fontWeight': '500'
                    }
                )
            ], style={'flex': '1', 'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap', 'gap': '0.5rem', 'minWidth': '0', 'overflow': 'hidden'}),
            html.Span(
                score_text,
                className="score-bubble"
            )
        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '1rem'})
    ], className="detail-match-row")
