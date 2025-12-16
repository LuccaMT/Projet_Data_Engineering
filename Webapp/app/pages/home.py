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
from dash.exceptions import PreventUpdate


UPCOMING_OUTPUT = "../../data/dash_upcoming.json"
FINISHED_OUTPUT = "../../data/dash_finished.json"

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


def prepare_table(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """
    Sélectionne les colonnes utiles et formate le score, l'heure (locale) et les logos.
    """
    if df.empty:
        return [], []

    def logo_md(name: str, url: str) -> str:
        if url:
            return f"<img src='{url}' alt='{name}' style='height:28px;width:28px;border-radius:50%;object-fit:contain;'/>"
        return ""

    def fmt_kickoff(ts: str) -> str:
        if not ts:
            return ""
        try:
            dt_utc = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            dt_local = dt_utc.astimezone()
            return dt_local.strftime("%d %b %Y %H:%M (local)")
        except Exception:
            return ts

    def fmt_score(row) -> str:
        hs = row.get("home_score")
        as_ = row.get("away_score")
        if hs is None or as_ is None or pd.isna(hs) or pd.isna(as_):
            return "N/A"
        return f"{int(hs)} - {int(as_)}"

    df = df.copy()
    df["home_logo_md"] = df.apply(lambda r: logo_md(r.get("home", ""), r.get("home_logo", "")), axis=1)
    df["away_logo_md"] = df.apply(lambda r: logo_md(r.get("away", ""), r.get("away_logo", "")), axis=1)
    df["kickoff"] = df.get("start_time_utc").apply(fmt_kickoff)
    df["score"] = df.apply(fmt_score, axis=1)

    display_cols = [
        ("home_logo_md", ""),
        ("home", "Home"),
        ("score", "Score"),
        ("away", "Away"),
        ("away_logo_md", ""),
        ("status", "Status"),
        ("kickoff", "Horaire"),
        ("league", "Compétition"),
    ]

    df_display = df[[c for c, _ in display_cols]]
    columns = []
    for col_id, col_name in display_cols:
        col_def = {"id": col_id, "name": col_name}
        if "logo_md" in col_id:
            col_def["presentation"] = "markdown"
        columns.append(col_def)

    return columns, df_display.to_dict("records")


def initialize_data():
    """
    Initialise les données au démarrage si elles n'existent pas.
    Charge les matchs à venir et terminés.
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    upcoming_path = Path(UPCOMING_OUTPUT)
    finished_path = Path(FINISHED_OUTPUT)
    
    messages = []
    
    # Charger les matchs à venir si pas de données
    if not upcoming_path.exists():
        messages.append("📥 Chargement initial des matchs à venir...")
        cmd = ["python", "src/scrapy/fetch_upcoming.py", "--date", today_str, "--output", str(upcoming_path)]
        success, msg = run_cmd(cmd)
        if success:
            messages.append("✅ Matchs à venir chargés")
        else:
            messages.append("❌ Erreur lors du chargement des matchs à venir")
    
    # Charger les matchs terminés si pas de données
    if not finished_path.exists():
        messages.append("📥 Chargement initial des matchs terminés...")
        cmd = ["python", "src/scrapy/fetch_finished.py", "--month", current_month, "--output", str(finished_path)]
        success, msg = run_cmd(cmd)
        if success:
            messages.append("✅ Matchs terminés chargés")
        else:
            messages.append("❌ Erreur lors du chargement des matchs terminés")
    
    if not messages:
        messages.append("✅ Données déjà présentes")
    
    return "\n".join(messages)


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
                                    className="control-item date-picker-container",
                                    children=[
                                        html.Label("Sélectionner une date ou un mois"),
                                        html.Div(
                                            style={"display": "flex", "gap": "12px", "alignItems": "center", "flexWrap": "wrap"},
                                            children=[
                                                html.Div(
                                                    style={"flex": "1", "minWidth": "200px"},
                                                    children=[
                                                        dcc.DatePickerSingle(
                                                            id="date-input",
                                                            date=today_str,
                                                            display_format="DD/MM/YYYY",
                                                            placeholder="Choisir une date",
                                                            first_day_of_week=1,
                                                            month_format="MMMM YYYY",
                                                            style={"width": "100%"},
                                                        ),
                                                    ],
                                                ),
                                                html.Div(
                                                    style={"display": "flex", "alignItems": "center"},
                                                    children=[
                                                        dcc.Checklist(
                                                            id="month-mode",
                                                            options=[{"label": " Tout le mois", "value": "month"}],
                                                            value=[],
                                                            className="month-checkbox",
                                                        ),
                                                    ],
                                                ),
                                            ],
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
                        html.Pre(id="status-text", className="status-text", children="Chargement..."),
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
                            style_table={
                                "width": "100%",
                                "maxWidth": "100%",
                            },
                            style_cell={
                                "textAlign": "left",
                                "padding": "12px",
                                "fontSize": "14px",
                                "whiteSpace": "normal",
                                "height": "auto",
                                "minWidth": "80px",
                                "maxWidth": "300px",
                                "overflow": "hidden",
                                "textOverflow": "ellipsis",
                            },
                            style_header={
                                "whiteSpace": "normal",
                                "height": "auto",
                            },
                            style_data={
                                "whiteSpace": "normal",
                                "height": "auto",
                            },
                            tooltip_data=[],
                            tooltip_duration=None,
                            markdown_options={"html": True},
                        ),
                    ],
                ),
            ],
        ),
        
        dcc.Store(id="init-trigger", data={"initialized": False}),
    ])


@callback(
    Output("status-text", "children"),
    Output("data-table", "columns"),
    Output("data-table", "data"),
    Output("init-trigger", "data"),
    Input("init-trigger", "data"),
    State("dataset-type", "value"),
    prevent_initial_call=False,
)
def load_initial_data(init_data, dataset_type):
    """
    Charge les données initiales au démarrage de l'application.
    """
    if init_data and init_data.get("initialized"):
        raise PreventUpdate
    
    # Initialiser les données si nécessaire
    init_msg = initialize_data()
    
    # Charger les données par défaut (upcoming)
    output_path = Path(UPCOMING_OUTPUT)
    df = load_df(output_path)
    
    status_lines = [
        "🚀 Initialisation du dashboard",
        init_msg,
        "",
        f"📊 Affichage: Matchs à venir",
        f"📅 Date: {today_str}",
        f"📈 Lignes chargées: {len(df)}",
    ]
    
    columns, data = prepare_table(df)
    
    return "\n".join(status_lines), columns, data, {"initialized": True}


@callback(
    Output("status-text", "children", allow_duplicate=True),
    Output("data-table", "columns", allow_duplicate=True),
    Output("data-table", "data", allow_duplicate=True),
    Input("fetch-btn", "n_clicks"),
    Input("dataset-type", "value"),
    Input("date-input", "date"),
    Input("month-mode", "value"),
    State("init-trigger", "data"),
    prevent_initial_call=True,
)
def fetch_and_display(n_clicks, dataset_type: str, date_val: str, month_mode: list, init_data):
    """
    Rafraîchit les données quand l'utilisateur change les filtres ou clique sur le bouton.
    Supporte un jour précis ou tout un mois selon le mode sélectionné.
    """
    if not init_data or not init_data.get("initialized"):
        raise PreventUpdate
    
    date_val = date_val or today_str
    use_month_mode = "month" in (month_mode or [])
    
    if dataset_type == "upcoming":
        output_path = Path(UPCOMING_OUTPUT)
        cmd = ["python", "src/scrapy/fetch_upcoming.py", "--date", date_val, "--output", str(output_path)]
        date_display = f"📅 Date: {date_val}"
    else:
        output_path = Path(FINISHED_OUTPUT)
        if use_month_mode:
            # Mode mois : extraire YYYY-MM de la date
            month_val = date_val[:7]  # YYYY-MM-DD -> YYYY-MM
            cmd = ["python", "src/scrapy/fetch_finished.py", "--month", month_val, "--output", str(output_path)]
            date_display = f"📅 Mois: {month_val}"
        else:
            # Mode jour
            cmd = ["python", "src/scrapy/fetch_finished.py", "--date", date_val, "--output", str(output_path)]
            date_display = f"📅 Date: {date_val}"

    success, log_msg = run_cmd(cmd)
    df = load_df(output_path)

    # Déterminer le type d'affichage
    mode_label = "Matchs à venir" if dataset_type == "upcoming" else "Matchs terminés"
    
    # Message selon le succès
    if success:
        data_status = "✅ Nouvelles données enregistrées" if n_clicks > 0 else "✅ Données déjà présentes"
    else:
        data_status = "❌ Erreur lors du chargement"
    
    status_lines = [
        f"📊 Affichage: {mode_label}",
        data_status,
        date_display,
        f"📈 Lignes chargées: {len(df)}",
    ]
    
    columns, data = prepare_table(df)

    return "\n".join(status_lines), columns, data


# Layout pour être importé par main.py
layout = create_layout()
