# 1. Preserve each data source's native periodicity

## Status

Accepted

## Context

The medallion pipeline (bronze → silver → gold) stores every quote/index value
under a single `trade_date` column in `gold_daily_summaries` (and `quote_date`
in `silver_quotes`). Because the column is named/shaped like a "daily" table,
it is tempting to assume every symbol must have exactly one row per business
day, and to "fill gaps" or resample sparser series to match.

In practice, tracked symbols come from sources with very different native
publication frequencies:

- **Stocks / ETFs / crypto / currency pairs**: priced daily (or near-daily).
- **SELIC** (BCB SGS series `432`): published daily by the Banco Central, but
  the value only changes when Copom meets (~every 45 days); BCB republishes
  the same value on every business day in between.
- **CDI** (BCB SGS series `12`): also daily.
- **IPCA** (BCB SGS series `433`): a genuinely **monthly** index — the Brazilian
  central bank publishes exactly one value per month, not one per day.

We already hit a real bug from conflating these: the index scraper originally
called the BCB "last N records" endpoint (`ultimos/{n}`) using a day-count as
`n`. That endpoint caps at 20 records and has no notion of calendar days, so
large historical loads silently returned only the last 6-20 raw entries
instead of years of history, and the returned dates did not line up with what
callers expected.

## Decision

Ingestion, transformation, and aggregation must **preserve the native
periodicity of each source series** and must never force, pad, resample, or
infer additional rows to make a series "daily":

- Fetch history using the date-range/native pagination the source actually
  supports (e.g. BCB's `dados?dataInicial=...&dataFinal=...`), not an
  endpoint whose parameter is silently reinterpreted as something else (e.g.
  "last N records" being used as if it meant "last N days").
- Store exactly the (date, value) pairs the source returns — one row per
  value the provider actually published. A monthly series (IPCA) is expected
  to have ~12 rows/year in `gold_daily_summaries`; a daily series (SELIC, CDI,
  stocks, ETFs, currencies) is expected to have ~one row per business day.
- Do not write code that assumes `count(rows) == count(calendar days)` or
  that back-fills missing dates by carrying forward the last known value.
  Consumers that need a continuous daily series (e.g. for charting) must do
  that resampling explicitly at query/read time, not at ingestion time.
- When adding a new tracked asset/source, document its real publication
  frequency (daily, monthly, "changes only on X event", etc.) so reviewers
  can sanity-check record counts instead of assuming everything is daily.

## Consequences

- Row counts per symbol in `silver_quotes` / `gold_daily_summaries` will
  legitimately differ by asset type (e.g. IPCA: ~72 rows over 6 years vs.
  SELIC: ~2191 rows over the same period). This is correct and expected, not
  a data-quality bug.
- Scripts and dashboards that compute date-based statistics (gaps, moving
  averages, etc.) must be periodicity-aware per symbol/asset type instead of
  assuming a uniform daily grid.
- Any future scraper must fetch history via an endpoint/parameter that
  actually means "date range", to avoid repeating the `ultimos/{n}` bug.
