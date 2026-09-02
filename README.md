# fin-data

Financial data collection system – scrapers, medallion-architecture data pipeline, and REST API.

## Overview

`fin-data` collects financial data from public APIs, stores it in PostgreSQL following the **medallion architecture** (bronze → silver → gold), and exposes it via a FastAPI REST API.

### Data Sources

| Category | Symbols | Source |
|---|---|---|
| Cryptocurrencies | BTCUSD, ETHUSD, BNBUSD, SOLUSD, ADAUSD, ENA, HYPE, AAVE, SUI, GS, ALGN, LINK, NEAR, PENDLE, SYRUP, SPECTRA | CoinGecko |
| Brazilian Stocks | PETR4, ITUB4, SAPR11, CEAB3, VALE3, … | Yahoo Finance |
| ETFs | IVVB11, BOVA11, DIVO11, SMAL11, … | Yahoo Finance |
| BR Macro Indexes | SELIC, CDI, IPCA | Banco Central do Brasil |
| Brazilian Real Estate Index | IFIX | Banco Central do Brasil |
| Currency Pairs | USDBRL, JPYBRL, USDEUR, BTCUSD, ETHUSD | Open ER API |

## Architecture

```
src/
├── config/          # Settings (pydantic-settings)
├── domain/
│   ├── entities/    # Plain data-classes (RawQuote, Quote, DailySummary)
│   └── repositories/# Repository protocols
├── infrastructure/
│   ├── database/    # SQLAlchemy engine, models, repository implementations
│   └── scrapers/    # HTTP scrapers (crypto, stocks, indexes, currencies)
├── application/
│   ├── ingestion/   # Bronze layer – raw data ingestion
│   ├── transformation/ # Silver layer – data cleaning & validation
│   └── aggregation/ # Gold layer – daily OHLC summaries
├── api/
│   ├── app.py       # FastAPI factory
│   └── routers/     # quotes, ingestion endpoints
└── orchestration/   # APScheduler background jobs
```

## Quick Start

### Using Docker Compose

```bash
cp .env.example .env
# Edit .env with your settings
docker compose up -d
```

The API will be available at `http://localhost:8000`.  
OpenAPI docs: `http://localhost:8000/docs`

### Local Development

```bash
uv sync --dev
# Set DATABASE_URL in .env
uv run python main.py
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/quotes/{symbol}/latest` | Latest price for a symbol |
| GET | `/api/v1/quotes/{symbol}/history` | Price history (filterable by date) |
| GET | `/api/v1/quotes/{symbol}/summary` | Daily OHLC summaries |
| POST | `/api/v1/ingestion/run` | Trigger full pipeline manually |

## Testing

```bash
uv run pytest tests/unit/ -v
```

## Medallion Architecture

- **Bronze** – raw JSON payloads stored as-is (`bronze_quotes` table)
- **Silver** – parsed, validated quotes with typed fields (`silver_quotes` table)
- **Gold** – aggregated daily OHLC summaries (`gold_daily_summaries` table)

## Orchestration

The scheduler runs automatically on startup:
- **Every weekday at 13:00 UTC** – full pipeline (stocks, ETFs)
- **Every hour at :05** – crypto and currency pairs

Set `SCHEDULER_ENABLED=false` to disable.
