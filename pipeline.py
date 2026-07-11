import time
import json
import logging
import sqlite3
import requests
import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, current_timestamp
from pyspark.sql.types import StructType, StructField, StringType, DoubleType

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
API_URL = "https://api.coincap.io/v2/assets"
DB_PATH = "crypto_data.db"
POLL_INTERVAL = 10  # seconds (shortened for testing)

def fetch_live_data():
    """Fetch live cryptocurrency data from CoinCap API."""
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        data = response.json().get('data', [])
        logger.info(f"Successfully fetched {len(data)} records.")
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data: {e}")
        return []

def init_db():
    """Initialize SQLite database for downstream analytics."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS crypto_metrics (
            id TEXT,
            symbol TEXT,
            name TEXT,
            priceUsd REAL,
            marketCapUsd REAL,
            volumeUsd24Hr REAL,
            changePercent24Hr REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def process_and_store(spark, data):
    """Process data using PySpark and store in SQLite."""
    if not data:
        return False

    # Define schema for strict type checking
    schema = StructType([
        StructField("id", StringType(), True),
        StructField("symbol", StringType(), True),
        StructField("name", StringType(), True),
        StructField("priceUsd", StringType(), True),
        StructField("marketCapUsd", StringType(), True),
        StructField("volumeUsd24Hr", StringType(), True),
        StructField("changePercent24Hr", StringType(), True)
    ])

    # Load into Spark DataFrame
    df = spark.createDataFrame(data, schema=schema)

    # Clean and cast data types
    cleaned_df = df.select(
        col("id"),
        col("symbol"),
        col("name"),
        col("priceUsd").cast(DoubleType()).alias("priceUsd"),
        col("marketCapUsd").cast(DoubleType()).alias("marketCapUsd"),
        col("volumeUsd24Hr").cast(DoubleType()).alias("volumeUsd24Hr"),
        col("changePercent24Hr").cast(DoubleType()).alias("changePercent24Hr")
    ).withColumn("timestamp", current_timestamp())

    # Write to local SQLite database
    pandas_df = cleaned_df.toPandas()
    
    conn = sqlite3.connect(DB_PATH)
    pandas_df.to_sql('crypto_metrics', conn, if_exists='append', index=False)
    conn.close()
    
    logger.info("Successfully processed and stored batch.")
    return True

def main():
    test_mode = "--test" in sys.argv
    logger.info(f"Starting Live Data Pipeline{' (Test Mode)' if test_mode else ''}...")
    init_db()
    
    # Initialize Spark Session
    spark = SparkSession.builder \
        .appName("LiveDataPipeline") \
        .config("spark.driver.memory", "2g") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")
    
    try:
        while True:
            logger.info("--- New Batch ---")
            raw_data = fetch_live_data()
            success = process_and_store(spark, raw_data)
            
            if test_mode:
                if success:
                    logger.info("Test mode completed successfully. Exiting.")
                    break
                else:
                    logger.error("Test mode failed to process data.")
                    sys.exit(1)
                    
            logger.info(f"Sleeping for {POLL_INTERVAL} seconds...")
            time.sleep(POLL_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Pipeline stopped by user.")
    finally:
        spark.stop()
        logger.info("Spark session terminated.")

if __name__ == "__main__":
    main()
