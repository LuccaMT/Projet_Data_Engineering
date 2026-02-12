"""Page détail de ligue : liste des matchs + classement pour une ligue donnée."""

import datetime
import urllib.parse
from typing import Dict, List, Optional
from collections import defaultdict

from dash import Input, Output, State, callback, dcc, html

from components.navbar import create_navbar
from database import get_db_connection
from pages.cups import is_cup

RECENT_FINISHED_WINDOW_DAYS = 9999


def _parse_league_name(search: Optional[str]) -> Optional[str]:
    """Extract the league name from the URL query string.

    Args:
        search: Dash `Location.search` value (e.g. "?name=FRANCE%3A+Ligue+1").

    Returns:
        Decoded league name, or None when missing.
    """
    if not search:
        return None
    query = urllib.parse.parse_qs(search.lstrip("?"))
    raw = query.get("name", [None])[0]
    if not raw:
        return None
    return urllib.parse.unquote_plus(raw)


def _create_back_button(league_name: Optional[str], css_class: str = "link-button") -> dcc.Link:
    """Create a back button that adapts based on whether it's a cup or league.
    
    Args:
        league_name: Name of the league/cup.
        css_class: CSS class for the button.
    
    Returns:
        A Dash Link component.
    """
    if league_name and is_cup(league_name):
        return dcc.Link("Retour aux coupes", href="/cups", className=css_class)
    return dcc.Link("Retour aux ligues", href="/leagues", className=css_class)


def _format_kickoff(match: Dict) -> tuple[str, str]:
    """Format kickoff display text and a YYYY-MM-DD key.

    Args:
        match: Match document (expects `start_time_utc` or `target_date`).

    Returns:
        Tuple (display_label, date_key). The date_key can be empty if unknown.
    """
    ts_str = match.get("start_time_utc")
    target_date = match.get("target_date")
    try:
        if ts_str:
            dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
            local_dt = dt.astimezone()
            day_hint = "Aujourd'hui" if local_dt.date() == datetime.date.today() else (
                "Demain" if local_dt.date() == datetime.date.today() + datetime.timedelta(days=1) else local_dt.strftime("%Y-%m-%d")
            )
            return f"{day_hint} · {local_dt.strftime('%H:%M')}", local_dt.strftime("%Y-%m-%d")
        if target_date:
            dt = datetime.date.fromisoformat(target_date)
            return dt.strftime("%Y-%m-%d"), dt.strftime("%Y-%m-%d")
    except Exception:
        pass
    return "Horaire a confirmer", ""


def _match_status(match: Dict) -> tuple[str, str]:
    """Compute a human label and CSS class for match status.

    Args:
        match: Match document.

    Returns:
        Tuple (status_label, css_class).
    """
    status_code = match.get("status_code")
    status = (match.get("status") or "").lower()
    now_ts = datetime.datetime.utcnow().timestamp()
    start_ts = match.get("start_timestamp") or 0

    # Vérifier d'abord le statut textuel (plus fiable)
    if status == "finished":
        return "Terminé", "status-finished"
    if status in ("live", "in_progress"):
        return "En cours", "status-live"
    
    # Fallback sur status_code (100 = finished, 0 = not_started)
    if status_code == 100:
        return "Terminé", "status-finished"
    if status_code == 0 or status == "not_started":
        if start_ts and start_ts <= now_ts:
            return "Démarre", "status-upcoming"
        return "À venir", "status-upcoming"
    
    return "À confirmer", "status-upcoming"


def _score_text(match: Dict) -> str:
    """Render the score text shown between the teams.

    Args:
        match: Match document.

    Returns:
        A string like "2 - 1" or "vs" when not available.
    """
    hs = match.get("home_score")
    as_ = match.get("away_score")
    
    if hs is None or as_ is None or hs == "" or as_ == "":
        return "vs"
    
    try:
        home_score = int(hs) if isinstance(hs, (int, float, str)) else None
        away_score = int(as_) if isinstance(as_, (int, float, str)) else None
        
        if home_score is not None and away_score is not None:
            return f"{home_score} - {away_score}"
        return "vs"
    except (ValueError, TypeError):
        return "vs"


