"""
Synthetic e-commerce dataset generator.
Produces three CSV files in data/raw/:
  - transactions.csv   (50 000 rows)
  - sessions.csv       (80 000 rows)
  - inventory.csv      (500 rows)
"""
import os
import random
import numpy as np
import pandas as pd
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)
np.random.seed(42)

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

REGIONS = ["North America", "Europe", "Asia-Pacific", "Latin America", "Middle East"]
CATEGORIES = ["Electronics", "Apparel", "Home & Kitchen", "Sports", "Beauty", "Books", "Toys"]
DEVICES = ["Desktop", "Mobile", "Tablet"]
PRODUCTS = [f"PROD-{i:04d}" for i in range(1, 501)]


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def generate_transactions(n: int = 50_000) -> pd.DataFrame:
    dates = pd.date_range("2023-01-01", "2024-12-31", periods=n)
    # seasonal revenue boost in Q4
    month = dates.month
    seasonal = np.where(month == 12, 1.5, np.where(month == 11, 1.3, 1.0))

    df = pd.DataFrame({
        "transaction_id": [f"TXN-{i:07d}" for i in range(n)],
        "date": dates.date,
        "region": np.random.choice(REGIONS, n, p=[0.35, 0.25, 0.25, 0.10, 0.05]),
        "category": np.random.choice(CATEGORIES, n),
        "product_id": np.random.choice(PRODUCTS, n),
        "units": np.random.randint(1, 15, n),
        "unit_price": np.round(np.random.lognormal(3.5, 0.8, n), 2),
        "discount_pct": np.round(np.random.beta(2, 8, n) * 40, 1),  # 0-40 %
        "customer_id": [f"CUST-{random.randint(1, 10000):06d}" for _ in range(n)],
    })
    df["revenue"] = np.round(
        df["units"] * df["unit_price"] * (1 - df["discount_pct"] / 100) * seasonal, 2
    )
    return df


def generate_sessions(n: int = 80_000) -> pd.DataFrame:
    timestamps = pd.date_range("2023-01-01", "2024-12-31", periods=n)
    df = pd.DataFrame({
        "session_id": [f"SESS-{i:08d}" for i in range(n)],
        "timestamp": timestamps,
        "user_id": [f"USR-{random.randint(1, 10000):06d}" for _ in range(n)],
        "device": np.random.choice(DEVICES, n, p=[0.45, 0.40, 0.15]),
        "page_views": np.random.randint(1, 20, n),
        "session_duration_s": np.random.exponential(180, n).astype(int).clip(5, 1800),
        "converted": np.random.choice([0, 1], n, p=[0.82, 0.18]),
        "region": np.random.choice(REGIONS, n, p=[0.35, 0.25, 0.25, 0.10, 0.05]),
    })
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.day_name()
    return df


def generate_inventory() -> pd.DataFrame:
    df = pd.DataFrame({
        "product_id": PRODUCTS,
        "category": np.random.choice(CATEGORIES, len(PRODUCTS)),
        "stock_units": np.random.randint(0, 500, len(PRODUCTS)),
        "reorder_level": np.random.randint(20, 80, len(PRODUCTS)),
        "unit_cost": np.round(np.random.lognormal(3.0, 0.7, len(PRODUCTS)), 2),
        "supplier": [fake.company() for _ in PRODUCTS],
    })
    df["health"] = np.where(
        df["stock_units"] == 0, "Out of Stock",
        np.where(df["stock_units"] < df["reorder_level"], "Low Stock", "Healthy")
    )
    return df


def generate_all(force: bool = False) -> dict[str, str]:
    """
    Generate all datasets and write to CSV.
    Returns dict of dataset_name -> file_path.
    """
    _ensure_dir(RAW_DIR)
    paths = {
        "transactions": os.path.join(RAW_DIR, "transactions.csv"),
        "sessions": os.path.join(RAW_DIR, "sessions.csv"),
        "inventory": os.path.join(RAW_DIR, "inventory.csv"),
    }

    if not force and all(os.path.exists(p) for p in paths.values()):
        print("[DataGen] Raw data already exists — skipping generation.")
        return paths

    print("[DataGen] Generating synthetic datasets …")
    generate_transactions().to_csv(paths["transactions"], index=False)
    print(f"  ✓ transactions.csv (50 000 rows)")
    generate_sessions().to_csv(paths["sessions"], index=False)
    print(f"  ✓ sessions.csv (80 000 rows)")
    generate_inventory().to_csv(paths["inventory"], index=False)
    print(f"  ✓ inventory.csv (500 rows)")
    return paths


if __name__ == "__main__":
    generate_all(force=True)
