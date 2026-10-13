"""Transaction-level cost calculations for completed remittances."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

CAPITAL_COST_PER_DAY = 0.0002  # 0.02% of send amount per day


def calculate_transaction_cost(
    transaction: Mapping[str, Any], market_rates: Mapping[str, float]
) -> dict[str, Any] | None:
    """Return an enriched transaction, or None when it is not completed.

    FX markup is normalized to the sending currency by applying the rate
    shortfall percentage to the amount available for conversion.
    """
    if transaction["status"] != "completed":
        return None
    corridor = f"{transaction['send_currency']}->{transaction['receive_currency']}"
    if corridor not in market_rates:
        raise ValueError(f"Missing market rate for {corridor}")

    try:
        send_amount = float(transaction["send_amount"])
        explicit_fee = float(transaction["explicit_fee"])
        receive_amount = float(transaction["receive_amount"])
        settlement_hours = float(transaction["settlement_delay_hours"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid numeric value in transaction {transaction['transaction_id']}") from exc
    if send_amount <= explicit_fee or receive_amount <= 0 or settlement_hours < 0:
        raise ValueError(f"Invalid amount or delay in transaction {transaction['transaction_id']}")

    market_rate = float(market_rates[corridor])
    convertible_amount = send_amount - explicit_fee
    implied_fx_rate = receive_amount / convertible_amount
    fx_markup_rate = max(0.0, (market_rate - implied_fx_rate) / market_rate)
    fx_markup_cost = convertible_amount * fx_markup_rate
    capital_cost = send_amount * CAPITAL_COST_PER_DAY * settlement_hours / 24
    all_in_cost = explicit_fee + fx_markup_cost + capital_cost

    return {
        **transaction,
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
    }


def enrich_transactions(
    transactions: Iterable[Mapping[str, Any]], market_rates: Mapping[str, float]
) -> list[dict[str, Any]]:
    """Enrich completed rows in one pass; suitable for 10k+ records."""
    enriched = []
    for transaction in transactions:
        result = calculate_transaction_cost(transaction, market_rates)
        if result is not None:
            enriched.append(result)
    return enriched