def _team_chip(name: str, logo: Optional[str]) -> html.Div:
    """Build a small team badge with avatar + name.

    Args:
        name: Team name.
        logo: Optional logo URL.

    Returns:
        Dash HTML container for the team chip.
    """
    avatar_style = {
        "width": "32px",
        "height": "32px",
        "borderRadius": "50%",
        "backgroundColor": "#e5edff",
        "display": "inline-flex",
        "alignItems": "center",
        "justifyContent": "center",
        "color": "#1d4ed8",
        "fontWeight": "700",
        "flexShrink": "0",
        "backgroundSize": "cover",
        "backgroundPosition": "center",
    }
    if logo:
        avatar_style["backgroundImage"] = f"url('{logo}')"
        avatar_style["backgroundColor"] = "#eef2ff"
        avatar_style["color"] = "transparent"

    initials = (name or "?")[:2].upper()
    return html.Div(
        className="team-chip",
        children=[
            html.Div(initials, style=avatar_style),
            html.Span(name or "Equipe", className="team-chip-name"),
        ],
    )


def _build_match_card(match: Dict) -> html.Div:
    """Build a match card for the matches column.

    Args:
        match: Match document.

    Returns:
        Dash HTML container representing a match card.
    """
    kickoff_label, day_label = _format_kickoff(match)
    status_label, status_class = _match_status(match)
    score = _score_text(match)
    league_name = match.get("league") or "Ligue"
    return html.Div(
        className="match-card",
        children=[
            html.Div(
                className="match-card-header",
                children=[
                    html.Span(day_label or league_name, className="match-day-label"),
                    html.Span(status_label, className=f"match-status {status_class}"),
                ],
            ),
            html.Div(
                className="match-card-body",
                children=[
                    _team_chip(match.get("home", ""), match.get("home_logo")),
                    html.Div(
                        className="match-time",
                        children=[
                            html.Div(score, className="match-score"),
                            html.Div(kickoff_label, className="match-kickoff"),
                        ],
                    ),
                    _team_chip(match.get("away", ""), match.get("away_logo")),
                ],
            ),
            html.Div(
                className="match-meta",
                children=[
                    html.Span(f"Competition : {league_name}", className="meta-entry"),
                    html.Span(
                        f"Flashscore ID : {match.get('id', 'n/a')}",
                        className="meta-entry meta-id",
                    ),
                ],
            ),
        ],
    )


def _merge_matches(upcoming: List[Dict], recent_finished: List[Dict]) -> List[Dict]:
    """Merge upcoming and recently finished matches, de-duplicating entries.

    Args:
        upcoming: Matches to come.
        recent_finished: Recently finished matches.

    Returns:
        Combined list without duplicates.
    """
    merged: List[Dict] = []
    seen = set()

    def _push(match: Dict):
        key = match.get("id") or f"{match.get('home')}-{match.get('away')}-{match.get('start_time_utc')}"
        if key in seen:
            return
        seen.add(key)
        merged.append(match)

    for m in (upcoming or []):
        _push(m)
    for m in (recent_finished or []):
        _push(m)
    return merged


