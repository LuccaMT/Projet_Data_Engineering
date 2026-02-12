"""Page En Direct : tableau de bord + filtres pour les matchs."""

import datetime
import os
import logging
import re

import pandas as pd
from dash import dcc, html, dash_table, Input, Output, State, callback, callback_context
from dash.exceptions import PreventUpdate

from database import get_db_connection
from components.navbar import create_navbar

# Configuration du logging
logger = logging.getLogger(__name__)


# Vérifier si on est en mode DEV
IS_DEV = os.getenv('DEV', 'False').lower() == 'true'


today = datetime.date.today()
today_str = today.isoformat()

# Déterminer la saison de football (juillet - juin)
if today.month >= 7:
    season_start = datetime.date(today.year, 7, 1)
    season_end = datetime.date(today.year + 1, 6, 30)
else:
    season_start = datetime.date(today.year - 1, 7, 1)
    season_end = datetime.date(today.year, 6, 30)

MIN_DATE = season_start
MAX_DATE = season_end


def apply_league_filter(df: pd.DataFrame, league_filter: str) -> pd.DataFrame:
    """Apply a robust league filter on the DataFrame.

    Uses case-insensitive, non-regex matching to avoid issues with special
    characters and league name variants.
    """
    if df.empty or not league_filter or league_filter == "all":
        return df

    league_series = df.get("league")
    if league_series is None:
        # No league column: return empty result for explicit filter.
        return df.iloc[0:0]

    normalized = league_series.fillna("").astype(str).str.casefold()

    # Canonical leagues linked to the quick buttons.
    canonical_map = {
        "FRANCE: Ligue 1": "france: ligue 1",
        "SPAIN: LaLiga": "spain: laliga",
        "ENGLAND: Premier League": "england: premier league",
        "GERMANY: Bundesliga": "germany: bundesliga",
        "ITALY: Serie A": "italy: serie a",
    }

    target = canonical_map.get(league_filter)
    if target:
        # Strict mode first: only the selected championship.
        exact_mask = normalized == target
        if exact_mask.any():
            return df[exact_mask]

        # Fallback for minor formatting differences in source data.
        tokens = [t for t in re.split(r"[:\s-]+", target) if t]
        mask = pd.Series(True, index=df.index)
        for token in tokens:
            mask &= normalized.str.contains(token, regex=False)
        return df[mask]

    # Generic fallback for unknown custom filters.
    return df[normalized.str.contains(str(league_filter).casefold(), regex=False)]


def load_matches_from_db(dataset_type: str, **kwargs) -> pd.DataFrame:
    """Load matches from MongoDB.

    Args:
        dataset_type: Either "upcoming" or "finished".
        **kwargs: Filter parameters (e.g. target_date, month, start_date, end_date).

    Returns:
        A DataFrame of match documents (empty if none / on error).
    """
    db = get_db_connection()
    
    try:
        if dataset_type == "upcoming":
            matches = db.get_upcoming_matches(target_date=kwargs.get('target_date'))
        else:
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
    """Build a short textual summary of database stats.

    Returns:
        A multi-line string with counts and last scrape timestamps.
    """
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


def get_today_stats(df: pd.DataFrame) -> dict:
    """Compute stats used by the home KPI cards.

    Args:
        df: DataFrame of matches (typically upcoming/live).

    Returns:
        Dict with keys: total, live, upcoming, finished.
    """
    if df.empty:
        return {"total": 0, "live": 0, "upcoming": 0, "finished": 0}
    
    today_df = df[df.get('start_time_utc', pd.Series()).notna()]
    
    total = len(today_df)
    live = len(today_df[today_df.get('status').isin(['in_progress', 'live'])])
    upcoming = len(today_df[today_df.get('status') == 'not_started'])
    finished = len(today_df[today_df.get('status') == 'finished'])
    
    return {"total": total, "live": live, "upcoming": upcoming, "finished": finished}


