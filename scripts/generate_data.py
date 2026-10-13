"""Generate a reproducible 30-day remittance dataset and dashboard outputs."""

from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipeline import build_analytics, enrich_transactions, write_csv, write_json

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKET_RATES = json.loads(
    (PROJECT_ROOT / "config/market_rates.json").read_text(encoding="utf-8")
)
USD_RATES = json.loads(
    (PROJECT_ROOT / "config/usd_rates.json").read_text(encoding="utf-8")
)
PROCESSORS = ["AndesPay", "NovaRemit", "PampaLink", "SelvaMoney", "PacificWire"]
CORRIDOR_WEIGHTS = {
    "USD->MXN": 18,
    "MXN->COP": 14,
    "BRL->ARS": 13,
    "COP->PEN": 12,
    "CLP->PEN": 11,
    "PEN->MXN": 10,
    "ARS->CLP": 12,
    "BRL->COP": 10,
}
MARKUPS = {
    "USD->MXN": [.011, .019, .026, .016, .023],
    "MXN->COP": [.027, .013, .021, .024, .018],
    "BRL->ARS": [.024, .028, .012, .018, .021],
    "COP->PEN": [.022, .017, .026, .012, .019],
    "CLP->PEN": [.019, .023, .018, .021, .011],
    "PEN->MXN": [.014, .021, .025, .018, .023],
    "ARS->CLP": [.024, .016, .022, .027, .013],
    "BRL->COP": [.025, .014, .021, .018, .023],
}
ROUTING = {
    "USD->MXN": [18, 44, 12, 16, 10],
    "MXN->COP": [42, 20, 14, 12, 12],
    "BRL->ARS": [12, 38, 18, 18, 14],
    "COP->PEN": [13, 16, 12, 45, 14],
    "CLP->PEN": [19, 18, 16, 15, 32],
    "PEN->MXN": [34, 18, 18, 16, 14],
    "ARS->CLP": [15, 22, 15, 14, 34],
    "BRL->COP": [38, 18, 14, 16, 14],
}


def _time_adjusted_markup(
    base_markup: float,
    corridor: str,
    processor: str,
    timestamp: datetime,
) -> float:
    """Seed one balanced week-over-week spike so alerting can be demonstrated."""
    if corridor != "BRL->COP" or processor != "PacificWire":
        return base_markup
    if timestamp.date() >= datetime(2026, 9, 24, tzinfo=UTC).date():
        return base_markup * 1.20
    if timestamp.date() >= datetime(2026, 9, 17, tzinfo=UTC).date():
        return base_markup * 0.80
    return base_markup


def generate_transactions(count: int = 6400, seed: int = 90210) -> list[dict]:
    """Create realistic, deterministic processor and corridor transaction records."""
    rng = random.Random(seed)
    corridors = list(CORRIDOR_WEIGHTS)
    rows = []
    for index in range(count):
        corridor = rng.choices(
            corridors,
            weights=CORRIDOR_WEIGHTS.values(),
            k=1,
        )[0]
        send_currency, receive_currency = corridor.split("->")
        processor = rng.choices(
            PROCESSORS,
            weights=ROUTING[corridor],
            k=1,
        )[0]
        processor_index = PROCESSORS.index(processor)
        amount_usd = round(50 + rng.random() ** 1.65 * 4950, 2)
        amount = round(amount_usd / USD_RATES[send_currency], 2)
        fee_usd = round(
            2
            + processor_index * .55
            + (1.6 if amount_usd > 1500 else 0)
            + rng.random() * 1.8,
            2,
        )
        fee = round(fee_usd / USD_RATES[send_currency], 2)
        delay = round(
            2
            + processor_index * 5
            + rng.random() * 42
            + (10 if corridor == "BRL->ARS" else 0),
            1,
        )
        status_roll = rng.random()
        status = (
            "completed"
            if status_roll < .94
            else "failed"
            if status_roll < .975
            else "pending"
        )
        timestamp = datetime(2026, 9, 1, tzinfo=UTC) + timedelta(
            days=rng.randrange(30),
            hours=rng.randrange(24),
            minutes=rng.randrange(60),
        )
        base_markup = MARKUPS[corridor][processor_index] * (.88 + rng.random() * .24)
        markup = _time_adjusted_markup(
            base_markup,
            corridor,
            processor,
            timestamp,
        )
        receive_amount = round(
            (amount - fee) * MARKET_RATES[corridor] * (1 - markup),
            4,
        )
        rows.append(
            {
                "transaction_id": f"LBR-{index + 1:06d}",
                "timestamp": timestamp.isoformat(),
                "processor_name": processor,
                "send_currency": send_currency,
                "receive_currency": receive_currency,
                "send_amount": amount,
                "receive_amount": receive_amount,
                "explicit_fee": fee,
                "settlement_delay_hours": delay,
                "status": status,
            }
        )
    return rows


def main() -> None:
    rows = generate_transactions()
    enriched = enrich_transactions(rows, MARKET_RATES, USD_RATES)
    analytics = build_analytics(enriched, rows)
    write_csv(PROJECT_ROOT / "data/raw_transactions.csv", rows)
    write_csv(PROJECT_ROOT / "data/enriched_transactions.csv", enriched)
    write_json(PROJECT_ROOT / "data/corridor_analytics.json", analytics)
    write_json(PROJECT_ROOT / "public/analytics.json", analytics, compact=True)
    print(
        f"Generated {len(rows)} raw rows, {len(enriched)} completed rows, "
        f"{len(analytics['recommendations'])} recommendations, and "
        f"{len(analytics['alerts'])} rate alert(s)."
    )


if __name__ == "__main__":
    main()
