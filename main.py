import datetime
import json
import subprocess
from pathlib import Path
from typing import Tuple

import pandas as pd
from dash import Dash, Input, Output, State, dcc, html, dash_table


DATA_DIR = Path("data")
UPCOMING_OUTPUT = DATA_DIR / "dash_upcoming.json"
FINISHED_OUTPUT = DATA_DIR / "dash_finished.json"
UPCOMING_SCRIPT = Path("src") / "scrapy" / "fetch_upcoming.py"
FINISHED_SCRIPT = Path("src") / "scrapy" / "fetch_finished.py"


def run_cmd(cmd: list[str]) -> Tuple[bool, str]:
    """Execute a subprocess command and return success flag and a short message."""
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        success = proc.returncode == 0
        stdout = (proc.stdout or "").strip()
        stderr = (proc.stderr or "").strip()

        # Keep only the last line of stdout (usually the export message)
        stdout_line = stdout.splitlines()[-1] if stdout else ""

        # Truncate stderr to a few lines for display
        stderr_lines = stderr.splitlines()
        if len(stderr_lines) > 5:
            stderr_display = "\n".join(stderr_lines[:5] + [f"... ({len(stderr_lines) - 5} lignes supprimees)"])
        else:
            stderr_display = "\n".join(stderr_lines)

        msg = f"Command: {' '.join(cmd)}\nExit: {proc.returncode}"
        if stdout_line:
            msg += f"\nStdout (dernier): {stdout_line}"
        if stderr_display:
            msg += f"\nStderr (resume):\n{stderr_display}"
        return success, msg
    except Exception as exc:  # pragma: no cover
        return False, f"Execution failed: {exc}"


def load_df(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return pd.DataFrame(data)
    except Exception:
        return pd.DataFrame()


app = Dash(__name__)
app.title = "Flashscore Football Dashboard"

today_str = datetime.date.today().isoformat()
current_month = f"{datetime.date.today():%Y-%m}"

# Ensure data directory exists for outputs
DATA_DIR.mkdir(parents=True, exist_ok=True)

app.layout = html.Div(
    style={
        "minHeight": "100vh",
        "padding": "28px",
        "fontFamily": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        "background": "radial-gradient(circle at 20% 20%, #0f172a 0, #0b1221 40%, #0a0f1c 70%, #080c17 100%)",
        "color": "#e5e7eb",
    },
    children=[
        html.Div(
            style={
                "display": "flex",
                "justifyContent": "space-between",
                "alignItems": "center",
                "marginBottom": "18px",
            },
            children=[
                html.Div(
                    children=[
                        html.H2(
                            "Flashscore Football Dashboard",
                            style={"margin": 0, "fontSize": "26px", "fontWeight": "700"},
                        ),
                        html.P(
                            "Scrapy + Dash · Données Flashscore en temps réel",
                            style={"margin": "4px 0 0 0", "color": "#9ca3af"},
                        ),
                    ]
                ),
                html.Div(
                    style={
                        "display": "inline-flex",
                        "gap": "10px",
                        "alignItems": "center",
                        "background": "#111827",
                        "padding": "8px 12px",
                        "borderRadius": "12px",
                        "border": "1px solid #1f2937",
                        "boxShadow": "0 10px 30px rgba(0,0,0,0.25)",
                    },
                    children=[
                        html.Span("Mode : ", style={"color": "#9ca3af"}),
                        dcc.Dropdown(
                            id="dataset-type",
                            options=[
                                {"label": "Matches à venir / Live", "value": "upcoming"},
                                {"label": "Matches terminés", "value": "finished"},
                            ],
                            value="upcoming",
                            clearable=False,
                            style={"width": "220px"},
                        ),
                    ],
                ),
            ],
        ),
        html.Div(
            style={
                "background": "#0f172a",
                "border": "1px solid #1f2937",
                "borderRadius": "14px",
                "padding": "16px",
                "marginBottom": "18px",
                "boxShadow": "0 12px 40px rgba(0,0,0,0.35)",
            },
            children=[
                html.Div(
                    style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "alignItems": "flex-end"},
                    children=[
                        html.Div(
                            children=[
                                html.Label("Date / Mois", style={"color": "#9ca3af", "fontSize": "13px"}),
                                dcc.DatePickerSingle(
                                    id="date-picker",
                                    date=today_str,
                                    display_format="YYYY-MM-DD",
                                    style={"background": "#111827", "border": "1px solid #1f2937"},
                                ),
                                dcc.Checklist(
                                    id="month-mode",
                                    options=[{"label": "Prendre tout le mois (matchs terminés)", "value": "month"}],
                                    value=["month"],
                                    style={
                                        "marginTop": "8px",
                                        "color": "#e5e7eb",
                                        "fontSize": "13px",
                                    },
                                    inputStyle={"marginRight": "6px"},
                                ),
                            ]
                        ),
                        html.Div(
                            children=[
                                html.Button(
                                    "Rafraîchir les données",
                                    id="fetch-btn",
                                    n_clicks=0,
                                    style={
                                        "background": "linear-gradient(120deg, #22d3ee, #3b82f6)",
                                        "color": "white",
                                        "border": "none",
                                        "padding": "12px 18px",
                                        "borderRadius": "10px",
                                        "cursor": "pointer",
                                        "fontWeight": "600",
                                        "boxShadow": "0 10px 25px rgba(59,130,246,0.35)",
                                    },
                                ),
                            ]
                        ),
                    ],
                )
            ],
        ),
        dash_table.DataTable(
            id="data-table",
            columns=[],
            data=[],
            page_size=20,
            style_table={"overflowX": "auto", "background": "#0b1221", "borderRadius": "12px"},
            style_header={
                "backgroundColor": "#111827",
                "color": "#e5e7eb",
                "fontWeight": "700",
                "border": "1px solid #1f2937",
            },
            style_cell={
                "padding": "10px",
                "fontSize": "14px",
                "backgroundColor": "#0b1221",
                "color": "#e5e7eb",
                "border": "1px solid #1f2937",
            },
            style_data_conditional=[
                {"if": {"row_index": "odd"}, "backgroundColor": "#0d1526"},
                {
                    "if": {"column_id": "status"},
                    "color": "#38bdf8",
                    "fontWeight": "600",
                },
                {
                    "if": {"column_id": "score"},
                    "fontWeight": "700",
                    "color": "#fbbf24",
                },
            ],
            markdown_options={"html": True},
        ),
        dcc.Store(id="data-store"),
    ],
)


