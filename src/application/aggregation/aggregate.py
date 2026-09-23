"""Gold layer – compute daily summaries from silver quotes."""
import logging
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List

from sqlalchemy.orm import Session

from src.domain.entities.quote import DailySummary, Quote
from src.infrastructure.database import repositories

logger = logging.getLogger(__name__)


def _group_by_date(quotes: List[Quote]) -> Dict[str, List[Quote]]:
    grouped: Dict[str, List[Quote]] = defaultdict(list)
    for q in quotes:
        key = q.quote_date.strftime("%Y-%m-%d")
        grouped[key].append(q)
    return grouped


def _compute_daily_summary(
    symbol: str,
    asset_type: str,
    date_str: str,
    quotes: List[Quote],
) -> DailySummary:
    prices = [q.price for q in quotes]
    sorted_quotes = sorted(quotes, key=lambda q: q.quote_date)

    open_price = sorted_quotes[0].price
    close_price = sorted_quotes[-1].price
    high_price = max(prices)
    low_price = min(prices)

    pct_change: Decimal | None = None
    if open_price and open_price != 0:
        pct_change = ((close_price - open_price) / open_price) * Decimal("100")

    trade_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    return DailySummary(
        id=str(uuid.uuid4()),
        symbol=symbol,
        asset_type=asset_type,
        trade_date=trade_date,
        open_price=open_price,
        close_price=close_price,
        high_price=high_price,
        low_price=low_price,
        pct_change=pct_change,
        currency=quotes[0].currency,
    )


def aggregate_symbol(
    db: Session,
    symbol: str,
    start: datetime | None = None,
    end: datetime | None = None,
) -> int:
    """Compute and save daily summaries only for dates newer than the last saved summary."""
    latest_summary = repositories.find_latest_daily_summary(db, symbol)
    if start is None and latest_summary is not None:
        start = latest_summary.trade_date

    quotes = repositories.find_quotes_by_symbol(db, symbol, start=start, end=end)
    if not quotes:
        logger.warning("No silver quotes found for %s", symbol)
        return 0

    grouped = _group_by_date(quotes)
    saved = 0
    for date_str, day_quotes in grouped.items():
        trade_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if latest_summary is not None and trade_date <= latest_summary.trade_date:
            continue
        summary = _compute_daily_summary(
            symbol=symbol,
            asset_type=day_quotes[0].asset_type,
            date_str=date_str,
            quotes=day_quotes,
        )
        try:
            repositories.save_daily_summary(db, summary)
            saved += 1
        except Exception as exc:
            logger.error("Failed to save daily summary %s %s: %s", symbol, date_str, exc)

    logger.info("Aggregated %d days for %s", saved, symbol)
    return saved


def run_aggregation_pipeline(
    db: Session, symbols: List[str]
) -> Dict[str, int]:
    """Aggregate gold summaries for a list of symbols."""
    started_at = time.monotonic()
    logger.info("Starting gold aggregation for %d symbols", len(symbols))
    results = {sym: aggregate_symbol(db, sym) for sym in symbols}
    logger.info(
        "Gold aggregation complete: symbols=%d summaries=%d duration=%.2fs",
        len(symbols), sum(results.values()), time.monotonic() - started_at,
    )
    return results