def _render_matches_column(league_name: Optional[str], matches: List[Dict]) -> html.Div:
    """Render the left column (matches list + date navigation).

    Args:
        league_name: Selected league name.
        matches: Matches for that league.

    Returns:
        Dash HTML container for the matches column.
    """
    if not league_name:
        return html.Div(
            className="empty-card",
            children=[
                html.H4("Choisissez une ligue"),
                html.P("Utilisez la page Ligues puis cliquez sur Voir les matchs."),
                _create_back_button(None, "link-button"),
            ],
        )

    if not matches:
        return html.Div(
            className="empty-card",
            children=[
                html.H4("Aucun match a venir"),
                html.P("Nous ne trouvons pas de match en cours, à venir ou récemment terminé pour cette ligue."),
            ],
        )

    sorted_matches = sorted(
        matches,
        key=lambda m: m.get("start_timestamp") or (10**15),
    )
    
    matches_by_date = defaultdict(list)
    for match in sorted_matches:
        match_date = None
        ts_str = match.get("start_time_utc")
        target_date = match.get("target_date")
        
        try:
            if ts_str:
                dt = datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                local_dt = dt.astimezone()
                match_date = local_dt.date().isoformat()
            elif target_date:
                match_date = target_date
        except Exception:
            match_date = "unknown"
        
        if match_date:
            matches_by_date[match_date].append(match)
    
    sorted_dates = sorted(matches_by_date.keys())
    
    today = datetime.date.today().isoformat()
    if sorted_dates:
        if today in sorted_dates:
            current_date = today
        else:
            closest_date = min(sorted_dates, key=lambda d: abs((datetime.date.fromisoformat(d) - datetime.date.today()).days))
            current_date = closest_date
    else:
        current_date = today
    
    return html.Div(
        children=[
            html.Div(
                className="section-title",
                children=[
                    html.Span("Matchs de la ligue"),
                    html.Span(f"{len(sorted_matches)} rencontre(s)", className="section-meta"),
                ],
            ),
            # Navigation par date
            html.Div(
                className="match-date-navigator",
                children=[
                    html.Button(
                        "◄",
                        id="prev-date-btn",
                        className="date-nav-btn",
                        n_clicks=0,
                    ),
                    dcc.Dropdown(
                        id="date-selector-dropdown",
                        options=[
                            {"label": _format_date_display(date), "value": date}
                            for date in sorted_dates
                        ],
                        value=current_date,
                        clearable=False,
                        searchable=False,
                        className="date-dropdown",
                    ),
                    html.Button(
                        "►",
                        id="next-date-btn",
                        className="date-nav-btn",
                        n_clicks=0,
                    ),
                ],
            ),
            # Store pour la date actuelle et la liste des dates
            dcc.Store(id="current-date-store", data=current_date),
            dcc.Store(id="available-dates-store", data=sorted_dates),
            dcc.Store(id="all-matches-store", data={date: [
                {
                    "id": m.get("id"),
                    "home": m.get("home"),
                    "away": m.get("away"),
                    "home_logo": m.get("home_logo"),
                    "away_logo": m.get("away_logo"),
                    "start_time_utc": m.get("start_time_utc"),
                    "target_date": m.get("target_date"),
                    "start_timestamp": m.get("start_timestamp"),
                    "status": m.get("status"),
                    "status_code": m.get("status_code"),
                    "home_score": m.get("home_score"),
                    "away_score": m.get("away_score"),
                    "league": m.get("league"),
                }
                for m in matches_list
            ] for date, matches_list in matches_by_date.items()}),
            # Liste des matchs filtrés par date
            html.Div(id="matches-list-by-date", className="matches-list"),
        ]
    )


def _format_date_display(date_str: str) -> str:
    """Convert a YYYY-MM-DD string into a French display label.

    Args:
        date_str: ISO date string.

    Returns:
        Friendly label (Aujourd'hui / Demain / weekday) or a fallback.
    """
    if not date_str or date_str == "unknown":
        return "Date inconnue"
    
    try:
        date = datetime.date.fromisoformat(date_str)
        today = datetime.date.today()
        
        if date == today:
            return f"Aujourd'hui - {date.strftime('%d/%m/%Y')}"
        elif date == today + datetime.timedelta(days=1):
            return f"Demain - {date.strftime('%d/%m/%Y')}"
        elif date == today - datetime.timedelta(days=1):
            return f"Hier - {date.strftime('%d/%m/%Y')}"
        else:
            days_fr = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
            day_name = days_fr[date.weekday()]
            return f"{day_name} {date.strftime('%d/%m/%Y')}"
    except:
        return date_str


