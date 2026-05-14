"""
Spark Data Dashboard — Entry Point
====================================
Run:  python app.py
Open: http://localhost:8050
"""
import os
import sys
import warnings
warnings.filterwarnings("ignore")

# ── Silence noisy Java/Spark logs before importing PySpark ───────────────────
os.environ["PYSPARK_SUBMIT_ARGS"] = (
    "--conf spark.ui.showConsoleProgress=false pyspark-shell"
)

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc

# ── Internal modules ─────────────────────────────────────────────────────────
from spark_engine.session import get_spark
from spark_engine.data_generator import generate_all
from spark_engine import transforms as T
from viz import callbacks as CB
from viz.components import filter_panel

# ────────────────────────────────────────────────────────────────────────────
# 1. Generate synthetic data (skipped if CSVs already exist)
# ────────────────────────────────────────────────────────────────────────────
print("\n╔══════════════════════════════════════════════╗")
print("║      ⚡ Spark Data Dashboard  v1.0           ║")
print("╚══════════════════════════════════════════════╝\n")

paths = generate_all()

# ────────────────────────────────────────────────────────────────────────────
# 2. Initialise Spark and load DataFrames
# ────────────────────────────────────────────────────────────────────────────
print("[Spark] Starting local SparkSession …")
spark = get_spark()
print("[Spark] Session ready ✓\n")

print("[Spark] Loading raw data …")
txn_df = T.load_transactions(spark, paths["transactions"])
sess_df = T.load_sessions(spark, paths["sessions"])
inv_df  = T.load_inventory(spark, paths["inventory"])

# Cache for fast repeated callbacks
txn_df.cache()
sess_df.cache()
inv_df.cache()

# Warm up the cache with one action
txn_count  = txn_df.count()
sess_count = sess_df.count()
print(f"[Spark] Loaded {txn_count:,} transactions + {sess_count:,} sessions ✓\n")

# ────────────────────────────────────────────────────────────────────────────
# 3. Share state with callbacks module
# ────────────────────────────────────────────────────────────────────────────
CB.app_state.update({
    "spark": spark,
    "txn":   txn_df,
    "sess":  sess_df,
    "inv":   inv_df,
})

# ────────────────────────────────────────────────────────────────────────────
# 4. Build Dash app
# ────────────────────────────────────────────────────────────────────────────
REGIONS    = [r["region"]   for r in txn_df.select("region").distinct().collect()]
CATEGORIES = [c["category"] for c in txn_df.select("category").distinct().collect()]

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],
    title="⚡ Spark Dashboard",
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"},
        {"name": "description",
         "content": "Real-time e-commerce analytics dashboard powered by Apache Spark and Plotly Dash"},
    ],
    suppress_callback_exceptions=True,
)

# Register callbacks before layout is set
CB.register_callbacks(app)

# ── Layout ───────────────────────────────────────────────────────────────────
app.layout = html.Div(id="app-shell", children=[
    dbc.Container([

        # ── Header ──────────────────────────────────────────────────────────
        html.Div([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span("⚡", style={"marginRight": "8px"}),
                        html.Span("Spark", className="header-logo"),
                        html.Span(" Dashboard",
                                  style={"color": "#e2e8f0", "fontWeight": 700,
                                         "fontSize": "1.5rem", "letterSpacing": "-0.5px"}),
                    ]),
                    html.P("E-Commerce Analytics · Apache Spark + Plotly Dash",
                           className="header-subtitle"),
                ], xs=12, md=8),
                dbc.Col([
                    html.Div([
                        html.Span(className="live-dot"),
                        "Spark Running Locally",
                    ], className="live-badge", style={"float": "right", "marginTop": "8px"}),
                ], xs=12, md=4, className="d-flex align-items-start justify-content-end"),
            ]),
        ], className="dash-header"),

        html.Hr(style={"borderColor": "#2d2d4e", "margin": "12px 0 20px"}),

        # ── Filter Panel ─────────────────────────────────────────────────────
        filter_panel(sorted(REGIONS), sorted(CATEGORIES)),

        # ── Tabs ─────────────────────────────────────────────────────────────
        dbc.Tabs(
            id="main-tabs",
            active_tab="tab-overview",
            children=[
                dbc.Tab(label="📊  Overview",   tab_id="tab-overview"),
                dbc.Tab(label="📈  Trends",     tab_id="tab-trends"),
                dbc.Tab(label="🔍  Deep Dive",  tab_id="tab-deep-dive"),
            ],
        ),

        # Tab content is rendered by callback
        html.Div(id="tab-content", style={"minHeight": "500px"}),

        # ── Footer ───────────────────────────────────────────────────────────
        html.Hr(style={"borderColor": "#2d2d4e", "marginTop": "32px"}),
        html.P(
            [
                "Built with ",
                html.A("Apache Spark", href="https://spark.apache.org", target="_blank",
                       style={"color": "#6366f1"}),
                " · ",
                html.A("Plotly Dash", href="https://dash.plotly.com", target="_blank",
                       style={"color": "#22d3ee"}),
                f"  ·  {txn_count:,} rows processed",
            ],
            style={"color": "#64748b", "fontSize": "0.78rem",
                   "textAlign": "center", "padding": "12px 0 24px"},
        ),

    ], fluid=True, style={"maxWidth": "1400px"}),
])

# ────────────────────────────────────────────────────────────────────────────
# 5. Run
# ────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[Dash] Starting server on http://localhost:8050 …")
    print("[Dash] Press Ctrl+C to stop.\n")
    app.run(debug=False, host="0.0.0.0", port=8050)
