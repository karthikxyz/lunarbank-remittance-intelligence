"""Transaction-level cost calculations for completed remittances."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

CAPITAL_COST_PER_DAY = 0.0002  # 0.02% of send amount per day
VALID_STATUSES = {"completed", "failed", "pending"}
REQUIRED_FIELDS = {
    "transaction_id",
    "processor_name",
    "send_currency",
    "receive_currency",
    "send_amount",
    "receive_amount",
    "explicit_fee",
    "settlement_delay_hours",
    "status",
}


def _finite_number(value: Any, field: str, transaction_id: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Transaction {transaction_id}: {field} must be numeric"
        ) from exc
    if not math.isfinite(number):
        raise ValueError(f"Transaction {transaction_id}: {field} must be finite")
    return number


def calculate_transaction_cost(
    transaction: Mapping[str, Any],
    market_rates: Mapping[str, float],
    usd_rates: Mapping[str, float] | None = None,
) -> dict[str, Any] | None:
    """Return an enriched transaction, or None when it is not completed.

    FX markup is normalized to the sending currency by applying the rate
    shortfall percentage to the amount available for conversion.
    """
    missing = REQUIRED_FIELDS.difference(transaction)
    transaction_id = str(transaction.get("transaction_id", "<unknown>"))
    if missing:
        raise ValueError(
            f"Transaction {transaction_id}: missing fields {', '.join(sorted(missing))}"
        )

    status = str(transaction["status"]).strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"Transaction {transaction_id}: unknown status {status!r}")
    if status != "completed":
        return None

    send_currency = str(transaction["send_currency"]).strip().upper()
    receive_currency = str(transaction["receive_currency"]).strip().upper()
    corridor = f"{send_currency}->{receive_currency}"
    if corridor not in market_rates:
        raise ValueError(f"Missing market rate for {corridor}")

    send_amount = _finite_number(
        transaction["send_amount"], "send_amount", transaction_id
    )
    explicit_fee = _finite_number(
        transaction["explicit_fee"], "explicit_fee", transaction_id
    )
    receive_amount = _finite_number(
        transaction["receive_amount"], "receive_amount", transaction_id
    )
    settlement_hours = _finite_number(
        transaction["settlement_delay_hours"],
        "settlement_delay_hours",
        transaction_id,
    )
    if send_amount <= 0 or explicit_fee < 0 or send_amount <= explicit_fee:
        raise ValueError(
            f"Transaction {transaction_id}: send_amount must exceed a non-negative fee"
        )
    if receive_amount <= 0 or settlement_hours < 0:
        raise ValueError(
            f"Transaction {transaction_id}: receive_amount must be positive "
            "and delay non-negative"
        )

    market_rate = _finite_number(market_rates[corridor], "market_rate", transaction_id)
    if market_rate <= 0:
        raise ValueError(f"Transaction {transaction_id}: market_rate must be positive")
    if usd_rates is None and send_currency != "USD":
        raise ValueError(f"Missing USD conversion rate for {send_currency}")
    usd_rate = _finite_number(
        1.0 if usd_rates is None else usd_rates.get(send_currency),
        "usd_rate",
        transaction_id,
    )
    if usd_rate <= 0:
        raise ValueError(f"Transaction {transaction_id}: usd_rate must be positive")

    convertible_amount = send_amount - explicit_fee
    implied_fx_rate = receive_amount / convertible_amount
    fx_markup_rate = max(0.0, (market_rate - implied_fx_rate) / market_rate)
    fx_markup_cost = convertible_amount * fx_markup_rate
    capital_cost = send_amount * CAPITAL_COST_PER_DAY * settlement_hours / 24
    all_in_cost = explicit_fee + fx_markup_cost + capital_cost

    return {
        **transaction,
        "status": status,
        "send_currency": send_currency,
        "receive_currency": receive_currency,
        "send_amount": send_amount,
        "receive_amount": receive_amount,
        "explicit_fee": explicit_fee,
        "settlement_delay_hours": settlement_hours,
        "corridor": corridor,
        "market_rate": market_rate,
        "implied_fx_rate": implied_fx_rate,
        "fx_markup_rate": fx_markup_rate,
        "fx_markup_cost": fx_markup_cost,
        "capital_cost": capital_cost,
        "all_in_cost": all_in_cost,
        "effective_take_rate": all_in_cost / send_amount * 100,
        "usd_rate": usd_rate,
        "send_amount_usd": send_amount * usd_rate,
        "explicit_fee_usd": explicit_fee * usd_rate,
        "fx_markup_cost_usd": fx_markup_cost * usd_rate,
        "capital_cost_usd": capital_cost * usd_rate,
        "all_in_cost_usd": all_in_cost * usd_rate,
    }


def enrich_transactions(
    transactions: Iterable[Mapping[str, Any]],
    market_rates: Mapping[str, float],
    usd_rates: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Enrich completed rows in one pass; suitable for 10k+ records."""
    enriched = []
    for transaction in transactions:
        result = calculate_transaction_cost(transaction, market_rates, usd_rates)
        if result is not None:
            enriched.append(result)
    return enriched