def _compute_standings(finished_matches: List[Dict]) -> List[Dict]:
    """Compute a lightweight standings table from finished matches.

    Args:
        finished_matches: Finished matches with scores.

    Returns:
        List of standings rows sorted by points, goal difference, goals for.
    """
    if not finished_matches:
        return []

    ordered = sorted(finished_matches, key=lambda m: m.get("start_timestamp") or 0)
    table: Dict[str, Dict] = {}

    for match in ordered:
        home = match.get("home")
        away = match.get("away")
        hs = match.get("home_score")
        as_ = match.get("away_score")

        if not home or not away or hs is None or as_ is None:
            continue
        
        try:
            home_score = int(hs) if isinstance(hs, (int, float, str)) and str(hs).strip() else None
            away_score = int(as_) if isinstance(as_, (int, float, str)) and str(as_).strip() else None
            
            if home_score is None or away_score is None:
                continue
        except (ValueError, TypeError):
            continue

        # Initialiser les équipes si elles n'existent pas encore
        for team in (home, away):
            if team not in table:
                table[team] = {
                    "team": team,
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "gf": 0,
                    "ga": 0,
                    "form": [],
                }

        table[home]["played"] += 1
        table[away]["played"] += 1
        table[home]["gf"] += home_score
        table[home]["ga"] += away_score
        table[away]["gf"] += away_score
        table[away]["ga"] += home_score

        if home_score > away_score:
            table[home]["wins"] += 1
            table[away]["losses"] += 1
            table[home]["form"].append("W")
            table[away]["form"].append("L")
        elif home_score < away_score:
            table[away]["wins"] += 1
            table[home]["losses"] += 1
            table[away]["form"].append("W")
            table[home]["form"].append("L")
        else:
            table[home]["draws"] += 1
            table[away]["draws"] += 1
            table[home]["form"].append("D")
            table[away]["form"].append("D")


        table[home]["form"] = table[home]["form"][-5:]
        table[away]["form"] = table[away]["form"][-5:]

    standings: List[Dict] = []
    for team, stats in table.items():
        gd = stats["gf"] - stats["ga"]
        points = stats["wins"] * 3 + stats["draws"]
        standings.append(
            {
                "team": team,
                "played": stats["played"],
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "gf": stats["gf"],
                "ga": stats["ga"],
                "gd": gd,
                "points": points,
                "form": stats["form"],
            }
        )


    standings.sort(
        key=lambda r: (
            -r["points"],
            -r["gd"],
            -r["gf"],
            r["team"],
        )
    )
    return standings


def _render_form_badges(form: List[str]) -> html.Div:
    """Génère les badges de forme récente (V/N/D)."""
    badges = []
    for res in form:
        cls = {
            "W": "form-win",
            "D": "form-draw",
            "L": "form-loss",
        }.get(res, "")
        badges.append(html.Span(res, className=f"form-badge {cls}"))
    return html.Div(className="form-badges", children=badges)


def _render_brackets(brackets_data: Dict) -> html.Div:
    """Render cup brackets display using custom HTML with navigation.

    Args:
        brackets_data: Brackets document from MongoDB.

    Returns:
        Dash HTML container for the brackets display.
    """
    
    rounds = brackets_data.get("rounds", [])
    
    if not rounds:
        return html.Div(
            className="empty-card",
            children=[
                html.H4("Brackets non disponibles"),
                html.P("Les brackets n'ont pas encore été scrapés pour cette coupe."),
            ],
        )
    
    
    # Créer tous les rounds (on les affichera tous avec navigation JS)
    rounds_html = []
    
    for idx, round_data in enumerate(rounds):
        round_name = round_data.get("round_name", "Round")
        matches = round_data.get("matches", [])
        
        # Créer les cartes de matchs pour ce round
        match_cards = []
        for match in matches:
            home = match.get("home", "TBD")
            away = match.get("away", "TBD")
            home_score = match.get("home_score")
            away_score = match.get("away_score")
            
            # Déterminer le style du match
            match_style = {
                "backgroundColor": "#ffffff",
                "border": "2px solid #e2e8f0",
                "borderRadius": "12px",
                "padding": "16px",
                "marginBottom": "12px",
                "transition": "all 0.3s ease"
            }
            
            # Créer la carte du match
            match_card = html.Div([
                # Équipe domicile
                html.Div([
                    html.Span(home, style={"fontWeight": "600", "fontSize": "14px", "flex": "1"}),
                    html.Span(
                        str(home_score) if home_score is not None else "-",
                        style={
                            "backgroundColor": "#f1f5f9" if home_score is None else ("#10b981" if home_score is not None and away_score is not None and home_score > away_score else "#f1f5f9"),
                            "color": "#ffffff" if home_score is not None and away_score is not None and home_score > away_score else "#64748b",
                            "padding": "4px 12px",
                            "borderRadius": "6px",
                            "fontWeight": "700",
                            "fontSize": "14px",
                            "minWidth": "40px",
                            "textAlign": "center"
                        }
                    )
                ], style={"display": "flex", "alignItems": "center", "gap": "12px", "marginBottom": "8px"}),
                
                # Équipe extérieur
                html.Div([
                    html.Span(away, style={"fontWeight": "600", "fontSize": "14px", "flex": "1"}),
                    html.Span(
                        str(away_score) if away_score is not None else "-",
                        style={
                            "backgroundColor": "#f1f5f9" if away_score is None else ("#10b981" if home_score is not None and away_score is not None and away_score > home_score else "#f1f5f9"),
                            "color": "#ffffff" if home_score is not None and away_score is not None and away_score > home_score else "#64748b",
                            "padding": "4px 12px",
                            "borderRadius": "6px",
                            "fontWeight": "700",
                            "fontSize": "14px",
                            "minWidth": "40px",
                            "textAlign": "center"
                        }
                    )
                ], style={"display": "flex", "alignItems": "center", "gap": "12px"})
            ], style=match_style, className="bracket-match-card")
            
            match_cards.append(match_card)
        
        # Créer la colonne du round
        round_column = html.Div([
            html.Div(
                round_name,
                style={
                    "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
                    "color": "white",
                    "padding": "12px 20px",
                    "borderRadius": "10px",
                    "fontWeight": "700",
                    "fontSize": "13px",
                    "textAlign": "center",
                    "marginBottom": "16px",
                    "boxShadow": "0 4px 6px -1px rgba(102, 126, 234, 0.3)",
                    "letterSpacing": "0.5px",
                    "textTransform": "uppercase"
                }
            ),
            html.Div(match_cards, style={"minWidth": "280px"})
        ], 
        style={
            "flex": "0 0 auto",
            "display": "flex",
            "flexDirection": "column",
            "padding": "0 16px"
        },
        className=f"bracket-round bracket-round-{idx}"
        )
        
        rounds_html.append(round_column)
    
    return html.Div(
        className="bracket-full-width-container",
        children=[
            html.Div([
                html.H3("🏆 Tableau à élimination", style={"marginBottom": "8px", "fontSize": "20px", "fontWeight": "700", "color": "#1e293b"}),
                html.Div([
                    html.Span("📊 ", style={"fontSize": "14px"}),
                    html.Span(f"{len(rounds)} tour(s) · {sum(len(r.get('matches', [])) for r in rounds)} matchs", style={"color": "#64748b", "fontSize": "14px"})
                ], style={"marginBottom": "24px"}),
            ]),
            html.Div(
                rounds_html,
                style={
                    "display": "flex",
                    "flexDirection": "row",
                    "overflowX": "auto",
                    "overflowY": "visible",
                    "gap": "0px",
                    "padding": "20px 0",
                    "alignItems": "flex-start",
                },
                className="brackets-container"
            )
        ],
    )


