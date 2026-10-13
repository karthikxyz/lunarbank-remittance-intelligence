"""Corridor intelligence, recommendations, trends, and processor alerts."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Any, Iterable, Mapping

INEFFICIENT_VOLUME_THRESHOLD = 30.0
ALERT_INCREASE_THRESHOLD = 20.0
ALERT_WINDOW_DAYS = 7
MIN_ALERT_TRANSACTIONS = 10


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def _timestamp(transaction: Mapping[str, Any]) -> datetime:
    return datetime.fromisoformat(str(transaction["timestamp"]).replace("Z", "+00:00"))


def _usd(transaction: Mapping[str, Any], field: str) -> float:
    """Read a normalized value, with a USD-only fallback for focused unit tests."""
    normalized_field = f"{field}_usd"
    if normalized_field in transaction:
        return float(transaction[normalized_field])
    return float(transaction[field])


def _take_rate(rows: Iterable[Mapping[str, Any]]) -> float:
    records = list(rows)
    tpv = sum(_usd(row, "send_amount") for row in records)
    if tpv <= 0:
        raise ValueError("Cannot calculate a take rate for zero TPV")
    return sum(_usd(row, "all_in_cost") for row in records) / tpv * 100


def aggregate_corridors(transactions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate completed transactions and identify misrouted corridor volume."""
    records = list(transactions)
    if not records:
        raise ValueError("No completed transactions are available for aggregation")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for transaction in records:
        groups[transaction["corridor"]].append(transaction)

    corridors: list[dict[str, Any]] = []
    for corridor, rows in groups.items():
        total_tpv = sum(_usd(row, "send_amount") for row in rows)
        processor_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            processor_groups[row["processor_name"]].append(row)

        raw_take_rates = {
            name: _take_rate(items) for name, items in processor_groups.items()
        }
        raw_volume_shares: dict[str, float] = {}
        processors = []
        for name, items in processor_groups.items():
            tpv = sum(_usd(item, "send_amount") for item in items)
            all_in = sum(_usd(item, "all_in_cost") for item in items)
            raw_volume_shares[name] = tpv / total_tpv * 100
            processors.append(
                {
                    "name": name,
                    "transactions": len(items),
                    "tpv": _round(tpv),
                    "volume_share": _round(raw_volume_shares[name], 1),
                    "avg_cost": _round(all_in / len(items)),
                    "avg_take_rate": _round(raw_take_rates[name], 3),
                    "explicit_fees": _round(
                        sum(_usd(item, "explicit_fee") for item in items)
                    ),
                    "fx_markup": _round(
                        sum(_usd(item, "fx_markup_cost") for item in items)
                    ),
                    "capital_cost": _round(
                        sum(_usd(item, "capital_cost") for item in items)
                    ),
                    "avg_delay": _round(
                        sum(item["settlement_delay_hours"] for item in items)
                        / len(items),
                        1,
                    ),
                }
            )

        processors.sort(key=lambda processor: raw_take_rates[processor["name"]])
        cheapest = processors[0]
        cheapest_rate = raw_take_rates[cheapest["name"]]
        inefficient = [
            processor
            for processor in processors
            if processor["name"] != cheapest["name"]
            and raw_volume_shares[processor["name"]]
            > INEFFICIENT_VOLUME_THRESHOLD
        ]
        primary_inefficient = max(
            inefficient,
            key=lambda processor: raw_volume_shares[processor["name"]],
            default=None,
        )

        def saving(row: Mapping[str, Any]) -> float:
            target_cost = _usd(row, "send_amount") * cheapest_rate / 100
            return max(0.0, _usd(row, "all_in_cost") - target_cost)

        optimization_savings = sum(saving(row) for row in rows)
        routing_savings = (
            sum(
                saving(row)
                for row in rows
                if row["processor_name"] == primary_inefficient["name"]
            )
            if primary_inefficient
            else 0.0
        )
        all_in = sum(_usd(row, "all_in_cost") for row in rows)
        corridors.append(
            {
                "corridor": corridor,
                "tpv": _round(total_tpv),
                "transactions": len(rows),
                "avg_cost": _round(all_in / len(rows)),
                "avg_take_rate": _round(all_in / total_tpv * 100, 3),
                "cheapest_processor": cheapest["name"],
                "optimization_savings": _round(optimization_savings),
                "routing_savings": _round(routing_savings),
                "inefficient_processor": (
                    primary_inefficient["name"] if primary_inefficient else None
                ),
                "inefficient_processors": [
                    processor["name"] for processor in inefficient
                ],
                "is_inefficient": bool(inefficient),
                "processors": processors,
            }
        )
    return sorted(corridors, key=lambda item: item["avg_take_rate"], reverse=True)


