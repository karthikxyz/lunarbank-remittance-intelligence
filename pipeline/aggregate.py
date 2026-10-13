"""Corridor- and processor-level cost intelligence."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Any, Iterable


def _round(value: float, digits: int = 2) -> float:
    return round(value, digits)


def aggregate_corridors(transactions: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for transaction in transactions:
        groups[transaction["corridor"]].append(transaction)

    corridors = []
    for corridor, rows in groups.items():
        total_tpv = sum(row["send_amount"] for row in rows)
        processor_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            processor_groups[row["processor_name"]].append(row)
        processors = []
        for name, items in processor_groups.items():
            tpv = sum(item["send_amount"] for item in items)
            all_in = sum(item["all_in_cost"] for item in items)
            processors.append({
                "name": name,
                "transactions": len(items),
                "tpv": _round(tpv),
                "volume_share": _round(tpv / total_tpv * 100, 1),
                "avg_cost": _round(all_in / len(items)),
                "avg_take_rate": _round(all_in / tpv * 100, 3),
                "explicit_fees": _round(sum(item["explicit_fee"] for item in items)),
                "fx_markup": _round(sum(item["fx_markup_cost"] for item in items)),
                "capital_cost": _round(sum(item["capital_cost"] for item in items)),
                "avg_delay": _round(sum(item["settlement_delay_hours"] for item in items) / len(items), 1),
            })
        processors.sort(key=lambda processor: processor["avg_take_rate"])
        cheapest = processors[0]
        inefficient = [
            processor for processor in processors
            if processor["name"] != cheapest["name"] and processor["volume_share"] > 30
        ]
        savings = sum(
            max(0, row["all_in_cost"] - row["send_amount"] * cheapest["avg_take_rate"] / 100)
            for row in rows
        )
        all_in = sum(row["all_in_cost"] for row in rows)
        corridors.append({
            "corridor": corridor,
            "tpv": _round(total_tpv),
            "transactions": len(rows),
            "avg_cost": _round(all_in / len(rows)),
            "avg_take_rate": _round(all_in / total_tpv * 100, 3),
            "cheapest_processor": cheapest["name"],
            "potential_savings": _round(savings),
            "inefficient_processor": inefficient[0]["name"] if inefficient else None,
            "is_inefficient": bool(inefficient),
            "processors": processors,
        })
    return sorted(corridors, key=lambda item: item["avg_take_rate"], reverse=True)


def build_analytics(transactions: list[dict[str, Any]]) -> dict[str, Any]:
    corridors = aggregate_corridors(transactions)
    total_tpv = sum(row["send_amount"] for row in transactions)
    total_cost = sum(row["all_in_cost"] for row in transactions)
    recommendations = [
        {
            "corridor": corridor["corridor"],
            "from": corridor["inefficient_processor"],
            "to": corridor["cheapest_processor"],
            "monthly_savings": corridor["potential_savings"],
            "current_take_rate": corridor["avg_take_rate"],
            "target_take_rate": corridor["processors"][0]["avg_take_rate"],
        }
        for corridor in corridors if corridor["is_inefficient"]
    ]
    recommendations.sort(key=lambda item: item["monthly_savings"], reverse=True)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "period": "30 days",
        "summary": {
            "tpv": _round(total_tpv),
            "transactions": len(transactions),
            "avg_take_rate": _round(total_cost / total_tpv * 100, 3),
            "total_cost": _round(total_cost),
            "potential_savings": _round(sum(item["potential_savings"] for item in corridors)),
            "inefficient_corridors": len(recommendations),
        },
        "corridors": corridors,
        "recommendations": recommendations,
    }
