"""
Dash callbacks — wires filter controls to Spark re-queries and chart updates.
Uses a module-level cache (app_state) populated by app.py on startup.
"""
from dash import Input, Output, State, callback, no_update
from dash.exceptions import PreventUpdate
import dash

from spark_engine import transforms as T
from viz import layouts

# Populated by app.py before the server starts
app_state: dict = {}


def register_callbacks(app: dash.Dash) -> None:
    """Attach all callbacks to the Dash app."""

    @app.callback(
        Output("tab-content", "children"),
        Input("main-tabs", "active_tab"),
        Input("filter-date-range", "start_date"),
        Input("filter-date-range", "end_date"),
        Input("filter-region", "value"),
        Input("filter-category", "value"),
    )
    def render_tab(active_tab, start_date, end_date, region, category):
        spark   = app_state["spark"]
        txn_raw = app_state["txn"]
        sess_raw= app_state["sess"]
        inv_raw = app_state["inv"]

        # Apply user filters via Spark
        txn, sess = T.apply_filters(txn_raw, sess_raw, start_date, end_date, region, category)

        if active_tab == "tab-overview":
            kpis      = T.kpi_summary(txn, sess)
            rev_time  = T.revenue_over_time(txn)
            rev_region= T.revenue_by_region(txn)
            rev_cat   = T.revenue_by_category(txn)
            return layouts.build_overview(kpis, rev_time, rev_region, rev_cat)

        elif active_tab == "tab-trends":
            heatmap_df = T.heatmap_activity(sess)
            device_df  = T.device_trend(sess)
            mom_df     = T.mom_growth(txn)
            return layouts.build_trends(heatmap_df, device_df, mom_df)

        elif active_tab == "tab-deep-dive":
            scatter_df = T.discount_vs_revenue(txn)
            top_df     = T.top_products(txn, n=10)
            inv_df     = T.inventory_health(inv_raw)
            return layouts.build_deep_dive(scatter_df, top_df, inv_df)

        return dash.no_update

    @app.callback(
        Output("filter-region", "value"),
        Output("filter-category", "value"),
        Output("filter-date-range", "start_date"),
        Output("filter-date-range", "end_date"),
        Input("btn-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def reset_filters(n):
        return "All", "All", "2023-01-01", "2024-12-31"