def prepare_table(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Convert a matches DataFrame into DataTable columns and rows.

    Args:
        df: Matches DataFrame.

    Returns:
        Tuple (columns, records) compatible with Dash DataTable.
    """
    if df.empty:
        return [], []

    def logo_md(name: str, url: str) -> str:
        """Génère une balise HTML <img> pour un logo d'équipe (utilisée dans les cellules markdown)."""
        if url:
            return f"<img src='{url}' alt='{name}' style='height:28px;width:28px;border-radius:50%;object-fit:contain;'/>"
        return ""

    def fmt_kickoff(ts: str) -> str:
        """Formate l'heure de coup d'envoi en fuseau horaire local pour l'affichage."""
        if not ts:
            return ""
        try:
            dt_utc = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            dt_local = dt_utc.astimezone()
            return dt_local.strftime("%d %b %Y %H:%M (local)")
        except Exception:
            return ts

    def fmt_score(row) -> str:
        """Formate le score comme 'X - Y' ou un message approprié si manquant."""
        hs = row.get("home_score")
        as_ = row.get("away_score")
        status = row.get("status", "")
        status_code = row.get("status_code")
        
        # Debug: log pour les premiers matchs
        home = row.get("home", "")
        if home in ["Lyon", "Aston Villa", "Manchester Utd"]:
            logger.info(f"🔍 DEBUG fmt_score: {home} - hs={hs} (type={type(hs)}), as_={as_} (type={type(as_)}), status={status}")
        
        def coerce_score(value):
            """Convertit un score en int (supporte int/float/str)."""
            if value is None or pd.isna(value):
                return None

            # Cas courant Mongo->pandas: 1 devient 1.0 (numpy.float64)
            numeric = pd.to_numeric(value, errors="coerce")
            if not pd.isna(numeric):
                return int(float(numeric))

            # Fallback permissif si la valeur contient des caractères parasites.
            match = re.search(r"-?\d+", str(value))
            if match:
                return int(match.group(0))
            return None

        hs_int = coerce_score(hs)
        as_int = coerce_score(as_)

        # Si les scores sont absents/inexploitables
        if hs_int is None or as_int is None:
            # Match terminé mais sans score = probablement annulé/reporté
            if status == "finished" or status_code in [100, "100", 3, "3"]:
                return "❌ Annulé"
            # Match pas encore commencé
            elif status == "not_started":
                return "⏳ À venir"
            # Autres cas
            else:
                return "-"
        
        return f"{hs_int} - {as_int}"
    
    def normalize_status(row) -> str:
        """Normalise le statut et gère les cas limites 'cancelled'."""
        status = row.get("status", "")
        status_code = row.get("status_code")
        hs = row.get("home_score")
        as_ = row.get("away_score")
        # Match terminé (status_code 100 ou "3") mais sans score = annulé
        if (status_code == 100 or status_code == "3" or status_code == 3) and (hs is None or pd.isna(hs)) and (as_ is None or pd.isna(as_)):
            return "cancelled"
        return status or "unknown"
    
    def fmt_status(status: str) -> str:
        """Mappe les valeurs de statut internes vers des labels français avec icônes."""
        status_map = {
            'not_started': '⏳ Programmé',
            'in_progress': '🔴 En cours',
            'live': 'En cours',
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
    df["status_fr"] = df.apply(lambda r: fmt_status(r.get("status_norm", "")), axis=1)

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

    records = df_display.to_dict("records")
    return columns, records


def initialize_data() -> str:
    """Check database connectivity and basic counts.

    Returns:
        A multi-line string describing the initialization state.
    """
    db = get_db_connection()
    
    messages = []
    
    if not db.connect():
        messages.append("❌ Impossible de se connecter à MongoDB")
        messages.append("⚠️  Vérifiez que le service MongoDB est démarré")
        return "\n".join(messages)
    
    messages.append("✅ Connexion MongoDB établie")
    
    upcoming_count = db.get_matches_count('matches_upcoming')
    finished_count = db.get_matches_count('matches_finished')
    
    messages.append(f"📊 Matchs à venir: {upcoming_count}")
    messages.append(f"📊 Matchs terminés: {finished_count}")
    
    if upcoming_count == 0 and finished_count == 0:
        messages.append("")
        messages.append("ℹ️  Aucune donnée - scraping en cours au démarrage")
    
    return "\n".join(messages)


def create_layout():
    """Crée le layout de la page En Direct."""
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
                                html.H1("Matchs En Direct"),
                                html.P("Suivez les matchs en temps réel"),
                            ],
                        ),
                    ],
                ),
            ],
        ),
        
        # Navbar
        create_navbar(current_page="live"),
        
        # Statistics Cards
        html.Div(
            className="stats-cards-container",
            children=[
                html.Div(
                    className="stat-card",
                    children=[
                        html.Div(className="stat-icon", children="📊"),
                        html.Div(className="stat-content", children=[
                            html.Div(id="stat-total", className="stat-value", children="0"),
                            html.Div(className="stat-label", children="Matchs aujourd'hui")
                        ])
                    ]
                ),
                html.Div(
                    className="stat-card stat-card-live",
                    children=[
                        html.Div(className="stat-icon live-icon", children="🔴"),
                        html.Div(className="stat-content", children=[
                            html.Div(id="stat-live", className="stat-value", children="0"),
                            html.Div(className="stat-label", children="En direct")
                        ])
                    ]
                ),
                html.Div(
                    className="stat-card",
                    children=[
                        html.Div(className="stat-icon", children="⏰"),
                        html.Div(className="stat-content", children=[
                            html.Div(id="stat-upcoming", className="stat-value", children="0"),
                            html.Div(className="stat-label", children="À venir")
                        ])
                    ]
                ),
                html.Div(
                    className="stat-card",
                    children=[
                        html.Div(className="stat-icon", children="✅"),
                        html.Div(className="stat-content", children=[
                            html.Div(id="stat-finished", className="stat-value", children="0"),
                            html.Div(className="stat-label", children="Terminés")
                        ])
                    ]
                ),
            ]
        ),
        
        # Main content
        html.Div(
            className="main-content",
            children=[
                # Control Panel
                html.Div(
                    className="control-panel",
                    children=[
                        html.H3("⚙️ Paramètres de recherche"),
                        
                        # Type de données
                        html.Div(
                            className="control-section",
                            children=[
                                html.Label("Type de données", className="control-label"),
                                dcc.Dropdown(
                                    id="dataset-type",
                                    options=[
                                        {"label": "⏰ Matchs à venir / en cours", "value": "upcoming"},
                                        {"label": "✅ Matchs terminés", "value": "finished"},
                                    ],
                                    value="upcoming",
                                    clearable=False,
                                    className="control-dropdown",
                                ),
                            ],
                        ),
                        
                        # Période de recherche
                        html.Div(
                            className="control-section period-section",
                            children=[
                                html.Div(
                                    className="period-header",
                                    children=[
                                        html.Label("📅 Période de recherche", className="control-label"),
                                        html.Div(
                                            className="info-badge",
                                            children=[
                                                html.Span("ℹ️", style={"marginRight": "6px"}),
                                                f"Saison {season_start.year}/{season_end.year} disponible"
                                            ]
                                        )
                                    ]
                                ),
                                html.Div(
                                    className="date-controls",
                                    children=[
                                        html.Div(
                                            className="date-input-wrapper",
                                            children=[
                                                html.Label("Date", className="sub-label"),
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
                                                    with_portal=True,
                                                    style={"width": "100%"},
                                                ),
                                            ],
                                        ),
                                        html.Div(
                                            id="month-mode-wrapper",
                                            className="checkbox-wrapper",
                                            children=[
                                                html.Label("Options", className="sub-label"),
                                                dcc.Checklist(
                                                    id="month-mode",
                                                    options=[{"label": " Tout le mois", "value": "month"}],
                                                    value=[],
                                                    className="month-checkbox",
                                                ),
                                            ],
                                            style={"display": "none"},  # Hidden by default (upcoming mode)
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        
                        # Info sur le scraping automatique
                        html.Div(
                            className="control-section",
                            children=[
                                html.Div(
                                    className="info-box",
                                    children=[
                                        html.Span("💡", className="info-icon"),
                                        html.Div(
                                            className="info-text",
                                            children="Tous les matchs de la saison sont disponibles. Les données sont automatiquement mises à jour toutes les 1-10 secondes."
                                        )
                                    ],
                                ),
                            ],
                        ),
                    ],
                ),
                
                # Status Panel (uniquement en mode DEV)
                html.Div(
                    className="status-panel",
                    style={"display": "block" if IS_DEV else "none"},
                    children=[
                        html.H3("Statut"),
                        html.Pre(id="status-text", className="status-text", children="Chargement..."),
                    ],
                ) if IS_DEV else html.Div(id="status-text", style={"display": "none"}, children=""),
                
                # Data Table
                html.Div(
                    className="table-container",
                    children=[
                        html.Div(
                            className="table-header-actions",
                            children=[
                                html.H3("Résultats"),
                                html.Div(
                                    className="league-filter",
                                    children=[
                                        html.Span("Filtrer par ligue:", className="filter-label"),
                                        html.Button("Toutes", id="filter-all", className="league-btn active", n_clicks=0),
                                        html.Button("🇫🇷 Ligue 1", id="filter-france", className="league-btn", n_clicks=0),
                                        html.Button("🇪🇸 LaLiga", id="filter-spain", className="league-btn", n_clicks=0),
                                        html.Button("🏴󠁧󠁢󠁥󠁮󠁧󠁿 Premier League", id="filter-england", className="league-btn", n_clicks=0),
                                        html.Button("🇩🇪 Bundesliga", id="filter-germany", className="league-btn", n_clicks=0),
                                        html.Button("🇮🇹 Serie A", id="filter-italy", className="league-btn", n_clicks=0),
                                    ]
                                )
                            ]
                        ),
                        html.Div(
                            id="no-match-message",
                            className="no-match-message",
                            style={"display": "none"},
                            children=[
                                html.Div(
                                    className="no-match-content",
                                    children=[
                                        html.Span("🔍", className="no-match-icon"),
                                        html.H3("Aucun match trouvé", className="no-match-title"),
                                        html.P(id="no-match-details", className="no-match-details", children=""),
                                        html.P(
                                            "💡 Essayez de sélectionner une autre date ou période.",
                                            className="no-match-hint"
                                        )
                                    ]
                                )
                            ]
                        ),
                        dash_table.DataTable(
                            id="data-table",
                            columns=[],
                            data=[],
                            page_size=20,
                            filter_action="native",
                            filter_options={
                                "case": "insensitive",
                                "placeholder_text": "Filtrer...",
                            },
                            sort_action="native",
                            sort_mode="multi",
                            style_table={
                                "width": "100%",
                                "maxWidth": "100%",
                            },
                            style_filter={
                                "backgroundColor": "#f8fafc",
                                "color": "#0f172a",
                                "border": "1px solid #cbd5e1",
                            },
                            style_cell={
                                "textAlign": "left",
                                "padding": "8px",
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
        dcc.Store(id="league-filter", data="all"),
        dcc.Interval(
            id="auto-refresh-interval",
            interval=30*1000,  # 30 secondes
            n_intervals=0
        ),
    ])


@callback(
    Output("status-text", "children"),
    Output("data-table", "columns"),
    Output("data-table", "data"),
    Output("init-trigger", "data"),
    Output("stat-total", "children"),
    Output("stat-live", "children"),
    Output("stat-upcoming", "children"),
    Output("stat-finished", "children"),
    Output("no-match-message", "style"),
    Output("no-match-details", "children"),
    Input("init-trigger", "data"),
        prevent_initial_call=False,
)
def load_initial_data(init_data):
    """Callback initial pour remplir le tableau et le panneau de statut."""
    if init_data and init_data.get("initialized"):
        raise PreventUpdate
    
    init_msg = initialize_data()
    
    # Charger TOUS les matchs d'aujourd'hui (upcoming) pour avoir les matchs live
    df = load_matches_from_db("upcoming", target_date=today_str)
    
    # Filtrer pour ne garder que les matchs live et à venir d'aujourd'hui
    if not df.empty:
        # Garder les matchs live (in_progress) ou à venir (not_started) uniquement
        df = df[df.get('status', pd.Series()).isin(['in_progress', 'not_started', 'live'])]
    
    stats = get_today_stats(df)
    
    db_stats = get_db_stats()
    
    status_lines = [
        "🚀 Initialisation du dashboard",
        init_msg,
        "",
        db_stats,
        "",
        f"🔴 Affichage: Matchs en direct & à venir",
        f"📅 Date: Aujourd'hui ({today_str})",
        f"📈 Lignes affichées: {len(df)}",
        f"⚡ Rafraîchissement automatique: toutes les 30s",
    ]
    
    columns, data = prepare_table(df)
    
    # Message pour pas de matches
    no_match_style = {"display": "none"}
    no_match_details = ""
    
    return ("\n".join(status_lines), columns, data, {"initialized": True},
            stats["total"], stats["live"], stats["upcoming"], stats["finished"],
            no_match_style, no_match_details)


@callback(
    Output("status-text", "children", allow_duplicate=True),
    Output("data-table", "columns", allow_duplicate=True),
    Output("data-table", "data", allow_duplicate=True),
    Output("stat-total", "children", allow_duplicate=True),
    Output("stat-live", "children", allow_duplicate=True),
    Output("stat-upcoming", "children", allow_duplicate=True),
    Output("stat-finished", "children", allow_duplicate=True),
    Output("no-match-message", "style", allow_duplicate=True),
    Output("no-match-details", "children", allow_duplicate=True),
    Input("dataset-type", "value"),
    Input("date-input", "date"),
    Input("month-mode", "value"),
    Input("league-filter", "data"),
    Input("auto-refresh-interval", "n_intervals"),
    State("init-trigger", "data"),
    prevent_initial_call=True,
)
def fetch_and_display(dataset_type: str, date_val: str, month_mode: list, league_filter: str, _n_intervals: int, init_data):
    """Rafraîchit le tableau et les cartes quand les filtres changent ou l'intervalle tick."""
    if not init_data or not init_data.get("initialized"):
        raise PreventUpdate
    
    date_val = date_val or today_str
    use_month_mode = "month" in (month_mode or [])
    
    if dataset_type == "upcoming":
        filter_params = {"target_date": date_val}
        # Si c'est aujourd'hui, afficher "En direct & Ã€ venir", sinon juste "Ã€ venir"
        if date_val == today_str:
            mode_label = "🔴 Matchs en direct & à venir"
            date_display = f"📅 Aujourd'hui ({date_val})"
        else:
            mode_label = "Matchs à venir"
            date_display = f"📅 Date: {date_val}"
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
    
    df = load_matches_from_db(dataset_type, **filter_params)
    
    # Pour les matchs d'aujourd'hui (upcoming), filtrer pour ne garder que live + Ã  venir
    if dataset_type == "upcoming" and date_val == today_str and not df.empty:
        df = df[df.get('status', pd.Series()).isin(['in_progress', 'not_started', 'live'])]
    
    # Filtrer par ligue si nécessaire
    df = apply_league_filter(df, league_filter)
    
    # Calculer les stats pour les cards (toujours pour aujourd'hui)
    today_df = load_matches_from_db("upcoming", target_date=today_str)
    stats = get_today_stats(today_df)
    
    scraping_msg = ""
    if df.empty:
        scraping_msg = f"ℹ️ Aucune donnée disponible pour {period_label}. Le scraping automatique s'exécute toutes les heures dans le conteneur Scrapy."
    else:
        scraping_msg = f"✅ {len(df)} match(s) chargé(s) pour {period_label}"
    
    db_stats = get_db_stats()
    
    if df.empty and not scraping_msg:
        scraping_msg = f"ℹ️ Aucun match programmé pour {period_label}"
    
    filter_msg = f" (Filtre: {league_filter})" if league_filter != "all" else ""
    
    status_lines = [
        f"📊 Affichage: {mode_label}{filter_msg}",
        date_display,
        f"📈 Lignes affichées: {len(df)}",
        "",
        db_stats,
    ]
    
    if scraping_msg:
        status_lines.insert(0, scraping_msg)
        status_lines.insert(1, "")
    
    columns, data = prepare_table(df)
    
    # Gérer l'affichage du message "pas de matches"
    if df.empty:
        no_match_style = {"display": "flex"}
        if league_filter and league_filter != "all":
            no_match_details = f"Aucun match {mode_label.lower()} pour {period_label} avec le filtre '{league_filter}'."
        else:
            no_match_details = f"Aucun match {mode_label.lower()} pour {period_label}."
    else:
        no_match_style = {"display": "none"}
        no_match_details = ""

    return ("\n".join(status_lines), columns, data, 
            stats["total"], stats["live"], stats["upcoming"], stats["finished"],
            no_match_style, no_match_details)


@callback(
    Output("league-filter", "data"),
    Output("filter-all", "className"),
    Output("filter-france", "className"),
    Output("filter-spain", "className"),
    Output("filter-england", "className"),
    Output("filter-germany", "className"),
    Output("filter-italy", "className"),
    Input("filter-all", "n_clicks"),
    Input("filter-france", "n_clicks"),
    Input("filter-spain", "n_clicks"),
    Input("filter-england", "n_clicks"),
    Input("filter-germany", "n_clicks"),
    Input("filter-italy", "n_clicks"),
    prevent_initial_call=True,
)
def update_league_filter(_n_all, _n_fr, _n_es, _n_en, _n_de, _n_it):
    """Met à jour l'état du filtre de ligue quand un bouton de ligue est cliqué."""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    league_map = {
        "filter-all": "all",
        "filter-france": "FRANCE: Ligue 1",
        "filter-spain": "SPAIN: LaLiga",
        "filter-england": "ENGLAND: Premier League",
        "filter-germany": "GERMANY: Bundesliga",
        "filter-italy": "ITALY: Serie A",
    }
    
    selected = league_map.get(button_id, "all")
    
    classes = [
        "league-btn active" if selected == "all" else "league-btn",
        "league-btn active" if selected == "FRANCE: Ligue 1" else "league-btn",
        "league-btn active" if selected == "SPAIN: LaLiga" else "league-btn",
        "league-btn active" if selected == "ENGLAND: Premier League" else "league-btn",
        "league-btn active" if selected == "GERMANY: Bundesliga" else "league-btn",
        "league-btn active" if selected == "ITALY: Serie A" else "league-btn",
    ]
    
    return selected, *classes


layout = create_layout()


@callback(
    Output("dataset-type", "options"),
    Output("dataset-type", "value"),
    Input("date-input", "date"),
    State("dataset-type", "value"),
    prevent_initial_call=False,
)
def enforce_dataset_for_date(date_val: str, current_value: str):
    """Restrict dataset type when browsing past dates.

    Past dates can't have upcoming matches, so the dropdown is limited to
    "finished".
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
        return options_finished, "finished"
    
    new_value = current_value if current_value in {"upcoming", "finished"} else "upcoming"
    return options_all, new_value


@callback(
    Output("month-mode-wrapper", "style"),
    Output("month-mode", "value"),
    Input("dataset-type", "value"),
    State("month-mode", "value"),
    prevent_initial_call=False,
)
def toggle_month_mode_visibility(dataset_type: str, current_value: list):
    """Show/hide the month mode checkbox based on dataset type.
    
    The "Tout le mois" checkbox only makes sense for finished matches.
    """
    if dataset_type == "finished":
        # Show checkbox and keep current value
        return {"display": "block"}, current_value or []
    else:
        # Hide checkbox and clear value
        return {"display": "none"}, []