def _daily_trend(transactions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[date, list[dict[str, Any]]] = defaultdict(list)
    for transaction in transactions:
        groups[_timestamp(transaction).date()].append(transaction)

    trend = []
    for day, rows in sorted(groups.items()):
        total_tpv = sum(_usd(row, "send_amount") for row in rows)
        total_cost = sum(_usd(row, "all_in_cost") for row in rows)
        trend.append(
            {
                "date": day.isoformat(),
                "tpv": _round(total_tpv),
                "transactions": len(rows),
                "total_cost": _round(total_cost),
                "take_rate": _round(total_cost / total_tpv * 100, 3),
            }
        )
    return trend


def _window_comparison(
    transactions: list[dict[str, Any]], period_end: date
) -> dict[str, float | bool]:
    recent_start = period_end - timedelta(days=ALERT_WINDOW_DAYS - 1)
    prior_start = recent_start - timedelta(days=ALERT_WINDOW_DAYS)
    prior_end = recent_start - timedelta(days=1)
    recent = [
        row
        for row in transactions
        if recent_start <= _timestamp(row).date() <= period_end
    ]
    prior = [
        row
        for row in transactions
        if prior_start <= _timestamp(row).date() <= prior_end
    ]
    if not recent or not prior:
        return {
            "comparison_available": False,
            "tpv_change_pct": 0.0,
            "take_rate_change_bps": 0.0,
        }
    recent_tpv = sum(_usd(row, "send_amount") for row in recent)
    prior_tpv = sum(_usd(row, "send_amount") for row in prior)
    recent_rate = _take_rate(recent)
    prior_rate = _take_rate(prior)
    return {
        "comparison_available": True,
        "tpv_change_pct": _round((recent_tpv / prior_tpv - 1) * 100, 1),
        "take_rate_change_bps": _round((recent_rate - prior_rate) * 100, 1),
    }


def _processor_alerts(
    transactions: list[dict[str, Any]], period_end: date
) -> tuple[list[dict[str, Any]], int]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for transaction in transactions:
        groups[(transaction["corridor"], transaction["processor_name"])].append(
            transaction
        )

    recent_start = period_end - timedelta(days=ALERT_WINDOW_DAYS - 1)
    prior_start = recent_start - timedelta(days=ALERT_WINDOW_DAYS)
    prior_end = recent_start - timedelta(days=1)
    alerts = []
    monitored = 0
    for (corridor, processor), rows in groups.items():
        recent = [
            row
            for row in rows
            if recent_start <= _timestamp(row).date() <= period_end
        ]
        prior = [
            row
            for row in rows
            if prior_start <= _timestamp(row).date() <= prior_end
        ]
        if len(recent) < MIN_ALERT_TRANSACTIONS or len(prior) < MIN_ALERT_TRANSACTIONS:
            continue
        monitored += 1
        recent_rate = _take_rate(recent)
        prior_rate = _take_rate(prior)
        increase_pct = (recent_rate / prior_rate - 1) * 100
        if increase_pct > ALERT_INCREASE_THRESHOLD:
            alerts.append(
                {
                    "corridor": corridor,
                    "processor": processor,
                    "previous_take_rate": _round(prior_rate, 3),
                    "current_take_rate": _round(recent_rate, 3),
                    "increase_pct": _round(increase_pct, 1),
                    "recent_transactions": len(recent),
                }
            )
    alerts.sort(key=lambda alert: alert["increase_pct"], reverse=True)
    return alerts, monitored


def build_analytics(
    transactions: list[dict[str, Any]],
    source_transactions: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the compact analytics contract consumed by the dashboard."""
    if not transactions:
        raise ValueError("No completed transactions are available for analytics")

    corridors = aggregate_corridors(transactions)
    total_tpv = sum(_usd(row, "send_amount") for row in transactions)
    total_cost = sum(_usd(row, "all_in_cost") for row in transactions)
    timestamps = [_timestamp(row) for row in transactions]
    period_start = min(timestamps).date()
    period_end = max(timestamps).date()
    comparison = _window_comparison(transactions, period_end)
    alerts, monitored_routes = _processor_alerts(transactions, period_end)

    source = source_transactions or transactions
    status_counts = {"completed": 0, "failed": 0, "pending": 0}
    for row in source:
        status = str(row.get("status", "")).strip().lower()
        if status in status_counts:
            status_counts[status] += 1
    input_transactions = len(source)

    recommendations = [
        {
            "corridor": corridor["corridor"],
            "from": corridor["inefficient_processor"],
            "to": corridor["cheapest_processor"],
            "monthly_savings": corridor["routing_savings"],
            "current_take_rate": next(
                processor["avg_take_rate"]
                for processor in corridor["processors"]
                if processor["name"] == corridor["inefficient_processor"]
            ),
            "target_take_rate": corridor["processors"][0]["avg_take_rate"],
        }
        for corridor in corridors
        if corridor["is_inefficient"]
    ]
    recommendations.sort(key=lambda item: item["monthly_savings"], reverse=True)

    return {
        "generated_at": max(timestamps).isoformat(),
        "period": {
            "label": f"{(period_end - period_start).days + 1} days",
            "start": period_start.isoformat(),
            "end": period_end.isoformat(),
        },
        "summary": {
            "tpv": _round(total_tpv),
            "input_transactions": input_transactions,
            "transactions": len(transactions),
            "status_counts": status_counts,
            "completion_rate": _round(len(transactions) / input_transactions * 100, 1),
            "avg_take_rate": _round(total_cost / total_tpv * 100, 3),
            "total_cost": _round(total_cost),
            "optimization_savings": _round(
                sum(item["optimization_savings"] for item in corridors)
            ),
            "actionable_savings": _round(
                sum(item["routing_savings"] for item in corridors)
            ),
            "inefficient_corridors": len(recommendations),
            **comparison,
        },
        "daily_trend": _daily_trend(transactions),
        "alerts": alerts,
        "alerting": {
            "threshold_pct": ALERT_INCREASE_THRESHOLD,
            "window_days": ALERT_WINDOW_DAYS,
            "monitored_processor_routes": monitored_routes,
        },
        "corridors": corridors,
        "recommendations": recommendations,
    }
