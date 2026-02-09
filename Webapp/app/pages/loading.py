"""Page de chargement Dash affichée pendant l'initialisation des données initiales."""

from dash import html, dcc, callback, Input, Output
import os
from typing import Any, Dict, Optional, Tuple
from pymongo import MongoClient

def get_initialization_status():
    """Fetch initialization status from MongoDB.

    Returns:
        The status document without the MongoDB `_id` field, or None if unavailable.
    """
    try:
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://mongodb:27017/')
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        db = client['flashscore']
        
        # Retrieve status (never auto-create)
        status = db.initialization_status.find_one({}, {"_id": 0})
        
        client.close()
        return status
    except Exception as e:
        print(f"Error in get_initialization_status: {e}")
        return None

def layout():
    """Construit le layout de la page de chargement."""
    return html.Div(
        className="loading-page",
        children=[
            dcc.Interval(
                id='loading-interval',
                interval=2000,
                n_intervals=0
            ),
            html.Div(
                className="loading-container",
                children=[
                    html.Div(
                        className="loading-header",
                        children=[
                            html.H1("⚽ Flashscore Dashboard", className="loading-title"),
                            html.P("Initialisation en cours...", className="loading-subtitle"),
                        ]
                    ),
                    html.Div(id="loading-content"),
                ]
            )
        ]
    )

@callback(
    Output("loading-content", "children"),
    Output("loading-interval", "disabled"),
    Input("loading-interval", "n_intervals")
)
def update_loading_status(n):
    """Update the loading UI based on the initialization document.

    Args:
        n: Number of interval ticks.

    Returns:
        A tuple (children, disabled) where disabled stops the interval when ready.
    """
    status = get_initialization_status()
    
    # Define default steps
    default_steps = {
        "mongodb_setup": {"status": "pending", "progress": 0},
        "classements": {"status": "pending", "progress": 0},
        "top5_leagues": {"status": "pending", "progress": 0},
        "elasticsearch_indexing": {"status": "pending", "progress": 0},
        "other_leagues_upcoming": {"status": "pending", "progress": 0},
        "finished_matches": {"status": "pending", "progress": 0},
        "season_history": {"status": "pending", "progress": 0},
        "smart_catalog": {"status": "pending", "progress": 0}
    }
    
    # If no status, create default display
    if not status:
        status = {
            "status": "initializing",
            "overall_progress": 0,
            "current_step": "Démarrage du scraping...",
            "steps": default_steps
        }
    
    # Check if Top 5 step is complete (access allowed)
    steps = status.get("steps", default_steps)
    top5_step = steps.get("top5_leagues", {})
    
    if top5_step.get("status") == "completed":
        return html.Div(
            className="loading-complete",
            children=[
                html.Div("✅", className="success-icon"),
                html.H2("Top 5 Championnats chargés !", className="success-title"),
                html.P("Accès au dashboard...", className="success-message"),
                dcc.Location(id="redirect", href="/", refresh=True)
            ]
        ), True
    
    steps = status.get("steps", default_steps)
    overall_progress = status.get("overall_progress", 0)
    current_step = status.get("current_step", "Initialisation en cours...")
    
    step_displays = {
        "mongodb_setup": "📦 Configuration MongoDB",
        "classements": "🏆 Classements des ligues",
        "top5_leagues": "⭐ Top 5 Championnats (saison complète)",
        "elasticsearch_indexing": "🔍 Indexation Elasticsearch (1000+ clubs)",
        "other_leagues_upcoming": "📅 Autres ligues (matchs à venir)",
        "finished_matches": "✅ Matchs terminés",
        "season_history": "📊 Historique de la saison",
        "smart_catalog": "📚 Catalogue élargi"
    }
    
    step_elements = []
    for step_key, step_label in step_displays.items():
        step_data = steps.get(step_key, {"status": "pending", "progress": 0})
        step_status = step_data.get("status", "pending")
        step_progress = step_data.get("progress", 0)
        
        if step_status == "completed":
            icon = "✅"
            status_class = "step-completed"
            step_progress = 100  # Force 100% for completed steps
        elif step_status == "in_progress":
            icon = "⏳"
            status_class = "step-in-progress"
        else:
            icon = "⏸️"
            status_class = "step-pending"
        
        step_elements.append(
            html.Div(
                className=f"loading-step {status_class}",
                children=[
                    html.Div(
                        className="step-header",
                        children=[
                            html.Span(icon, className="step-icon"),
                            html.Span(step_label, className="step-label"),
                            html.Span(f"{step_progress}%", className="step-percentage")
                        ]
                    ),
                    html.Div(
                        className="step-progress-bar",
                        children=[
                            html.Div(
                                className="step-progress-fill",
                                style={"width": f"{step_progress}%"}
                            )
                        ]
                    )
                ]
            )
        )
    
    return html.Div([
        html.Div(
            className="overall-progress-section",
            children=[
                html.Div(
                    className="overall-progress-header",
                    children=[
                        html.H3("Progression globale", className="progress-title"),
                        html.Span(f"{overall_progress}%", className="progress-percentage")
                    ]
                ),
                html.Div(
                    className="overall-progress-bar",
                    children=[
                        html.Div(
                            className="overall-progress-fill",
                            style={"width": f"{overall_progress}%"}
                        )
                    ]
                ),
                html.P(current_step, className="current-step-message")
            ]
        ),
        html.Div(
            className="steps-container",
            children=[
                html.H4("Étapes d'initialisation", className="steps-title"),
                html.Div(className="steps-list", children=step_elements)
            ]
        )
    ]), False
