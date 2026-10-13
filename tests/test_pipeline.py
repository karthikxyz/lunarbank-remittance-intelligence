import csv
import tempfile
import unittest
from pathlib import Path

from pipeline.aggregate import aggregate_corridors
from pipeline.costs import calculate_transaction_cost, enrich_transactions
from pipeline.ingestion import read_transactions


class CostPipelineTests(unittest.TestCase):
    def setUp(self):
        self.row = {
            "transaction_id": "tx-1", "timestamp": "2026-09-01T00:00:00Z",
            "processor_name": "Processor A", "send_currency": "USD", "receive_currency": "MXN",
            "send_amount": 100.0, "receive_amount": 1911.0, "explicit_fee": 2.0,
            "settlement_delay_hours": 24, "status": "completed",
        }

    def test_cost_formula(self):
        result = calculate_transaction_cost(self.row, {"USD->MXN": 20.0})
        self.assertAlmostEqual(result["implied_fx_rate"], 19.5)
        self.assertAlmostEqual(result["fx_markup_cost"], 2.45)
        self.assertAlmostEqual(result["capital_cost"], 0.02)
        self.assertAlmostEqual(result["all_in_cost"], 4.47)
        self.assertAlmostEqual(result["effective_take_rate"], 4.47)

    def test_excludes_non_completed(self):
        pending = {**self.row, "status": "pending"}
        self.assertEqual(enrich_transactions([self.row, pending], {"USD->MXN": 20.0}), [calculate_transaction_cost(self.row, {"USD->MXN": 20.0})])

    def test_flags_over_30_percent_on_non_cheapest(self):
        cheap = calculate_transaction_cost(self.row, {"USD->MXN": 20.0})
        expensive_row = {**self.row, "transaction_id": "tx-2", "processor_name": "Processor B", "receive_amount": 1862.0}
        expensive = calculate_transaction_cost(expensive_row, {"USD->MXN": 20.0})
        corridor = aggregate_corridors([cheap, expensive])[0]
        self.assertEqual(corridor["cheapest_processor"], "Processor A")
        self.assertTrue(corridor["is_inefficient"])
        self.assertEqual(corridor["inefficient_processor"], "Processor B")

    def test_ingestion_validates_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("transaction_id,status\n1,completed\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Missing required columns"):
                read_transactions(path)


if __name__ == "__main__":
    unittest.main()