def prepare_table(df: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    """Select and format columns for display with logos."""
    if df.empty:
        return [], []

    def logo_md(name: str, url: str) -> str:
        if url:
            return f"<img src='{url}' alt='{name}' style='height:32px;width:32px;border-radius:50%;'/>"
        return ""

    df = df.copy()
    df["home_logo_md"] = df.apply(lambda r: logo_md(r.get("home", ""), r.get("home_logo", "")), axis=1)
    df["away_logo_md"] = df.apply(lambda r: logo_md(r.get("away", ""), r.get("away_logo", "")), axis=1)
    def fmt_kickoff(ts: str) -> str:
        """
        Convertit l'horodatage ISO UTC en heure locale de la machine.
        Affiche le format lisible, ex: 09 Dec 2025 15:00 (local).
        """
        if not ts:
            return ""
        try:
            dt_utc = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            dt_local = dt_utc.astimezone()  # convertit vers le fuseau local
            return dt_local.strftime("%d %b %Y %H:%M (local)")
        except Exception:
            return ts

    df["kickoff"] = df.get("start_time_utc").apply(fmt_kickoff)
    def fmt_score(r) -> str:
        hs = r.get("home_score")
        as_ = r.get("away_score")
        if hs is None or as_ is None or pd.isna(hs) or pd.isna(as_):
            return "N/A"
        return f"{int(hs)} - {int(as_)}"

    df["score"] = df.apply(fmt_score, axis=1)

    display_cols = [
        ("home_logo_md", ""),
        ("home", "Home"),
        ("score", "Score"),
        ("away", "Away"),
        ("away_logo_md", ""),
        ("status", "Status"),
        ("kickoff", "Kickoff (UTC)"),
        ("league", "Competition"),
    ]

    df_display = df[[c for c, _ in display_cols]]
    columns = []
    for col_id, col_name in display_cols:
        col_def = {"id": col_id, "name": col_name}
        if "logo_md" in col_id:
            col_def["presentation"] = "markdown"
        columns.append(col_def)

    return columns, df_display.to_dict("records")


@app.callback(
    Output("data-table", "columns"),
    Output("data-table", "data"),
    Input("fetch-btn", "n_clicks"),
    State("dataset-type", "value"),
    State("date-picker", "date"),
    State("month-mode", "value"),
    prevent_initial_call=False,
)
def fetch_and_display(_clicks, dataset_type: str, date_val: str, month_mode: list):
    """
    Run the appropriate Scrapy script and display the resulting JSON.
    """
    date_val = date_val or today_str
    month_selected = (month_mode or []) and "month" in month_mode
    month_val = date_val[:7] if date_val else current_month

    if dataset_type == "upcoming":
        output_path = UPCOMING_OUTPUT
        cmd = ["python", str(UPCOMING_SCRIPT), "--date", date_val, "--output", str(output_path)]
    else:
        output_path = FINISHED_OUTPUT
        if month_selected:
            cmd = ["python", str(FINISHED_SCRIPT), "--month", month_val, "--output", str(output_path)]
        else:
            cmd = ["python", str(FINISHED_SCRIPT), "--date", date_val, "--output", str(output_path)]

    run_cmd(cmd)
    df = load_df(output_path)
    return prepare_table(df)


def run():
    # Dash>=3.0 utilise app.run au lieu de run_server
    app.run(debug=True, host="0.0.0.0", port=8050)


if __name__ == "__main__":
    run()
