# ⚡ Spark Data Dashboard

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Apache Spark](https://img.shields.io/badge/Apache%20Spark-3.5-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white)
![Plotly Dash](https://img.shields.io/badge/Plotly%20Dash-2.x-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Java](https://img.shields.io/badge/Java-11-007396?style=for-the-badge&logo=java&logoColor=white)

**A production-grade data dashboard prototype integrating Apache Spark for large-scale data processing with a rich Python visualization layer built on Plotly Dash.**

</div>

---

## 📸 Preview

### Overview Tab — KPI Cards + Revenue Trend
> 4 KPI metric cards, revenue time-series with Spark rolling window average, region breakdown, and category donut chart.

### Trends Tab — Activity Heatmap + Device Split
> Session activity heatmap (day-of-week × hour), stacked device area chart, and month-over-month revenue growth powered by Spark lag window functions.

### Deep Dive Tab — Product Analytics
> Discount vs revenue bubble scatter (500 products), inventory health status, top-10 product leaderboard ranked by Spark `rank()` window function.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────┐
│               Synthetic Data (130k+ rows)                │
│   transactions.csv · sessions.csv · inventory.csv        │
└────────────────────┬─────────────────────────────────────┘
                     │
┌────────────────────▼─────────────────────────────────────┐
│             Apache Spark 3.5 (PySpark)                   │
│  • Ingestion & schema enforcement                         │
│  • groupBy aggregations (revenue, sessions, inventory)    │
│  • Window functions: rolling avg, lag (MoM), rank (top-N) │
│  • Filter pushdown for interactive filtering              │
│  • DataFrames cached for fast repeated queries           │
└────────────────────┬─────────────────────────────────────┘
                     │  Arrow-backed toPandas()
┌────────────────────▼─────────────────────────────────────┐
│          Plotly Dash 2.x (Visualization Layer)           │
│  • 3-tab dashboard: Overview · Trends · Deep Dive        │
│  • Real-time filter callbacks (date, region, category)    │
│  • Dark glassmorphism UI with animated KPI cards         │
└──────────────────────────────────────────────────────────┘
```

---

## ✨ Features

### Data Processing (Spark)
| Spark Feature | Used For |
|---|---|
| `groupBy` + `agg` | Revenue, session & inventory aggregations |
| `Window.rowsBetween` | 3-month rolling revenue average |
| `lag()` window function | Month-over-month growth % calculation |
| `rank()` window function | Top-10 product leaderboard |
| Filter pushdown | All interactive dashboard filters |
| Arrow `toPandas()` | High-speed Spark → Pandas bridge |
| `DataFrame.cache()` | Warm-up for fast repeated queries |

### Visualization (Plotly Dash)
- **KPI Cards** — Total Revenue, Orders, Avg Order Value, Conversion Rate
- **Line chart** — Monthly revenue with rolling average overlay
- **Heatmap** — Session activity by day-of-week and hour
- **Stacked Area** — Device split (Desktop / Mobile / Tablet) over time
- **Bar charts** — Revenue by region, MoM growth
- **Bubble Scatter** — Discount % vs Revenue (500 products)
- **Donut charts** — Category mix, Inventory health
- **Data table** — Top 10 ranked products

---

## 📁 Project Structure

```
spark-dashboard/
├── app.py                    # Dash app entry point
├── run.sh                    # Startup script (sets correct JAVA_HOME)
├── requirements.txt          # All Python dependencies
├── spark_engine/
│   ├── session.py            # SparkSession factory (Java 11 config)
│   ├── data_generator.py     # Synthetic dataset generator (Faker + NumPy)
│   └── transforms.py         # All Spark transformations
├── viz/
│   ├── components.py         # Reusable UI components (KPI card, filters)
│   ├── layouts.py            # 3-tab chart layouts (Plotly)
│   └── callbacks.py          # Dash callbacks (filter → Spark → chart)
└── assets/
    └── styles.css            # Dark glassmorphism CSS theme
```

> **Note:** `data/` is excluded from git via `.gitignore`. Raw CSVs are auto-generated on first run using `data_generator.py`.

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | |
| Java | **11** (LTS) | ⚠️ PySpark 3.5 is incompatible with Java 21+ |
| pip | Latest | |

Download Java 11: [Adoptium Temurin 11](https://adoptium.net/temurin/releases/?version=11)

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/spark-data-dashboard.git
cd spark-data-dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the dashboard
bash run.sh
```

Then open **http://localhost:8050** in your browser.

> The first run generates 130,000+ rows of synthetic data automatically.

### Manual Run (if not using run.sh)

```bash
# Set Java 11 explicitly (adjust path for your OS)
# macOS:
export JAVA_HOME=/Library/Java/JavaVirtualMachines/temurin-11.jdk/Contents/Home
# Linux:
# export JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64

python app.py
```

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Data Processing | Apache Spark 3.5.1 (PySpark) |
| Visualization | Plotly Dash 2.17 |
| Charts | Plotly Express + Graph Objects |
| UI Components | Dash Bootstrap Components |
| Styling | Vanilla CSS (dark glassmorphism) |
| Data Generation | Faker + NumPy |
| Python | 3.9+ |

---

## ⚠️ Known Limitations

- **Java 11 required** — PySpark 3.5.x uses `javax.security.auth.Subject.getSubject()` which was removed in Java 21. Always run with Java 11.
- **Local mode only** — Runs Spark in `local[*]` mode; not configured for a cluster.
- **Synthetic data** — Dataset is procedurally generated; swap `data_generator.py` with a real data source for production use.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
Built with ⚡ Apache Spark · 📊 Plotly Dash · 🐍 Python
</div>
