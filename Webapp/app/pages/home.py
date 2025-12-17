"""
Page d'accueil du dashboard Flashscore
"""
import datetime

import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State, callback
from dash.exceptions import PreventUpdate

from database import get_db_connection
from scraper import scrape_upcoming_matches, scrape_finished_matches
from components.navbar import create_navbar


today = datetime.date.today()
today_str = today.isoformat()
current_month = f"{today:%Y-%m}"

# Limites de dates basées sur les contraintes de l'API Flashscore
# L'API ne fournit des données que pour ±7 jours autour de la date actuelle
MIN_DATE = today - datetime.timedelta(days=7)
MAX_DATE = today + datetime.timedelta(days=7)


def load_matches_from_db(dataset_type: str, **kwargs) -> pd.DataFrame:
    """
    Charge les matchs depuis MongoDB.
    
    Args:
        dataset_type: 'upcoming' ou 'finished'
        **kwargs: Arguments pour filtrer (target_date, month, start_date, end_date)
    
    Returns:
        DataFrame avec les matchs
    """
    db = get_db_connection()
    
    try:
        if dataset_type == "upcoming":
            matches = db.get_upcoming_matches(target_date=kwargs.get('target_date'))
        else:  # finished
            matches = db.get_finished_matches(
                target_date=kwargs.get('target_date'),
                month=kwargs.get('month'),
                start_date=kwargs.get('start_date'),
                end_date=kwargs.get('end_date')
            )
        
        if not matches:
            return pd.DataFrame()
        
        return pd.DataFrame(matches)
    except Exception as e:
        print(f"Erreur lors du chargement des données: {e}")
        return pd.DataFrame()


