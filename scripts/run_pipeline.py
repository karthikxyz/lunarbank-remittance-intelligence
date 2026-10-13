"""Run the cost-intelligence pipeline against any compatible transaction CSV."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline import build_analytics, enrich_transactions, read_transactions, write_csv, write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich and aggregate LunarBank remittance transactions")
    parser.add_argument("--input", default="data/raw_transactions.csv", help="Raw transaction CSV")
    parser.add_argument("--rates", default="config/market_rates.json", help="JSON market-rate table")
    parser.add_argument("--output-dir", default="data/output", help="Directory for enriched and aggregate outputs")
    args = parser.parse_args()

    rates = json.loads(Path(args.rates).read_text(encoding="utf-8"))
    rows = read_transactions(args.input)
    enriched = enrich_transactions(rows, rates)
    analytics = build_analytics(enriched)
    output = Path(args.output_dir)
    write_csv(output / "enriched_transactions.csv", enriched)
    write_json(output / "corridor_analytics.json", analytics)
    print(f"Processed {len(rows)} rows; enriched {len(enriched)} completed transfers across {len(analytics['corridors'])} corridors.")


if __name__ == "__main__":
    main()
