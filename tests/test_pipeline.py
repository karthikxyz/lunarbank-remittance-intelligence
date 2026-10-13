import csv
import math
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pipeline.aggregate import aggregate_corridors, build_analytics
from pipeline.costs import calculate_transaction_cost, enrich_transactions
from pipeline.ingestion import read_transactions


class CostPipelineTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "transaction_id": "tx-1",
            "timestamp": "2026-09-01T00:00:00+00:00",
            "processor_name": "Processor A",
            "send_currency": "USD",
            "receive_currency": "MXN",
            "send_amount": 100.0,
            "receive_amount": 1911.0,
            "explicit_fee": 2.0,
            "settlement_delay_hours": 24,
            "status": "completed",
        }

    def test_cost_formula(self):
        result = calculate_transaction_cost(self.row, {"USD->MXN": 20.0})
        self.assertAlmostEqual(result["implied_fx_rate"], 19.5)
        self.assertAlmostEqual(result["fx_markup_cost"], 2.45)
        self.assertAlmostEqual(result["capital_cost"], 0.02)
        self.assertAlmostEqual(result["all_in_cost"], 4.47)
        self.assertAlmostEqual(result["effective_take_rate"], 4.47)

    def test_normalizes_status_and_excludes_non_completed(self):
        completed = {**self.row, "status": " Completed "}
        pending = {**self.row, "transaction_id": "tx-2", "status": "Pending"}
        enriched = enrich_transactions([completed, pending], {"USD->MXN": 20.0})
        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0]["status"], "completed")

    def test_rejects_non_finite_values_and_unknown_statuses(self):
        invalid_amount = {**self.row, "send_amount": math.nan}
        with self.assertRaisesRegex(ValueError, "send_amount must be finite"):
            calculate_transaction_cost(invalid_amount, {"USD->MXN": 20.0})

        invalid_status = {**self.row, "status": "reversed"}
        with self.assertRaisesRegex(ValueError, "unknown status"):
            calculate_transaction_cost(invalid_status, {"USD->MXN": 20.0})

    def test_normalizes_native_currency_costs_to_usd(self):
        mxn_row = {
            **self.row,
            "send_currency": "MXN",
            "receive_currency": "COP",
            "send_amount": 1_000.0,
            "explicit_fee": 50.0,
            "receive_amount": 190_000.0,
        }
        result = calculate_transaction_cost(
            mxn_row,
            {"MXN->COP": 210.0},
            {"MXN": 0.05},
        )
        self.assertAlmostEqual(result["send_amount_usd"], 50.0)
        self.assertAlmostEqual(result["all_in_cost_usd"], result["all_in_cost"] * 0.05)

    def test_flags_only_over_30_percent_and_separates_savings(self):
        cheap = calculate_transaction_cost(self.row, {"USD->MXN": 20.0})
        expensive = calculate_transaction_cost(
            {
                **self.row,
                "transaction_id": "tx-2",
                "processor_name": "Processor B",
                "send_amount": 100.0,
                "receive_amount": 1862.0,
            },
            {"USD->MXN": 20.0},
        )
        secondary = calculate_transaction_cost(
            {
                **self.row,
                "transaction_id": "tx-3",
                "processor_name": "Processor C",
                "send_amount": 50.0,
                "receive_amount": 946.68,
            },
            {"USD->MXN": 20.0},
        )
        corridor = aggregate_corridors([cheap, expensive, secondary])[0]
        self.assertEqual(corridor["cheapest_processor"], "Processor A")
        self.assertTrue(corridor["is_inefficient"])
        self.assertEqual(corridor["inefficient_processor"], "Processor B")
        self.assertGreater(
            corridor["optimization_savings"], corridor["routing_savings"]
        )

    def test_threshold_uses_unrounded_volume_share(self):
        cheap_amount = 69.96
        expensive_amount = 30.04
        cheap = calculate_transaction_cost(
            {
                **self.row,
                "send_amount": cheap_amount,
                "explicit_fee": 1.0,
                "receive_amount": (cheap_amount - 1.0) * 19.8,
            },
            {"USD->MXN": 20.0},
        )
        expensive = calculate_transaction_cost(
            {
                **self.row,
                "transaction_id": "tx-2",
                "processor_name": "Processor B",
                "send_amount": expensive_amount,
                "explicit_fee": 1.0,
                "receive_amount": (expensive_amount - 1.0) * 18.0,
            },
            {"USD->MXN": 20.0},
        )
        corridor = aggregate_corridors([cheap, expensive])[0]
        displayed_share = next(
            processor["volume_share"]
            for processor in corridor["processors"]
            if processor["name"] == "Processor B"
        )
        self.assertEqual(displayed_share, 30.0)
        self.assertTrue(corridor["is_inefficient"])

    def test_empty_completed_dataset_has_clear_error(self):
        with self.assertRaisesRegex(ValueError, "No completed transactions"):
            build_analytics([])

    def test_short_history_still_builds_without_fake_comparison(self):
        row = calculate_transaction_cost(self.row, {"USD->MXN": 20.0})
        analytics = build_analytics([row], [self.row])
        self.assertFalse(analytics["summary"]["comparison_available"])
        self.assertEqual(analytics["alerts"], [])

    def test_alerts_on_twenty_percent_week_over_week_increase(self):
        start = datetime(2026, 9, 17, tzinfo=UTC)
        rows = []
        for day in range(14):
            for transaction in range(10):
                take_rate = 2.0 if day < 7 else 3.0
                rows.append(
                    {
                        "transaction_id": f"tx-{day}-{transaction}",
                        "timestamp": (start + timedelta(days=day)).isoformat(),
                        "processor_name": "Processor A",
                        "send_currency": "USD",
                        "receive_currency": "MXN",
                        "corridor": "USD->MXN",
                        "send_amount": 100.0,
                        "receive_amount": 1900.0,
                        "explicit_fee": 1.0,
                        "settlement_delay_hours": 12.0,
                        "status": "completed",
                        "fx_markup_cost": take_rate - 1.0,
                        "capital_cost": 0.0,
                        "all_in_cost": take_rate,
                    }
                )
        analytics = build_analytics(rows, rows)
        self.assertEqual(len(analytics["daily_trend"]), 14)
        self.assertEqual(len(analytics["alerts"]), 1)
        self.assertAlmostEqual(analytics["alerts"][0]["increase_pct"], 50.0)

    def test_aggregates_ten_thousand_transactions(self):
        enriched = []
        for index in range(10_000):
            result = calculate_transaction_cost(
                {**self.row, "transaction_id": f"tx-{index}"},
                {"USD->MXN": 20.0},
            )
            enriched.append(result)
        corridors = aggregate_corridors(enriched)
        self.assertEqual(corridors[0]["transactions"], 10_000)


