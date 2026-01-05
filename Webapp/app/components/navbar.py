"""Composant Navbar utilisé dans toutes les pages Dash."""

from dash import html, dcc


def create_navbar(current_page="home"):
    """Create the navigation bar.

    Args:
        current_page: Page key used to highlight the active link.

    Returns:
        A Dash HTML container for the navbar.
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
                                    html.Span("Coupes", className="nav-text"),
                                ],
                                href="/cups",
                                className=f"nav-link {'active' if current_page == 'cups' else ''}",
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
