# Spark Data Dashboard

This repo contains **two separate demo components** that share a tech stack (PySpark) but are not currently wired together:

1. **`pipeline.py`** -- a standalone live data ingestion script that polls the CoinCap crypto API every 10s, processes the response with PySpark (schema enforcement, type casting), and appends it to a local SQLite database (`crypto_metrics.db`).
2. **`app.py`** -- an interactive Plotly Dash dashboard that visualizes **synthetic, locally-generated e-commerce data** (transactions, sessions, inventory) via `spark_engine/data_generator.py`. It does not read from `crypto_metrics.db`.

If you run both, you'll have a live crypto ingestion job running in one terminal and a dashboard showing unrelated synthetic e-commerce data in another. This is intentional as two separate demos of the same stack, but it's worth being upfront about: **the dashboard is not currently visualizing the pipeline's output.**

## Component 1: Live Data Pipeline (`pipeline.py`)

```
External REST API (CoinCap) --> pipeline.py --> PySpark (schema + casting) --> SQLite (crypto_metrics.db)
```

- Polls `https://api.coincap.io/v2/assets` every 10 seconds (configurable via `POLL_INTERVAL`).
- Has real error handling: request timeouts, `try/except` around the HTTP call, and structured logging.
- Runs as an infinite polling loop, not a message-queue-based system -- there's no retry/backoff on failure beyond logging and continuing to the next poll cycle, and no distributed fault tolerance. "Resilient" here means "handles a failed HTTP call gracefully," not "production-grade streaming infrastructure."

Run it:
```bash
python pipeline.py          # runs continuously
python pipeline.py --test   # runs one batch and exits
```

## Component 2: Dashboard (`app.py`)

```
spark_engine/data_generator.py (synthetic data) --> PySpark DataFrames --> Plotly Dash UI
```

- Generates synthetic e-commerce transaction/session/inventory data on first run (cached as CSVs after that).
- Loads it into cached PySpark DataFrames.
- Serves an interactive dashboard (Overview / Trends / Deep Dive tabs) with region and category filters.

Run it:
```bash
python app.py
```
Navigate to `http://localhost:8050`.

## Setup

```bash
pip install -r requirements.txt
```

## Known Limitations

- **The two components are not connected.** Making the dashboard visualize the live pipeline's `crypto_metrics.db` output instead of (or alongside) synthetic data is the natural next step if this becomes one integrated demo.
- **Java 11 required** -- PySpark 3.5.x uses `javax.security.auth.Subject.getSubject()`, which was removed in Java 21. Run with Java 11.
- **Local mode only** -- Spark runs in `local[*]` mode; not configured for a cluster.
- **No retry/backoff in the pipeline poller** -- a failed API call is logged and the loop just waits for the next interval; there's no exponential backoff or dead-letter handling.

## License

MIT License -- see LICENSE for details.