def get_db_stats() -> str:
    """Retourne des statistiques sur la base de données"""
    db = get_db_connection()
    
    try:
        upcoming_count = db.get_matches_count('matches_upcoming')
        finished_count = db.get_matches_count('matches_finished')
        latest_upcoming = db.get_latest_scrape_time('matches_upcoming')
        latest_finished = db.get_latest_scrape_time('matches_finished')
        
        stats = [
            f"📊 Statistiques MongoDB:",
            f"  - Matchs à venir: {upcoming_count}",
            f"  - Matchs terminés: {finished_count}",
        ]
        
        if latest_upcoming:
            stats.append(f"  - Dernier scrape (upcoming): {latest_upcoming}")
        if latest_finished:
            stats.append(f"  - Dernier scrape (finished): {latest_finished}")
        
        return "\n".join(stats)
    except Exception as e:
        return f"Erreur lors de la récupération des stats: {e}"


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
    
    def normalize_status(row) -> str:
        """Détecter les matches annulés (scores manquants) même si status_code=3."""
        status = row.get("status", "")
        status_code = str(row.get("status_code") or "")
        hs = row.get("home_score")
        as_ = row.get("away_score")
        # Si le flux indique 'terminé' mais sans score, on considère comme annulé/reporté
        if status_code == "3" and (hs is None or pd.isna(hs)) and (as_ is None or pd.isna(as_)):
            return "cancelled"
        return status or "unknown"
    
    def fmt_status(status: str, status_code: str) -> str:
        """Formater le status en français"""
        status_map = {
            'not_started': '⏳ Programmé',
            'in_progress': '🔴 En cours',
            'finished': '✅ Terminé',
            'postponed': '⏸️ Reporté',
            'cancelled': '❌ Annulé',
            'abandoned': '🚫 Abandonné',
            'delayed': '⏱️ Retardé'
        }
        return status_map.get(status, status)

    df = df.copy()
    df["home_logo_md"] = df.apply(lambda r: logo_md(r.get("home", ""), r.get("home_logo", "")), axis=1)
    df["away_logo_md"] = df.apply(lambda r: logo_md(r.get("away", ""), r.get("away_logo", "")), axis=1)
    df["kickoff"] = df.get("start_time_utc").apply(fmt_kickoff)
    df["score"] = df.apply(fmt_score, axis=1)
    df["status_norm"] = df.apply(normalize_status, axis=1)
    df["status_fr"] = df.apply(lambda r: fmt_status(r.get("status_norm", ""), str(r.get("status_code", ""))), axis=1)

    display_cols = [
        ("home_logo_md", ""),
        ("home", "Home"),
        ("score", "Score"),
        ("away", "Away"),
        ("away_logo_md", ""),
        ("status_fr", "Statut"),
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
    Vérifie si des données existent dans MongoDB au démarrage.
    Le scraping initial est fait automatiquement par le conteneur Scrapy.
    """
    db = get_db_connection()
    
    messages = []
    
    # Vérifier la connexion
    if not db.connect():
        messages.append("❌ Impossible de se connecter à MongoDB")
        messages.append("⚠️  Vérifiez que le service MongoDB est démarré")
        return "\n".join(messages)
    
    messages.append("✅ Connexion MongoDB établie")
    
    # Vérifier les données existantes
    upcoming_count = db.get_matches_count('matches_upcoming')
    finished_count = db.get_matches_count('matches_finished')
    
    messages.append(f"📊 Matchs à venir en base: {upcoming_count}")
    messages.append(f"📊 Matchs terminés en base: {finished_count}")
    
    # Scraping automatique si des dates manquent dans les 7 prochains jours
    auto_scrape_logs: list[str] = []
    window_days = 8  # aujourd'hui + 7 jours
    for offset in range(window_days):
        dt = today + datetime.timedelta(days=offset)
        dt_str = dt.isoformat()
        # Vérifier s'il y a déjà des matchs pour cette date
        existing = db.get_upcoming_matches(target_date=dt_str)
        if existing:
            continue
        success, msg = scrape_upcoming_matches(dt_str)
        prefix = "✅" if success else "⚠️"
        auto_scrape_logs.append(f"{prefix} Scrape auto {dt_str}: {msg}")
    
    if auto_scrape_logs:
        messages.append("")
        messages.append("🔄 Scraping auto des 7 prochains jours (au premier démarrage) :")
        messages.extend(auto_scrape_logs)
    
    # Message informatif si pas de données
    if upcoming_count == 0 and finished_count == 0:
        messages.append("")
        messages.append("ℹ️  Aucune donnée trouvée")
        messages.append("💡 Le scraping automatique s'exécute au démarrage du conteneur Scrapy")
        messages.append("💡 Il est possible qu'il n'y ait pas de matchs pour aujourd'hui")
        messages.append("💡 Utilisez le bouton 'Rafraîchir' ci-dessous pour scraper une date spécifique")
    
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
        
        # Navbar
        create_navbar(current_page="home"),
        
        # Main content
        html.Div(
            className="main-content",
            children=[
                # Control Panel
                html.Div(
                    className="control-panel",
                    children=[
                        html.H3("Paramètres de recherche"),
                        
                        # Section 1: Type de données
                        html.Div(
                            style={"marginBottom": "24px"},
                            children=[
                                html.Div(
                                    className="control-item",
                                    children=[
                                        html.Label("Type de données", style={"marginBottom": "8px", "display": "block"}),
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
                            ],
                        ),
                        
                        # Section 2: Sélection de date
                        html.Div(
                            style={
                                "backgroundColor": "#f0f9ff",
                                "padding": "20px",
                                "borderRadius": "12px",
                                "border": "2px solid #bfdbfe",
                                "marginBottom": "20px"
                            },
                            children=[
                                html.Label("📅 Période de recherche", style={
                                    "fontSize": "16px",
                                    "fontWeight": "700",
                                    "color": "#1e40af",
                                    "marginBottom": "12px",
                                    "display": "block"
                                }),
                                html.P(
                                    f"⚠️ Flashscore limite les données à ±7 jours (du {MIN_DATE:%d/%m/%Y} au {MAX_DATE:%d/%m/%Y})",
                                    style={
                                        "fontSize": "12px",
                                        "color": "#1e40af",
                                        "margin": "0 0 16px 0",
                                        "fontStyle": "italic",
                                        "fontWeight": "500"
                                    }
                                ),
                                
                                # Date picker et checkbox
                                html.Div(
                                    style={"display": "grid", "gridTemplateColumns": "2fr 1fr", "gap": "16px", "alignItems": "start"},
                                    children=[
                                        html.Div(
                                            className="date-picker-container",
                                            children=[
                                                html.Label("Date", style={"marginBottom": "8px", "display": "block", "fontWeight": "600"}),
                                                dcc.DatePickerSingle(
                                                    id="date-input",
                                                    date=today_str,
                                                    min_date_allowed=MIN_DATE,
                                                    max_date_allowed=MAX_DATE,
                                                    initial_visible_month=today,
                                                    display_format="DD/MM/YYYY",
                                                    placeholder="Choisir une date",
                                                    first_day_of_week=1,
                                                    month_format="MMMM YYYY",
                                                    style={"width": "100%"},
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            children=[
                                                html.Label("Options", style={"marginBottom": "8px", "display": "block", "fontWeight": "600"}),
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
                        
                        # Section 3: Action
                        html.Div(
                            style={"display": "flex", "flexDirection": "column", "gap": "12px"},
                            children=[
                                html.Button(
                                    "🔄 Rafraîchir (scraper la date choisie)",
                                    id="refresh-button",
                                    n_clicks=0,
                                    className="refresh-button",
                                ),
                                html.Div(
                                    style={
                                        "backgroundColor": "#eff6ff",
                                        "padding": "12px 16px",
                                        "borderRadius": "8px",
                                        "border": "1px solid #dbeafe",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "8px"
                                    },
                                    children=[
                                        html.Span("💡", style={"fontSize": "18px"}),
                                        html.P(
                                            "Les données sont automatiquement scrapées par le conteneur Scrapy toutes les 1-10 secondes (délai aléatoire)",
                                            style={
                                                "fontSize": "13px",
                                                "color": "#1e40af",
                                                "margin": "0",
                                                "fontWeight": "500"
                                            }
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
    Charge les données initiales au démarrage de l'application depuis MongoDB.
    """
    if init_data and init_data.get("initialized"):
        raise PreventUpdate
    
    # Initialiser les données si nécessaire
    init_msg = initialize_data()
    
    # Charger les données par défaut (upcoming) depuis MongoDB
    df = load_matches_from_db("upcoming", target_date=None)
    
    db_stats = get_db_stats()
    
    status_lines = [
        "🚀 Initialisation du dashboard",
        init_msg,
        "",
        db_stats,
        "",
        f"📊 Affichage: Matchs à venir",
        f"📅 Date: Toutes",
        f"📈 Lignes affichées: {len(df)}",
    ]
    
    columns, data = prepare_table(df)
    
    return "\n".join(status_lines), columns, data, {"initialized": True}


@callback(
    Output("status-text", "children", allow_duplicate=True),
    Output("data-table", "columns", allow_duplicate=True),
    Output("data-table", "data", allow_duplicate=True),
    Input("dataset-type", "value"),
    Input("date-input", "date"),
    Input("month-mode", "value"),
    State("init-trigger", "data"),
    prevent_initial_call=True,
)
def fetch_and_display(dataset_type: str, date_val: str, month_mode: list, init_data):
    """
    Affiche les données depuis MongoDB.
    Le scraping est géré automatiquement par le conteneur Scrapy.
    """
    if not init_data or not init_data.get("initialized"):
        raise PreventUpdate
    
    date_val = date_val or today_str
    use_month_mode = "month" in (month_mode or [])
    
    # Déterminer les paramètres selon le type et le mode
    if dataset_type == "upcoming":
        filter_params = {"target_date": date_val}
        date_display = f"📅 Date: {date_val}"
        mode_label = "Matchs à venir"
        period_label = date_val
    else:
        if use_month_mode:
            month_val = date_val[:7]
            filter_params = {"month": month_val}
            date_display = f"📅 Mois: {month_val}"
            period_label = f"le mois {month_val}"
        else:
            filter_params = {"target_date": date_val}
            date_display = f"📅 Date: {date_val}"
            period_label = date_val
        mode_label = "Matchs terminés"
    
    # 1. Charger les données directement depuis MongoDB (le scraping est géré par le conteneur scrapy)
    df = load_matches_from_db(dataset_type, **filter_params)
    
    scraping_msg = ""
    if df.empty:
        scraping_msg = f"ℹ️ Aucune donnée disponible pour {period_label}. Le scraping automatique s'exécute toutes les heures dans le conteneur Scrapy."
    else:
        scraping_msg = f"✅ {len(df)} match(s) chargé(s) pour {period_label}"
    
    # Statistiques DB
    db_stats = get_db_stats()
    
    # Message si aucun match trouvé
    if df.empty and not scraping_msg:
        scraping_msg = f"ℹ️ Aucun match programmé pour {period_label}"
    
    status_lines = [
        f"📊 Affichage: {mode_label}",
        date_display,
        f"📈 Lignes affichées: {len(df)}",
        "",
        db_stats,
    ]
    
    if scraping_msg:
        status_lines.insert(0, scraping_msg)
        status_lines.insert(1, "")
    
    columns, data = prepare_table(df)

    return "\n".join(status_lines), columns, data


@callback(
    Output("status-text", "children", allow_duplicate=True),
    Output("data-table", "columns", allow_duplicate=True),
    Output("data-table", "data", allow_duplicate=True),
    Input("refresh-button", "n_clicks"),
    State("dataset-type", "value"),
    State("date-input", "date"),
    State("month-mode", "value"),
    prevent_initial_call=True,
)
def manual_scrape_and_display(n_clicks: int, dataset_type: str, date_val: str, month_mode: list):
    """
    Lance un scraping manuel pour la date ou le mois sélectionné, puis recharge les données.
    """
    if not n_clicks:
        raise PreventUpdate
    
    date_val = date_val or today_str
    use_month_mode = "month" in (month_mode or [])
    
    # Déterminer la commande de scraping
    if dataset_type == "upcoming":
        success, msg = scrape_upcoming_matches(date_val)
        filter_params = {"target_date": date_val}
        mode_label = "Matchs à venir"
        period_label = date_val
        date_display = f"📅 Date: {date_val}"
    else:
        if use_month_mode:
            month_val = date_val[:7]
            success, msg = scrape_finished_matches(month=month_val)
            filter_params = {"month": month_val}
            period_label = f"le mois {month_val}"
            date_display = f"📅 Mois: {month_val}"
        else:
            success, msg = scrape_finished_matches(target_date=date_val)
            filter_params = {"target_date": date_val}
            period_label = date_val
            date_display = f"📅 Date: {date_val}"
        mode_label = "Matchs terminés"
    
    # Charger les données mises à jour
    df = load_matches_from_db(dataset_type, **filter_params)
    columns, data = prepare_table(df)
    
    scrape_prefix = "✅ Scraping manuel" if success else "⚠️ Scraping manuel"
    scraping_msg = f"{scrape_prefix}: {msg}"
    data_msg = f"📈 Lignes affichées: {len(df)}"
    
    status_lines = [
        scraping_msg,
        "",
        f"📊 Affichage: {mode_label}",
        date_display,
        data_msg,
    ]
    
    db_stats = get_db_stats()
    if db_stats:
        status_lines.extend(["", db_stats])
    
    if df.empty:
        status_lines.insert(1, f"ℹ️ Aucun match trouvé pour {period_label}")
    
    return "\n".join(status_lines), columns, data


# Layout pour être importé par main.py
layout = create_layout()


@callback(
    Output("dataset-type", "options"),
    Output("dataset-type", "value"),
    Input("date-input", "date"),
    State("dataset-type", "value"),
    prevent_initial_call=False,
)
def enforce_dataset_for_date(date_val: str, current_value: str):
    """
    Empêche la sélection 'Matchs à venir' pour les dates passées (matchs déjà terminés).
    Force le dataset sur 'terminés' si la date est < aujourd'hui.
    """
    date_val = date_val or today_str
    try:
        selected_date = datetime.date.fromisoformat(date_val)
    except ValueError:
        selected_date = today
    
    options_all = [
        {"label": "⏰ Matchs à venir / en cours", "value": "upcoming"},
        {"label": "✅ Matchs terminés", "value": "finished"},
    ]
    options_finished = [
        {"label": "✅ Matchs terminés", "value": "finished"},
    ]
    
    if selected_date < today:
        # Date dans le passé : uniquement les matchs terminés sont pertinents
        return options_finished, "finished"
    
    # Date aujourd'hui ou future : on conserve les deux options, en gardant la valeur si valide
    new_value = current_value if current_value in {"upcoming", "finished"} else "upcoming"
    return options_all, new_value
