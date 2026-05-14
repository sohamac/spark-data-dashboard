"""
All Spark transformations for the dashboard.

Each function accepts a SparkSession and file paths, runs transformations,
and returns a Pandas DataFrame ready for Plotly.
"""
from __future__ import annotations
import os
from typing import Optional, Tuple
from pyspark.sql import SparkSession, DataFrame as SparkDF
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, DateType
)

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


# ──────────────────────────────────────────────
# 1. INGESTION
# ──────────────────────────────────────────────

def load_transactions(spark: SparkSession, csv_path: str) -> SparkDF:
    return (
        spark.read.option("header", True).option("inferSchema", True)
        .csv(csv_path)
        .withColumn("date", F.to_date("date", "yyyy-MM-dd"))
        .withColumn("year_month", F.date_format("date", "yyyy-MM"))
        .withColumn("month_num", F.month("date"))
        .withColumn("year", F.year("date"))
    )


def load_sessions(spark: SparkSession, csv_path: str) -> SparkDF:
    return (
        spark.read.option("header", True).option("inferSchema", True)
        .csv(csv_path)
        .withColumn("timestamp", F.to_timestamp("timestamp"))
    )


def load_inventory(spark: SparkSession, csv_path: str) -> SparkDF:
    return (
        spark.read.option("header", True).option("inferSchema", True)
        .csv(csv_path)
    )


# ──────────────────────────────────────────────
# 2. OVERVIEW TRANSFORMS
# ──────────────────────────────────────────────

def kpi_summary(txn: SparkDF, sess: SparkDF) -> dict:
    """Top-level KPIs returned as a plain dict."""
    txn_agg = txn.agg(
        F.round(F.sum("revenue"), 2).alias("total_revenue"),
        F.count("transaction_id").alias("total_orders"),
        F.round(F.avg("revenue"), 2).alias("avg_order_value"),
        F.round(F.avg("discount_pct"), 1).alias("avg_discount"),
    ).collect()[0]

    sess_agg = sess.agg(
        F.count("session_id").alias("total_sessions"),
        F.round(F.avg("converted") * 100, 2).alias("conversion_rate"),
    ).collect()[0]

    return {
        "total_revenue": txn_agg["total_revenue"],
        "total_orders": txn_agg["total_orders"],
        "avg_order_value": txn_agg["avg_order_value"],
        "avg_discount": txn_agg["avg_discount"],
        "total_sessions": sess_agg["total_sessions"],
        "conversion_rate": sess_agg["conversion_rate"],
    }


def revenue_over_time(txn: SparkDF) -> "pd.DataFrame":
    """Monthly revenue with 3-month rolling average (window function)."""
    monthly = (
        txn.groupBy("year_month")
        .agg(F.round(F.sum("revenue"), 2).alias("revenue"),
             F.count("transaction_id").alias("orders"))
        .orderBy("year_month")
    )

    window = (
        Window.orderBy("year_month")
        .rowsBetween(-2, 0)
    )
    return (
        monthly
        .withColumn("rolling_avg", F.round(F.avg("revenue").over(window), 2))
        .toPandas()
    )


def revenue_by_region(txn: SparkDF) -> "pd.DataFrame":
    return (
        txn.groupBy("region")
        .agg(F.round(F.sum("revenue"), 2).alias("revenue"),
             F.count("transaction_id").alias("orders"))
        .orderBy(F.desc("revenue"))
        .toPandas()
    )


def revenue_by_category(txn: SparkDF) -> "pd.DataFrame":
    return (
        txn.groupBy("category")
        .agg(F.round(F.sum("revenue"), 2).alias("revenue"))
        .orderBy(F.desc("revenue"))
        .toPandas()
    )


# ──────────────────────────────────────────────
# 3. TRENDS TRANSFORMS
# ──────────────────────────────────────────────

def heatmap_activity(sess: SparkDF) -> "pd.DataFrame":
    """Sessions count by day_of_week × hour → pivot table."""
    grouped = (
        sess.groupBy("day_of_week", "hour")
        .agg(F.count("session_id").alias("sessions"))
        .toPandas()
    )
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = grouped.pivot(index="day_of_week", columns="hour", values="sessions").reindex(day_order)
    return pivot


def device_trend(sess: SparkDF) -> "pd.DataFrame":
    """Monthly sessions by device type."""
    return (
        sess.withColumn("year_month", F.date_format("timestamp", "yyyy-MM"))
        .groupBy("year_month", "device")
        .agg(F.count("session_id").alias("sessions"))
        .orderBy("year_month", "device")
        .toPandas()
    )


def mom_growth(txn: SparkDF) -> "pd.DataFrame":
    """Month-over-month revenue growth %."""
    monthly = (
        txn.groupBy("year_month")
        .agg(F.round(F.sum("revenue"), 2).alias("revenue"))
        .orderBy("year_month")
    )
    lag_window = Window.orderBy("year_month")
    return (
        monthly
        .withColumn("prev_revenue", F.lag("revenue", 1).over(lag_window))
        .withColumn(
            "growth_pct",
            F.round((F.col("revenue") - F.col("prev_revenue")) / F.col("prev_revenue") * 100, 2)
        )
        .toPandas()
    )


# ──────────────────────────────────────────────
# 4. DEEP DIVE TRANSFORMS
# ──────────────────────────────────────────────

def discount_vs_revenue(txn: SparkDF) -> "pd.DataFrame":
    """Aggregated discount% vs revenue per product (bubble = units)."""
    return (
        txn.groupBy("product_id", "category")
        .agg(
            F.round(F.avg("discount_pct"), 1).alias("avg_discount"),
            F.round(F.sum("revenue"), 2).alias("total_revenue"),
            F.sum("units").alias("total_units"),
        )
        .toPandas()
    )


def top_products(txn: SparkDF, n: int = 10) -> "pd.DataFrame":
    """Top N products by revenue with rank column."""
    window = Window.orderBy(F.desc("total_revenue"))
    return (
        txn.groupBy("product_id", "category")
        .agg(
            F.round(F.sum("revenue"), 2).alias("total_revenue"),
            F.sum("units").alias("total_units"),
            F.count("transaction_id").alias("orders"),
        )
        .withColumn("rank", F.rank().over(window))
        .filter(F.col("rank") <= n)
        .orderBy("rank")
        .toPandas()
    )


def inventory_health(inv: SparkDF) -> "pd.DataFrame":
    return (
        inv.withColumn(
            "stock_value",
            F.round(F.col("stock_units") * F.col("unit_cost"), 2)
        )
        .orderBy("stock_units")
        .toPandas()
    )


# ──────────────────────────────────────────────
# 5. FILTERED TRANSFORMS (called by callbacks)
# ──────────────────────────────────────────────

def apply_filters(
    txn: SparkDF,
    sess: SparkDF,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    region: Optional[str] = None,
    category: Optional[str] = None,
) -> Tuple[SparkDF, SparkDF]:
    """Apply common filter predicates and return filtered DataFrames."""
    if start_date:
        txn = txn.filter(F.col("date") >= F.lit(start_date))
        sess = sess.filter(F.col("timestamp") >= F.lit(start_date))
    if end_date:
        txn = txn.filter(F.col("date") <= F.lit(end_date))
        sess = sess.filter(F.col("timestamp") <= F.lit(end_date))
    if region and region != "All":
        txn = txn.filter(F.col("region") == region)
        sess = sess.filter(F.col("region") == region)
    if category and category != "All":
        txn = txn.filter(F.col("category") == category)
    return txn, sess