def _render_standings_column(league_name: Optional[str], standings_data: Optional[Dict], _brackets_data: Optional[Dict]) -> html.Div:
    """Render the right column (official standings table).

    Args:
        league_name: Selected league name.
        standings_data: Standings document from MongoDB.

    Returns:
        Dash HTML container for the standings column.
    """
    if not league_name:
        return html.Div(
            className="empty-card",
            children=[
                html.H4("Classement indisponible"),
                html.P("Selectionnez d'abord une ligue pour voir le classement."),
            ],
        )
    
    # Pour les coupes, afficher un message approprié (les brackets sont affichés en pleine largeur)
    if is_cup(league_name):
        return html.Div(
            className="empty-card",
            style={
                "backgroundColor": "#f8fafc",
                "border": "2px dashed #cbd5e1",
            },
            children=[
                html.Div(
                    style={"fontSize": "48px", "marginBottom": "16px", "opacity": "0.6"},
                    children="🏆"
                ),
                html.H4(
                    "Compétition à élimination directe",
                    style={"color": "#1e40af", "marginBottom": "12px"}
                ),
                html.P(
                    "Les coupes utilisent un format à élimination directe (brackets) plutôt qu'un classement.",
                    style={"marginBottom": "16px", "color": "#475569"}
                ),
                html.Div(
                    style={
                        "backgroundColor": "#eff6ff",
                        "padding": "16px",
                        "borderRadius": "8px",
                        "border": "1px solid #bfdbfe",
                        "marginTop": "20px",
                    },
                    children=[
                        html.P(
                            "ℹ️ Information",
                            style={"fontWeight": "700", "color": "#1e40af", "marginBottom": "8px"}
                        ),
                        html.P(
                            "Les brackets n'ont pas encore été scrapés pour cette coupe.",
                            style={"fontSize": "0.9em", "color": "#475569", "margin": "0"}
                        ),
                    ]
                ),
            ],
        )

    if not standings_data or not standings_data.get("standings"):
        return html.Div(
            className="empty-card",
            children=[
                html.H4("Classement non disponible"),
                html.P("Le classement officiel n'a pas encore été scrapé pour cette ligue."),
                html.P("Le classement sera disponible après le prochain scraping automatique.", style={"fontSize": "0.9em", "color": "#666"}),
            ],
        )

    standings = standings_data["standings"]
    
    header = html.Div(
        className="standings-header",
        children=[
            html.Div("#", className="col-rank"),
            html.Div("Équipe", className="col-team"),
            html.Div("MJ", className="col-small", title="Matchs Joués"),
            html.Div("V", className="col-small", title="Victoires"),
            html.Div("N", className="col-small", title="Nuls"),
            html.Div("D", className="col-small", title="Défaites"),
            html.Div("BP", className="col-small", title="Buts Pour"),
            html.Div("BC", className="col-small", title="Buts Contre"),
            html.Div("Diff", className="col-small", title="Différence"),
            html.Div("Pts", className="col-points", title="Points"),
        ],
    )

    rows = []
    for team_data in standings:
        goal_diff = team_data.get("goal_difference", 0)
        diff_text = f"+{goal_diff}" if goal_diff > 0 else str(goal_diff)
        
        qual_label = team_data.get("qualification_label", "")
        qual_color = team_data.get("qualification_color", "")
        
        qual_class = ""
        if qual_color:
            if "0, 70, 130" in qual_color:  # Bleu foncé - Champions League Phase de ligue
                qual_class = "qual-ucl-main"
            elif "30, 168, 236" in qual_color:  # Bleu clair - Champions League Qualification
                qual_class = "qual-ucl-qual"
            elif "127, 0, 41" in qual_color:  # Bordeaux - Europa League Phase de ligue
                qual_class = "qual-uel-main"
            elif "184, 134, 11" in qual_color:  # Doré - Conference League
                qual_class = "qual-ecl"
            elif "189, 0, 0" in qual_color:  # Rouge foncé - Playoff/Promotion
                qual_class = "qual-po"
            elif "255, 65, 65" in qual_color:  # Rouge clair - Relégation
                qual_class = "qual-rel"
        
        rows.append(
            html.Div(
                className=f"standings-row {qual_class}",
                children=[
                    html.Div(
                        str(team_data.get("position", "")), 
                        className="col-rank",
                        title=qual_label if qual_label else None
                    ),
                    html.Div(team_data.get("team", ""), className="col-team"),
                    html.Div(str(team_data.get("played", 0)), className="col-small"),
                    html.Div(str(team_data.get("wins", 0)), className="col-small"),
                    html.Div(str(team_data.get("draws", 0)), className="col-small"),
                    html.Div(str(team_data.get("losses", 0)), className="col-small"),
                    html.Div(str(team_data.get("goals_for", 0)), className="col-small"),
                    html.Div(str(team_data.get("goals_against", 0)), className="col-small"),
                    html.Div(diff_text, className="col-small", style={
                        "color": "#10b981" if goal_diff > 0 else ("#ef4444" if goal_diff < 0 else "#94a3b8"),
                        "fontWeight": "700"
                    }),
                    html.Div(str(team_data.get("points", 0)), className="col-points"),
                ],
            )
        )
    
    scraped_at = standings_data.get("scraped_at", "")
    if scraped_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(scraped_at.replace("Z", "+00:00"))
            scraped_str = dt.strftime("%d/%m/%Y %H:%M")
        except:
            scraped_str = "récemment"
    else:
        scraped_str = "récemment"

    return html.Div(
        children=[
            html.Div(
                className="section-title",
                children=[
                    html.Span("Classement officiel Flashscore"),
                    html.Span(f"{len(standings)} équipes", className="section-meta"),
                ],
            ),
            html.Div(className="standings-card", children=[header] + rows),
            _render_qualification_legend(standings_data.get("qualification_legend", [])),
            html.Div(
                style={"fontSize": "0.85em", "color": "#999", "marginTop": "12px", "textAlign": "center"},
                children=f"Mis à jour: {scraped_str}"
            ),
        ]
    )


