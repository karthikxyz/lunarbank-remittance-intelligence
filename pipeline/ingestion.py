"""CSV ingestion and output helpers, intentionally separate from calculations."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

REQUIRED_COLUMNS = {
    "transaction_id", "timestamp", "processor_name", "send_currency",
    "receive_currency", "send_amount", "receive_amount", "explicit_fee",
    "settlement_delay_hours", "status",
}


def read_transactions(path: str | Path) -> list[dict[str, Any]]:
    """Read and validate transaction records from a CSV file."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
        return list(reader)


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    records = list(rows)
    if not records:
        return
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(records)


def write_json(path: str | Path, payload: Any, *, compact: bool = False) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=None if compact else 2, separators=(",", ":") if compact else None),
        encoding="utf-8",
    )
