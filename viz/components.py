"""
Reusable Dash UI components.
"""
import dash_bootstrap_components as dbc
from dash import html

# ── Colour palette (dark theme) ──────────────────────────────────────────────
ACCENT   = "#6366f1"      # indigo
ACCENT2  = "#22d3ee"      # cyan
SUCCESS  = "#10b981"      # emerald
WARNING  = "#f59e0b"      # amber
DANGER   = "#ef4444"      # red
BG_CARD  = "#1e1e2e"
BG_INNER = "#13131f"
TEXT     = "#e2e8f0"
MUTED    = "#64748b"


def kpi_card(title: str, value: str, delta: str = "", icon: str = "📊",
             color: str = ACCENT) -> dbc.Col:
    """A single KPI metric card."""
    delta_color = SUCCESS if (delta.startswith("+") or delta == "") else DANGER
    return dbc.Col(
        dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Span(icon, style={"fontSize": "1.8rem"}),
                    html.Div([
                        html.P(title, className="kpi-title"),
                        html.H3(value, className="kpi-value",
                                style={"color": color}),
                        html.Span(delta, className="kpi-delta",
                                  style={"color": delta_color}) if delta else None,
                    ], style={"marginLeft": "12px"}),
                ], className="kpi-inner"),
            ])
        ], className="kpi-card"),
        xs=12, sm=6, md=3,
    )


def section_header(title: str, subtitle: str = "") -> html.Div:
    return html.Div([
        html.H5(title, className="section-title"),
        html.P(subtitle, className="section-subtitle") if subtitle else None,
    ], className="section-header")


def filter_panel(regions: list[str], categories: list[str]) -> dbc.Card:
    """Global filter bar placed in the header."""
    from dash import dcc
    region_opts  = [{"label": "All Regions", "value": "All"}] + \
                   [{"label": r, "value": r} for r in regions]
    cat_opts     = [{"label": "All Categories", "value": "All"}] + \
                   [{"label": c, "value": c} for c in categories]

    return dbc.Card(
        dbc.CardBody(
            dbc.Row([
                dbc.Col([
                    html.Label("Date Range", className="filter-label"),
                    dcc.DatePickerRange(
                        id="filter-date-range",
                        start_date="2023-01-01",
                        end_date="2024-12-31",
                        display_format="MMM D, YYYY",
                        className="date-picker",
                    ),
                ], xs=12, md=4),

                dbc.Col([
                    html.Label("Region", className="filter-label"),
                    dcc.Dropdown(
                        id="filter-region",
                        options=region_opts,
                        value="All",
                        clearable=False,
                        className="dash-dropdown",
                    ),
                ], xs=12, md=3),

                dbc.Col([
                    html.Label("Category", className="filter-label"),
                    dcc.Dropdown(
                        id="filter-category",
                        options=cat_opts,
                        value="All",
                        clearable=False,
                        className="dash-dropdown",
                    ),
                ], xs=12, md=3),

                dbc.Col([
                    html.Label("‎", className="filter-label"),  # spacer
                    dbc.Button("↺  Reset", id="btn-reset", color="secondary",
                               outline=True, className="reset-btn"),
                ], xs=12, md=2, className="d-flex align-items-end"),
            ])
        ),
        className="filter-card",
    )


def loading_chart(child_id: str, children) -> html.Div:
    from dash import dcc
    return dcc.Loading(
        children,
        type="dot",
        color=ACCENT,
    )