def _render_qualification_legend(legend_data: List[Dict]) -> html.Div:
    """Génère la légende de qualification/relégation sous le classement."""
    if not legend_data:
        return html.Div()
    
    legend_items = []
    for item in legend_data:
        color = item.get("color", "")
        description = item.get("description", "")
        
        color_class = ""
        if "0, 70, 130" in color:
            color_class = "legend-ucl-main"
        elif "30, 168, 236" in color:
            color_class = "legend-ucl-qual"
        elif "127, 0, 41" in color:
            color_class = "legend-uel-main"
        elif "184, 134, 11" in color:
            color_class = "legend-ecl"
        elif "189, 0, 0" in color:
            color_class = "legend-po"
        elif "255, 65, 65" in color:
            color_class = "legend-rel"
        
        if color_class and description:
            legend_items.append(
                html.Div([
                    html.Span(className=f"legend-color {color_class}"),
                    html.Span(description, className="legend-text")
                ], className="legend-item")
            )
    
    if not legend_items:
        return html.Div()
    
    return html.Div(
        className="standings-legend",
        children=legend_items
    )


def _hero_section(league_name: Optional[str], match_count: int, standings_data: Optional[Dict]) -> html.Div:
    """Génère la section héro en haut de la page."""
    if not league_name:
        return html.Div(
            className="hero-card",
            children=[
                html.H2("Choisissez une ligue"),
                html.P("Depuis l'onglet Ligues, cliquez sur Voir les matchs pour afficher le detail."),
                dcc.Link("Parcourir les ligues", href="/leagues", className="link-button"),
            ],
        )
    
    team_count = len(standings_data.get("standings", [])) if standings_data else 0

    return html.Div(
        className="hero-card",
        children=[
            html.Div(
                className="hero-top",
                children=[
                    html.Div(
                        children=[
                            html.P("Ligue" if not is_cup(league_name) else "Coupe", className="hero-eyebrow"),
                            html.H2(league_name, className="hero-title"),
                        ]
                    ),
                    _create_back_button(league_name, "link-button ghost"),
                ],
            ),
            html.Div(
                className="hero-stats",
                children=[
                    html.Div(
                        className="hero-stat",
                        children=[
                            html.Span("Matchs affichés", className="stat-label"),
                            html.Span(str(match_count), className="stat-value"),
                        ],
                    ),
                    html.Div(
                        className="hero-stat",
                        children=[
                            html.Span("Equipes classees", className="stat-label"),
                            html.Span(str(team_count), className="stat-value"),
                        ],
                    ),
                ],
            ),
        ],
    )


