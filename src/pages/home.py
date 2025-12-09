"""
Page d'accueil du dashboard Flashscore
"""
import datetime
from pathlib import Path
from typing import Tuple
import subprocess
import json

import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State, callback


UPCOMING_OUTPUT = "data/dash_upcoming.json"
FINISHED_OUTPUT = "data/dash_finished.json"

today_str = datetime.date.today().isoformat()
current_month = f"{datetime.date.today():%Y-%m}"


def run_cmd(cmd: list[str]) -> Tuple[bool, str]:
    """Execute a subprocess command and return success flag and message."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        success = proc.returncode == 0
        stdout = proc.stdout.strip()
        stderr = proc.stderr.strip()
        msg = f"Command: {' '.join(cmd)}\nExit: {proc.returncode}\nStdout:\n{stdout}"
        if stderr:
            msg += f"\nStderr:\n{stderr}"
        return success, msg
    except Exception as exc:
        return False, f"Execution failed: {exc}"


def load_df(path: Path) -> pd.DataFrame:
    """Load dataframe from JSON file."""
    if not path.exists():
        return pd.DataFrame()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


def create_layout():
    """Create the home page layout."""
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
                        html.Div("⚽", className="header-icon"),
                        html.Div(
                            className="header-text",
                            children=[
                                html.H1("Flashscore Football Dashboard"),
                                html.P("Données en temps réel via Scrapy"),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        
        # Main content
        html.Div(
            className="main-content",
            children=[
                # Control Panel
                html.Div(
                    className="control-panel",
                    children=[
                        html.H3("Paramètres de recherche"),
                        html.Div(
                            className="controls-grid",
                            children=[
                                html.Div(
                                    className="control-item",
                                    children=[
                                        html.Label("Type de données"),
                                        dcc.Dropdown(
                                            id="dataset-type",
                                            options=[
                                                {"label": "⏰ Matchs à venir / en cours", "value": "upcoming"},
                                                {"label": "✅ Matchs terminés", "value": "finished"},
                                            ],
                                            value="upcoming",
                                            clearable=False,
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="control-item",
                                    children=[
                                        html.Label("Date (YYYY-MM-DD)"),
                                        dcc.Input(
                                            id="date-input",
                                            type="text",
                                            value=today_str,
                                            placeholder="2025-12-09",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="control-item",
                                    children=[
                                        html.Label("Mois (YYYY-MM) pour terminés"),
                                        dcc.Input(
                                            id="month-input",
                                            type="text",
                                            value=current_month,
                                            placeholder="2025-12",
                                        ),
                                    ],
                                ),
                                html.Div(
                                    className="control-item",
                                    children=[
                                        html.Button(
                                            "🔄 Rafraîchir les données",
                                            id="fetch-btn",
                                            n_clicks=0,
                                            className="refresh-button",
                                        ),
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                
                # Status Panel
                html.Div(
                    className="status-panel",
                    children=[
                        html.H3("Statut"),
                        html.Pre(id="status-text", className="status-text"),
                    ],
                ),
                
                # Data Table
                html.Div(
                    className="table-container",
                    children=[
                        html.H3("Résultats"),
                        dash_table.DataTable(
                            id="data-table",
                            columns=[],
                            data=[],
                            page_size=20,
                            style_table={"overflowX": "auto"},
                        ),
                    ],
                ),
            ],
        ),
        
        dcc.Store(id="data-store"),
    ])


@callback(
    Output("status-text", "children"),
    Output("data-table", "columns"),
    Output("data-table", "data"),
    Input("fetch-btn", "n_clicks"),
    State("dataset-type", "value"),
    State("date-input", "value"),
    State("month-input", "value"),
    prevent_initial_call=False,
)
def fetch_and_display(_clicks, dataset_type: str, date_val: str, month_val: str):
    """
    Run the appropriate Scrapy script and display the resulting JSON.
    """
    date_val = date_val or today_str
    month_val = month_val or current_month

    if dataset_type == "upcoming":
        output_path = Path(UPCOMING_OUTPUT)
        cmd = ["python", "src/scrapy/fetch_upcoming.py", "--date", date_val, "--output", str(output_path)]
    else:
        output_path = Path(FINISHED_OUTPUT)
        cmd = ["python", "src/scrapy/fetch_finished.py", "--month", month_val, "--output", str(output_path)]

    success, log_msg = run_cmd(cmd)
    df = load_df(output_path)

    status_lines = [
        f"Mode: {dataset_type}",
        f"Date: {date_val}",
        f"Mois: {month_val}",
        f"Output: {output_path}",
        f"Rows loaded: {len(df)}",
        log_msg,
    ]
    columns = [{"name": c, "id": c} for c in df.columns]
    data = df.to_dict("records")

    if not success:
        status_lines.insert(0, "ERREUR lors de l'execution du script.")

    return "\n".join(status_lines), columns, data


# Layout pour être importé par main.py
layout = create_layout()
