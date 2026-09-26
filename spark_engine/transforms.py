"""
All Spark transformations for the dashboard.

Each function accepts a SparkSession and file paths, runs transformations,
and returns a Pandas DataFrame ready for Plotly.
"""
from __future__ import annotations
import os
import sqlite3
from typing import Optional, Tuple, List
import pandas as pd
from pyspark.sql import SparkSession, DataFrame as SparkDF
from pyspark.sql import functions as F
from pyspark.sql.window import Window
from pyspark.sql.types import (
    StructType, StructField, StringType, DoubleType, IntegerType, DateType
)

PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "processed")

# Default location of the SQLite DB that the standalone pipeline.py process
# writes to. Resolved relative to this file so it works regardless of the
# working directory app.py or pipeline.py is launched from.
DEFAULT_CRYPTO_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "crypto_data.db")

CRYPTO_SCHEMA = StructType([
    StructField("id", StringType(), True),
    StructField("symbol", StringType(), True),
    StructField("name", StringType(), True),
    StructField("priceUsd", DoubleType(), True),
    StructField("marketCapUsd", DoubleType(), True),
    StructField("volumeUsd24Hr", DoubleType(), True),
    StructField("changePercent24Hr", DoubleType(), True),
    StructField("timestamp", StringType(), True),
])


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


def load_crypto_metrics(spark: SparkSession, db_path: Optional[str] = None) -> SparkDF:
    """Load the rows the standalone `pipeline.py` process has written to SQLite.

    pipeline.py and app.py are two separate processes with two separate
    SparkSessions -- there's no live in-memory link between them. This function
    is the actual connection: it re-reads pipeline.py's SQLite output fresh
    each time it's called, so the dashboard reflects whatever pipeline.py has
    ingested so far.

    Returns an empty (but correctly-schema'd) Spark DataFrame if the DB or
    table doesn't exist yet, so the dashboard can render a friendly empty
    state instead of crashing when pipeline.py hasn't been started.
    """
    db_path = db_path or DEFAULT_CRYPTO_DB_PATH

    if not os.path.exists(db_path):
        return spark.createDataFrame([], schema=CRYPTO_SCHEMA)

    conn = sqlite3.connect(db_path)
    try:
        pdf = pd.read_sql("SELECT * FROM crypto_metrics", conn)
    except (pd.errors.DatabaseError, sqlite3.OperationalError):
        # Table doesn't exist yet -- pipeline.py hasn't written a batch.
        pdf = pd.DataFrame(columns=[f.name for f in CRYPTO_SCHEMA.fields])
    finally:
        conn.close()

    if pdf.empty:
        return spark.createDataFrame([], schema=CRYPTO_SCHEMA)

    pdf["timestamp"] = pdf["timestamp"].astype(str)
    return spark.createDataFrame(pdf[[f.name for f in CRYPTO_SCHEMA.fields]], schema=CRYPTO_SCHEMA)


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
    """Sessions count by day_of_week x hour -> pivot table."""
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
# 5. CRYPTO TRANSFORMS (pipeline.py integration)
# ──────────────────────────────────────────────

def crypto_latest_snapshot(crypto: SparkDF) -> "pd.DataFrame":
    """Most recent ingested row per symbol, sorted by market cap."""
    empty_cols = ["id", "symbol", "name", "priceUsd", "marketCapUsd",
                  "volumeUsd24Hr", "changePercent24Hr", "timestamp"]
    if crypto.rdd.isEmpty():
        return pd.DataFrame(columns=empty_cols)

    window = Window.partitionBy("symbol").orderBy(F.desc("timestamp"))
    return (
        crypto.withColumn("rn", F.row_number().over(window))
        .filter(F.col("rn") == 1)
        .drop("rn")
        .orderBy(F.desc("marketCapUsd"))
        .toPandas()
    )


def crypto_price_history(crypto: SparkDF, symbols: Optional[List[str]] = None) -> "pd.DataFrame":
    """Price history across ingestion batches, optionally filtered to a symbol list."""
    if crypto.rdd.isEmpty():
        return pd.DataFrame(columns=["symbol", "timestamp", "priceUsd"])

    df = crypto
    if symbols:
        df = df.filter(F.col("symbol").isin(symbols))
    return (
        df.select("symbol", "timestamp", "priceUsd")
        .orderBy("timestamp")
        .toPandas()
    )


# ──────────────────────────────────────────────
# 6. FILTERED TRANSFORMS (called by callbacks)
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
