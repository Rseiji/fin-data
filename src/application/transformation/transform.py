"""Silver layer – parse and validate bronze records into clean quotes."""
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.quote import Quote, RawQuote
from src.infrastructure.database import repositories

logger = logging.getLogger(__name__)


def _parse_price(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        for fmt in (
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%f%z",
        ):
            try:
                dt = datetime.strptime(value, fmt)
                if dt.tzinfo is None:
                    return dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except ValueError:
                continue
    return None


def _first_non_none_timestamp(payload: Dict[str, Any]) -> Optional[datetime]:
    """Return the first parseable timestamp from a set of well-known payload keys."""
    for key in ("timestamp", "last_updated_at", "last_updated", "date"):
        ts = _parse_timestamp(payload.get(key))
        if ts is not None:
            return ts
    return None


def _raw_to_quote(raw: RawQuote) -> Optional[Quote]:
    try:
        payload: Dict[str, Any] = json.loads(raw.raw_payload)
    except json.JSONDecodeError as exc:
        logger.error("Cannot parse payload for %s: %s", raw.id, exc)
        return None

    price_key = "price" if "price" in payload else "value"
    price = _parse_price(payload.get(price_key))
    if price is None:
        logger.warning("No price in record %s", raw.id)
        return None

    ts = _first_non_none_timestamp(payload) or datetime.now(tz=timezone.utc)
    currency = payload.get("currency", "USD")

    return Quote(
        id=str(uuid.uuid4()),
        bronze_id=raw.id,
        symbol=raw.symbol,
        asset_type=raw.asset_type,
        price=price,
        currency=currency,
        quote_date=ts,
        source=raw.source,
    )


def transform_symbol(db: Session, symbol: str, limit: int | None = None) -> int:
    """Transform only bronze records newer than the latest silver quote for the symbol."""
    latest_quote = repositories.find_latest_quote(db, symbol)
    raw_quotes = repositories.find_raw_quotes_by_symbol(db, symbol, limit=limit)

    if latest_quote is not None:
        raw_quotes = [
            raw
            for raw in raw_quotes
            if _first_non_none_timestamp(json.loads(raw.raw_payload) if raw.raw_payload else {}) is None
            or _first_non_none_timestamp(json.loads(raw.raw_payload) if raw.raw_payload else {}) > latest_quote.quote_date
        ]

    saved = 0
    for raw in raw_quotes:
        quote = _raw_to_quote(raw)
        if quote is None:
            continue
        if latest_quote is not None and quote.quote_date <= latest_quote.quote_date:
            continue
        try:
            repositories.save_quote(db, quote)
            saved += 1
        except Exception as exc:
            logger.error("Failed to save silver quote from %s: %s", raw.id, exc)
    logger.info("Transformed %d/%d records for %s", saved, len(raw_quotes), symbol)
    return saved


def run_transformation_pipeline(db: Session, symbols: List[str]) -> Dict[str, int]:
    """Transform bronze data for a list of symbols."""
    started_at = time.monotonic()
    logger.info("Starting silver transformation for %d symbols", len(symbols))
    results = {sym: transform_symbol(db, sym) for sym in symbols}
    logger.info(
        "Silver transformation complete: symbols=%d records=%d duration=%.2fs",
        len(symbols), sum(results.values()), time.monotonic() - started_at,
    )
    return results
