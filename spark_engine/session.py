"""
SparkSession factory — singleton with local-mode config and Arrow optimization.
"""
from __future__ import annotations
from pyspark.sql import SparkSession
from typing import Optional
import os

_spark: Optional[SparkSession] = None


def get_spark() -> SparkSession:
    """Return (or create) the shared SparkSession."""
    global _spark
    if _spark is not None:
        return _spark

    # Suppress verbose Spark / Hadoop logs
    os.environ.setdefault("PYSPARK_PYTHON", "python3")
    # Fix for Java 21+: Subject.getSubject() removed; restore via add-opens
    os.environ.setdefault(
        "JAVA_TOOL_OPTIONS",
        "--add-opens=java.base/javax.security.auth=ALL-UNNAMED "
        "--add-opens=java.base/java.lang=ALL-UNNAMED",
    )

    java_opts = (
        "--add-opens=java.base/javax.security.auth=ALL-UNNAMED "
        "--add-opens=java.base/java.lang=ALL-UNNAMED"
    )

    _spark = (
        SparkSession.builder
        .master("local[*]")
        .appName("DataDashboard")
        # Fix Java 21+ compatibility
        .config("spark.driver.extraJavaOptions", java_opts)
        .config("spark.executor.extraJavaOptions", java_opts)
        # Enable Arrow-based columnar transfers for fast toPandas()
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.sql.shuffle.partitions", "8")
        .config("spark.driver.memory", "2g")
        # Silence most Spark noise
        .config("spark.ui.showConsoleProgress", "false")
        .getOrCreate()
    )

    # Only show ERRORs in the console
    _spark.sparkContext.setLogLevel("ERROR")
    return _spark


def stop_spark() -> None:
    """Gracefully stop the SparkSession."""
    global _spark
    if _spark is not None:
        _spark.stop()
        _spark = None
