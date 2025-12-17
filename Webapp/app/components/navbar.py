"""
Composant Navbar pour la navigation entre les pages
"""
from dash import html, dcc


def create_navbar(current_page="home"):
    """
    Crée une navbar simple avec navigation
    
    Args:
        current_page: Page actuellement active ("home" ou "leagues")
    """
    return html.Div(
        className="navbar-container",
        children=[
            html.Div(
                className="navbar-content",
                children=[
                    # Menu de navigation centré
                    html.Nav(
                        className="navbar-menu",
                        children=[
                            dcc.Link(
                                [
                                    html.Span("🏠", className="nav-icon"),
                                    html.Span("Accueil", className="nav-text"),
                                ],
                                href="/",
                                className=f"nav-link {'active' if current_page == 'home' else ''}",
                            ),
                            dcc.Link(
                                [
                                    html.Span("🏆", className="nav-icon"),
                                    html.Span("Ligues", className="nav-text"),
                                ],
                                href="/leagues",
                                className=f"nav-link {'active' if current_page == 'leagues' else ''}",
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
