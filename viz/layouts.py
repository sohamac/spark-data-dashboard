"""
Dash page layouts for the three tabs.
All charts are built from Pandas DataFrames returned by spark transforms.
"""
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd

from viz.components import (
    kpi_card, section_header, loading_chart,
    ACCENT, ACCENT2, SUCCESS, WARNING, DANGER, BG_CARD, BG_INNER, TEXT, MUTED
)

# ── Shared Plotly layout defaults ────────────────────────────────────────────
CHART_THEME = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="Inter, sans-serif", color=TEXT, size=12),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT)),
    xaxis=dict(gridcolor="#2d2d4e", zerolinecolor="#2d2d4e", color=TEXT),
    yaxis=dict(gridcolor="#2d2d4e", zerolinecolor="#2d2d4e", color=TEXT),
)


def apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(**CHART_THEME, title=dict(text=title, font=dict(size=14, color=TEXT)))
    return fig


# ──────────────────────────────────────────────
# TAB 1 — OVERVIEW
# ──────────────────────────────────────────────

def build_overview(kpis: dict, rev_time: pd.DataFrame,
                   rev_region: pd.DataFrame, rev_cat: pd.DataFrame) -> html.Div:

    # ── KPI row ──
    kpi_row = dbc.Row([
        kpi_card("Total Revenue",    f"${kpis['total_revenue']:,.0f}",   icon="💰", color=ACCENT),
        kpi_card("Total Orders",     f"{kpis['total_orders']:,}",         icon="🛒", color=ACCENT2),
        kpi_card("Avg Order Value",  f"${kpis['avg_order_value']:,.2f}",  icon="📦", color=SUCCESS),
        kpi_card("Conversion Rate",  f"{kpis['conversion_rate']}%",       icon="🎯", color=WARNING),
    ], className="mb-3 g-3")

    # ── Revenue over time ──
    fig_time = go.Figure()
    fig_time.add_trace(go.Scatter(
        x=rev_time["year_month"], y=rev_time["revenue"],
        name="Monthly Revenue", mode="lines+markers",
        line=dict(color=ACCENT, width=2),
        marker=dict(size=5),
        fill="tozeroy", fillcolor="rgba(99,102,241,0.12)",
    ))
    fig_time.add_trace(go.Scatter(
        x=rev_time["year_month"], y=rev_time["rolling_avg"],
        name="3-Month Rolling Avg", mode="lines",
        line=dict(color=ACCENT2, width=2, dash="dot"),
    ))
    apply_theme(fig_time, "Revenue Over Time")

    # ── Revenue by region ──
    fig_region = px.bar(
        rev_region, x="revenue", y="region", orientation="h",
        color="revenue", color_continuous_scale=[[0, "#312e81"], [1, ACCENT]],
        text=rev_region["revenue"].apply(lambda v: f"${v:,.0f}"),
    )
    fig_region.update_traces(textposition="outside", marker_line_width=0)
    fig_region.update_coloraxes(showscale=False)
    apply_theme(fig_region, "Revenue by Region")

    # ── Category donut ──
    fig_cat = go.Figure(go.Pie(
        labels=rev_cat["category"], values=rev_cat["revenue"],
        hole=0.55,
        marker=dict(colors=[ACCENT, ACCENT2, SUCCESS, WARNING, DANGER, "#a855f7", "#ec4899"],
                    line=dict(color=BG_INNER, width=2)),
        textinfo="label+percent",
        textfont=dict(color=TEXT, size=11),
    ))
    apply_theme(fig_cat, "Revenue by Category")

    return html.Div([
        kpi_row,
        dbc.Row([
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Revenue Trend", "Monthly revenue with 3-month rolling average"),
                    loading_chart("chart-time", dcc.Graph(id="chart-revenue-time",
                                                          figure=fig_time, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12, md=8,
            ),
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Category Mix"),
                    loading_chart("chart-cat", dcc.Graph(id="chart-category",
                                                         figure=fig_cat, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12, md=4,
            ),
        ], className="mb-3 g-3"),
        dbc.Row([
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Revenue by Region"),
                    loading_chart("chart-region", dcc.Graph(id="chart-region",
                                                            figure=fig_region, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12,
            ),
        ], className="mb-3"),
    ])


# ──────────────────────────────────────────────
# TAB 2 — TRENDS
# ──────────────────────────────────────────────

def build_trends(heatmap_df: pd.DataFrame, device_df: pd.DataFrame,
                 mom_df: pd.DataFrame) -> html.Div:

    # ── Heatmap ──
    fig_heat = go.Figure(go.Heatmap(
        z=heatmap_df.values,
        x=[str(h) for h in heatmap_df.columns],
        y=heatmap_df.index.tolist(),
        colorscale=[[0, BG_INNER], [0.5, "#4f46e5"], [1, ACCENT2]],
        hoverongaps=False,
        showscale=True,
        colorbar=dict(tickfont=dict(color=TEXT)),
    ))
    apply_theme(fig_heat, "Session Activity — Day of Week × Hour")
    fig_heat.update_xaxes(title="Hour of Day")
    fig_heat.update_yaxes(title="")

    # ── Device stacked area ──
    fig_device = px.area(
        device_df, x="year_month", y="sessions", color="device",
        color_discrete_map={"Desktop": ACCENT, "Mobile": ACCENT2, "Tablet": SUCCESS},
    )
    fig_device.update_traces(line_width=1)
    apply_theme(fig_device, "Sessions by Device Over Time")

    # ── MoM growth bar ──
    mom_clean = mom_df.dropna(subset=["growth_pct"])
    colors = [SUCCESS if v >= 0 else DANGER for v in mom_clean["growth_pct"]]
    fig_mom = go.Figure(go.Bar(
        x=mom_clean["year_month"],
        y=mom_clean["growth_pct"],
        marker_color=colors,
        text=mom_clean["growth_pct"].apply(lambda v: f"{v:+.1f}%"),
        textposition="outside",
    ))
    apply_theme(fig_mom, "Month-over-Month Revenue Growth %")
    fig_mom.add_hline(y=0, line_color=MUTED, line_dash="dash", line_width=1)

    return html.Div([
        dbc.Row([
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Activity Heatmap", "Sessions by day and hour of day"),
                    loading_chart("chart-heat", dcc.Graph(id="chart-heatmap",
                                                          figure=fig_heat, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12,
            ),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Device Split Over Time"),
                    loading_chart("chart-dev", dcc.Graph(id="chart-device",
                                                         figure=fig_device, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12, md=7,
            ),
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("MoM Revenue Growth"),
                    loading_chart("chart-mom", dcc.Graph(id="chart-mom",
                                                         figure=fig_mom, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12, md=5,
            ),
        ], className="mb-3 g-3"),
    ])


# ──────────────────────────────────────────────
# TAB 3 — DEEP DIVE
# ──────────────────────────────────────────────

def build_deep_dive(scatter_df: pd.DataFrame, top_df: pd.DataFrame,
                    inv_df: pd.DataFrame) -> html.Div:

    # ── Scatter: discount vs revenue ──
    fig_scatter = px.scatter(
        scatter_df, x="avg_discount", y="total_revenue",
        size="total_units", color="category",
        hover_name="product_id",
        color_discrete_sequence=[ACCENT, ACCENT2, SUCCESS, WARNING, DANGER, "#a855f7", "#ec4899"],
        size_max=30, opacity=0.7,
        labels={"avg_discount": "Avg Discount %", "total_revenue": "Total Revenue ($)"},
    )
    apply_theme(fig_scatter, "Discount % vs Revenue (bubble = units sold)")

    # ── Top 10 products table ──
    top_df_display = top_df[["rank", "product_id", "category",
                              "total_revenue", "total_units", "orders"]].copy()
    top_df_display["total_revenue"] = top_df_display["total_revenue"].apply(lambda v: f"${v:,.0f}")

    table = dbc.Table.from_dataframe(
        top_df_display.rename(columns={
            "rank": "#", "product_id": "Product", "category": "Category",
            "total_revenue": "Revenue", "total_units": "Units", "orders": "Orders"
        }),
        striped=False, bordered=False, hover=True, responsive=True,
        className="dash-table",
    )

    # ── Inventory health donut + bar ──
    health_counts = inv_df["health"].value_counts().reset_index()
    health_counts.columns = ["health", "count"]
    color_map = {"Healthy": SUCCESS, "Low Stock": WARNING, "Out of Stock": DANGER}
    fig_inv = px.pie(
        health_counts, names="health", values="count",
        color="health", color_discrete_map=color_map,
        hole=0.5,
    )
    fig_inv.update_traces(
        textinfo="label+percent",
        textfont=dict(color=TEXT),
        marker=dict(line=dict(color=BG_INNER, width=2)),
    )
    apply_theme(fig_inv, "Inventory Health Status")

    return html.Div([
        dbc.Row([
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Discount vs Revenue", "Each bubble = one product; size = units sold"),
                    loading_chart("chart-scatter", dcc.Graph(id="chart-scatter",
                                                             figure=fig_scatter, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12, md=8,
            ),
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Inventory Health"),
                    loading_chart("chart-inv", dcc.Graph(id="chart-inv",
                                                         figure=fig_inv, config={"displayModeBar": False})),
                ]), className="dash-card"),
                xs=12, md=4,
            ),
        ], className="mb-3 g-3"),
        dbc.Row([
            dbc.Col(
                dbc.Card(dbc.CardBody([
                    section_header("Top 10 Products by Revenue"),
                    html.Div(table, className="table-wrapper"),
                ]), className="dash-card"),
                xs=12,
            ),
        ], className="mb-3"),
    ])
