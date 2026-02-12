"""Page d'accueil du projet : présentation et description."""

from dash import dcc, html
from components.navbar import create_navbar


def create_layout():
    """Crée le layout de la page d'accueil."""
    return html.Div(
        className="app-wrapper",
        children=[
            # Hero Section
            html.Div(
                className="hero-section",
                style={
                    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    "padding": "60px 20px",
                    "textAlign": "center",
                    "color": "white"
                },
                children=[
                    html.Img(
                        src="/assets/logo.png",
                        style={
                            "height": "80px",
                            "marginBottom": "20px"
                        }
                    ),
                    html.H1(
                        "Flashscore Football Dashboard",
                        style={"fontSize": "48px", "fontWeight": "700", "marginBottom": "20px"}
                    ),
                    html.P(
                        "Projet Data Engineering - ESIEE Paris",
                        style={"fontSize": "24px", "opacity": "0.9", "marginBottom": "10px"}
                    ),
                    html.P(
                        "Scraping, stockage et visualisation de données football en temps réel",
                        style={"fontSize": "18px", "opacity": "0.8", "marginBottom": "5px"}
                    ),
                    html.P(
                        "Réalisé par Rayan Ben Tanfous et Lucca Matsumoto",
                        style={"fontSize": "18px", "opacity": "0.8"}
                    ),
                ]
            ),
            
            # Navbar
            create_navbar(current_page="home"),
            
            # Main Content
            html.Div(
                className="main-content",
                style={"maxWidth": "1200px", "margin": "0 auto", "padding": "0 40px", "marginTop": "40px"},
                children=[
                    # Description du projet
                    html.Div(
                        className="content-card",
                        style={
                            "background": "white",
                            "borderRadius": "12px",
                            "padding": "40px",
                            "marginBottom": "30px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.1)"
                        },
                        children=[
                            html.H2(
                                "📖 À propos du projet 📖",
                                style={"color": "#1e293b", "marginBottom": "20px", "textAlign": "center"}
                            ),
                            html.P(
                                "Ce projet est une application web complète de Data Engineering qui collecte, stocke et visualise "
                                "des données de matchs de football depuis Flashscore.fr en temps réel. "
                                "L'application permet de suivre les matchs en direct, consulter les résultats passés, "
                                "explorer les classements des ligues et les brackets des compétitions à élimination directe.",
                                style={"fontSize": "16px", "lineHeight": "1.6", "marginBottom": "15px", "textAlign": "center"}
                            ),
                            html.Div(
                                style={"display": "flex", "gap": "20px", "marginTop": "30px", "flexWrap": "wrap", "justifyContent": "flex-start"},
                                children=[
                                    html.Div(
                                        style={"flex": "1", "minWidth": "250px"},
                                        children=[
                                            html.H4("🎯 Objectifs", style={"color": "#3b82f6", "marginBottom": "10px"}),
                                            html.Ul(
                                                style={"lineHeight": "1.8", "paddingLeft": "30px"},
                                                children=[
                                                    html.Li("Scraping automatisé de données sportives"),
                                                    html.Li("Stockage efficace avec MongoDB"),
                                                    html.Li("Visualisation interactive temps réel"),
                                                    html.Li("Architecture Docker containerisée"),
                                                ]
                                            )
                                        ]
                                    ),
                                    html.Div(
                                        style={"flex": "1", "minWidth": "250px"},
                                        children=[
                                            html.H4("✨ Fonctionnalités", style={"color": "#3b82f6", "marginBottom": "10px"}),
                                            html.Ul(
                                                style={"lineHeight": "1.8", "paddingLeft": "30px"},
                                                children=[
                                                    html.Li("Matchs en direct et statistiques"),
                                                    html.Li("Classements des ligues (Top 5)"),
                                                    html.Li("Brackets des compétitions à élimination"),
                                                    html.Li("Filtrage avancé par date et ligue/coupe"),
                                                    html.Li("Recherche de clubs, comparaison et statistiques détaillées"),
                                                ]
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ]
                    ),
                    
                    # Technologies utilisées
                    html.Div(
                        className="content-card",
                        style={
                            "background": "white",
                            "borderRadius": "12px",
                            "padding": "40px",
                            "marginBottom": "30px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.1)"
                        },
                        children=[
                            html.H2(
                                "🔧 Technologies utilisées",
                                style={"color": "#1e293b", "marginBottom": "30px", "textAlign": "center"}
                            ),
                            html.Div(
                                style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(300px, 1fr))", "gap": "20px"},
                                children=[
                                    # Backend
                                    html.Div(
                                        style={"padding": "20px", "background": "#f8fafc", "borderRadius": "8px"},
                                        children=[
                                            html.H4("⚙️ Backend & Scraping", style={"color": "#059669", "marginBottom": "15px", "textAlign": "center"}),
                                            html.Ul(
                                                style={"lineHeight": "1.8", "fontSize": "15px", "paddingLeft": "25px"},
                                                children=[
                                                    html.Li([html.Strong("Python"), " - Langage principal"]),
                                                    html.Li([html.Strong("Scrapy"), " - Framework de web scraping"]),
                                                    html.Li([html.Strong("Selenium"), " - Scraping dynamique JavaScript"]),
                                                    html.Li([html.Strong("BeautifulSoup"), " - Parsing HTML"]),
                                                ]
                                            )
                                        ]
                                    ),
                                    # Database
                                    html.Div(
                                        style={"padding": "20px", "background": "#f8fafc", "borderRadius": "8px"},
                                        children=[
                                            html.H4("🗄️ Base de données", style={"color": "#059669", "marginBottom": "15px", "textAlign": "center"}),
                                            html.Ul(
                                                style={"lineHeight": "1.8", "fontSize": "15px", "paddingLeft": "25px"},
                                                children=[
                                                    html.Li([html.Strong("MongoDB 7.0"), " - Base NoSQL"]),
                                                    html.Li([html.Strong("PyMongo"), " - Driver Python MongoDB"]),
                                                    html.Li([html.Strong("Elasticsearch"), " - Moteur de recherche et indexation"]),
                                                ]
                                            )
                                        ]
                                    ),
                                    # Frontend
                                    html.Div(
                                        style={"padding": "20px", "background": "#f8fafc", "borderRadius": "8px"},
                                        children=[
                                            html.H4("🎨 Frontend", style={"color": "#059669", "marginBottom": "15px", "textAlign": "center"}),
                                            html.Ul(
                                                style={"lineHeight": "1.8", "fontSize": "15px", "paddingLeft": "25px"},
                                                children=[
                                                    html.Li([html.Strong("Dash/Plotly"), " - Framework web interactif"]),
                                                    html.Li([html.Strong("Pandas"), " - Manipulation de données"]),
                                                    html.Li([html.Strong("HTML/CSS"), " - Interface utilisateur"]),
                                                ]
                                            )
                                        ]
                                    ),
                                    # DevOps
                                    html.Div(
                                        style={"padding": "20px", "background": "#f8fafc", "borderRadius": "8px", "gridColumn": "2 / 3"},
                                        children=[
                                            html.H4("🐳 DevOps & Infrastructure", style={"color": "#059669", "marginBottom": "15px", "textAlign": "center"}),
                                            html.Ul(
                                                style={"lineHeight": "1.8", "fontSize": "15px", "paddingLeft": "25px"},
                                                children=[
                                                    html.Li([html.Strong("Docker"), " - Containerisation"]),
                                                    html.Li([html.Strong("Docker Compose"), " - Orchestration"]),
                                                    html.Li([html.Strong("Git"), " - Contrôle de version"]),
                                                ]
                                            )
                                        ]
                                    ),
                                ]
                            )
                        ]
                    ),
                    
                    # Vidéo de présentation
                    html.Div(
                        className="content-card",
                        style={
                            "background": "white",
                            "borderRadius": "12px",
                            "padding": "40px",
                            "marginBottom": "40px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.1)"
                        },
                        children=[
                            html.H2(
                                "🎥 Vidéo de présentation",
                                style={"color": "#1e293b", "marginBottom": "20px", "textAlign": "center"}
                            ),
                            html.Div(
                                style={
                                    "width": "100%",
                                    "maxWidth": "800px",
                                    "margin": "0 auto",
                                    "aspectRatio": "16/9",
                                    "background": "#f1f5f9",
                                    "borderRadius": "8px",
                                    "display": "flex",
                                    "alignItems": "center",
                                    "justifyContent": "center",
                                    "border": "2px dashed #cbd5e1"
                                },
                                children=[
                                    html.Div(
                                        style={"textAlign": "center", "color": "#64748b"},
                                        children=[
                                            html.Div("🎬", style={"fontSize": "48px", "marginBottom": "10px"}),
                                            html.P(
                                                "Espace réservé pour la vidéo de présentation",
                                                style={"fontSize": "16px", "margin": "0"}
                                            ),
                                            html.P(
                                                "(Format 16:9 - À ajouter ultérieurement)",
                                                style={"fontSize": "14px", "opacity": "0.7", "marginTop": "5px"}
                                            )
                                        ]
                                    )
                                ]
                            ),         
                        ]
                    ),
                    
                    # Call to action
                    html.Div(
                        style={"textAlign": "center", "padding": "40px 20px"},
                        children=[
                            html.H3(
                                "Prêt à explorer les données ?",
                                style={"color": "#1e293b", "marginBottom": "20px"}
                            ),
                            dcc.Link(
                                html.Button(
                                    "🔴 Voir les matchs en direct",
                                    style={
                                        "padding": "15px 40px",
                                        "fontSize": "18px",
                                        "fontWeight": "600",
                                        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                                        "color": "white",
                                        "border": "none",
                                        "borderRadius": "8px",
                                        "cursor": "pointer",
                                        "boxShadow": "0 4px 12px rgba(102, 126, 234, 0.4)",
                                        "transition": "transform 0.2s"
                                    }
                                ),
                                href="/live"
                            )
                        ]
                    )
                ]
            )
        ]
    )


layout = create_layout()