def create_layout() -> html.Div:
    """Crée le layout de la page (conteneurs statiques)."""
    return html.Div(
        className="app-wrapper",
        children=[
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
                                    html.P("Details d'une ligue : matchs et classement"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(id="navbar-container"),
            html.Div(
                className="main-content",
                children=[
                    html.Div(id="league-hero", className="league-hero"),
                    html.Div(
                        id="league-columns-container",
                        className="league-columns",
                        children=[
                            html.Div(id="league-matches-column", className="league-column"),
                            html.Div(id="league-standings-column", className="league-column"),
                        ],
                    ),
                    html.Div(id="bracket-full-width", className="bracket-full-width-container"),
                ],
            ),
        ],
    )


layout = create_layout()


@callback(
    Output("navbar-container", "children"),
    Input("url", "search"),
)
def render_navbar(search: Optional[str]):
    """Render navbar with correct active page based on whether it's a cup or league.
    
    Args:
        search: Dash `Location.search` value.
    
    Returns:
        Navbar component with appropriate active page highlighting.
    """
    league_name = _parse_league_name(search)
    if league_name and is_cup(league_name):
        return create_navbar(current_page="cups")
    return create_navbar(current_page="leagues")


@callback(
    Output("league-columns-container", "style"),
    Output("league-standings-column", "style"),
    Output("bracket-full-width", "style"),
    Input("url", "search"),
)
def adjust_columns_layout(search: Optional[str]):
    """Adjust the layout of columns based on whether it's a cup or league.
    
    For cups with brackets: single column for matches + full-width bracket below.
    For leagues: show both columns in 2fr 1fr grid.
    
    Args:
        search: Dash `Location.search` value.
    
    Returns:
        Tuple containing container style, standings column style, and bracket container style.
    """
    league_name = _parse_league_name(search)
    
    # Vérifier si c'est une coupe
    if league_name and is_cup(league_name):
        # Vérifier si on a des données de bracket
        db = get_db_connection()
        brackets_data = db.get_cup_brackets(league_name)
        
        if brackets_data and brackets_data.get("rounds"):
            # Une seule colonne pour les matchs, bracket en pleine largeur en dessous
            container_style = {
                "display": "grid",
                "gridTemplateColumns": "1fr",
                "gap": "20px",
            }
            standings_style = {"display": "none"}  # Cacher la colonne standings
            bracket_style = {"display": "block", "marginTop": "20px"}  # Afficher le bracket
            return container_style, standings_style, bracket_style
    
    # Pour les ligues : deux colonnes (matchs 2fr, classement 1fr)
    container_style = {
        "display": "grid",
        "gridTemplateColumns": "2fr 1fr",
        "gap": "20px",
    }
    standings_style = {}
    bracket_style = {"display": "none"}  # Cacher le bracket pleine largeur
    
    return container_style, standings_style, bracket_style


@callback(
    Output("league-hero", "children"),
    Output("league-matches-column", "children"),
    Output("league-standings-column", "children"),
    Output("bracket-full-width", "children"),
    Input("url", "search"),
)
def render_league_page(search: Optional[str]):
    """Render league page content based on query string.

    Args:
        search: Dash `Location.search` value.

    Returns:
        Tuple containing hero, matches column, standings column, and full-width bracket.
    """
    league_name = _parse_league_name(search)
    if not league_name:
        hero = _hero_section(None, 0, None)
        empty_left = _render_matches_column(None, [])
        empty_right = _render_standings_column(None, None, None)
        return hero, empty_left, empty_right, html.Div()

    db = get_db_connection()
    
    upcoming_matches = db.get_league_upcoming_matches(league_name)
    recent_finished = db.get_league_recent_finished(league_name, days=RECENT_FINISHED_WINDOW_DAYS)
    matches_for_display = _merge_matches(upcoming_matches, recent_finished)
    
    standings_data = db.get_league_standings(league_name)
    brackets_data = db.get_cup_brackets(league_name) if is_cup(league_name) else None

    hero = _hero_section(league_name, len(matches_for_display), standings_data)
    left_col = _render_matches_column(league_name, matches_for_display)
    right_col = _render_standings_column(league_name, standings_data, brackets_data)
    
    # Bracket pleine largeur pour les coupes
    if brackets_data and brackets_data.get("rounds"):
        bracket_full = _render_brackets(brackets_data)
    else:
        bracket_full = html.Div()
    
    return hero, left_col, right_col, bracket_full


@callback(
    Output("current-date-store", "data"),
    Output("date-selector-dropdown", "value"),
    Input("prev-date-btn", "n_clicks"),
    Input("next-date-btn", "n_clicks"),
    Input("date-selector-dropdown", "value"),
    State("current-date-store", "data"),
    State("available-dates-store", "data"),
    prevent_initial_call=True,
)
def update_current_date(_prev_clicks, _next_clicks, dropdown_value, current_date, available_dates):
    """Update currently selected date using buttons or dropdown.

    Returns:
        Tuple (current_date_store_value, dropdown_value).
    """
    from dash import ctx
    
    if not available_dates or not current_date:
        return current_date, current_date
    
    triggered_id = ctx.triggered_id
    new_date = current_date
    
    try:
        current_index = available_dates.index(current_date)
    except (ValueError, AttributeError):
        current_index = 0
    
    if triggered_id == "prev-date-btn" and current_index > 0:
        new_date = available_dates[current_index - 1]
    elif triggered_id == "next-date-btn" and current_index < len(available_dates) - 1:
        new_date = available_dates[current_index + 1]
    elif triggered_id == "date-selector-dropdown" and dropdown_value:
        new_date = dropdown_value
    
    return new_date, new_date


@callback(
    Output("matches-list-by-date", "children"),
    Input("current-date-store", "data"),
    State("all-matches-store", "data"),
)
def update_matches_display(selected_date, all_matches):
    """Met à jour la liste des cartes de matchs quand la date sélectionnée change."""
    if not selected_date or not all_matches:
        return html.Div(
            className="empty-card",
            children=[
                html.P("Aucun match pour cette date."),
            ],
        )
    
    matches_for_date = all_matches.get(selected_date, [])
    
    if not matches_for_date:
        return html.Div(
            className="empty-card",
            children=[
                html.P("Aucun match programmé pour cette date."),
            ],
        )
    
    sorted_matches = sorted(
        matches_for_date,
        key=lambda m: m.get("start_timestamp") or 0,
    )
    
    cards = [_build_match_card(match) for match in sorted_matches]
    return cards