class IngestionTests(unittest.TestCase):
    fieldnames = [
        "transaction_id",
        "timestamp",
        "processor_name",
        "send_currency",
        "receive_currency",
        "send_amount",
        "receive_amount",
        "explicit_fee",
        "settlement_delay_hours",
        "status",
    ]

    def _write_csv(self, path: Path, rows: list[dict]) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_validates_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("transaction_id,status\n1,completed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required columns"):
                read_transactions(path)

    def test_rejects_duplicate_ids_and_bad_timestamps(self):
        base = {
            "transaction_id": "tx-1",
            "timestamp": "2026-09-01T00:00:00+00:00",
            "processor_name": "Processor A",
            "send_currency": "USD",
            "receive_currency": "MXN",
            "send_amount": "100",
            "receive_amount": "1900",
            "explicit_fee": "2",
            "settlement_delay_hours": "12",
            "status": "completed",
        }
        with tempfile.TemporaryDirectory() as directory:
            duplicate_path = Path(directory) / "duplicate.csv"
            self._write_csv(duplicate_path, [base, base])
            with self.assertRaisesRegex(ValueError, "duplicate transaction_id"):
                read_transactions(duplicate_path)

            timestamp_path = Path(directory) / "timestamp.csv"
            self._write_csv(
                timestamp_path,
                [{**base, "timestamp": "not-a-date"}],
            )
            with self.assertRaisesRegex(ValueError, "timestamp must be ISO-8601"):
                read_transactions(timestamp_path)


if __name__ == "__main__":
    unittest.main()
