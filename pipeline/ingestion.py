"""CSV ingestion and output helpers, intentionally separate from calculations."""

from __future__ import annotations

import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

REQUIRED_COLUMNS = {
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
}
VALID_STATUSES = {"completed", "failed", "pending"}
NUMERIC_COLUMNS = {
    "send_amount",
    "receive_amount",
    "explicit_fee",
    "settlement_delay_hours",
}


def _validate_row(row: dict[str, Any], row_number: int, seen_ids: set[str]) -> None:
    """Validate fields needed by calculations and time-series aggregation."""
    for column in REQUIRED_COLUMNS:
        value = row.get(column)
        if value is None or str(value).strip() == "":
            raise ValueError(f"Row {row_number}: {column} cannot be empty")

    transaction_id = str(row["transaction_id"]).strip()
    if transaction_id in seen_ids:
        raise ValueError(f"Row {row_number}: duplicate transaction_id {transaction_id}")
    seen_ids.add(transaction_id)

    try:
        datetime.fromisoformat(str(row["timestamp"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: timestamp must be ISO-8601") from exc

    status = str(row["status"]).strip().lower()
    if status not in VALID_STATUSES:
        allowed = ", ".join(sorted(VALID_STATUSES))
        raise ValueError(f"Row {row_number}: status must be one of {allowed}")

    numeric_values: dict[str, float] = {}
    for column in NUMERIC_COLUMNS:
        try:
            numeric_values[column] = float(row[column])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Row {row_number}: {column} must be numeric") from exc
        if not math.isfinite(numeric_values[column]):
            raise ValueError(f"Row {row_number}: {column} must be finite")
    if numeric_values["send_amount"] <= 0 or numeric_values["explicit_fee"] < 0:
        raise ValueError(
            f"Row {row_number}: amount must be positive and fee non-negative"
        )
    if numeric_values["settlement_delay_hours"] < 0:
        raise ValueError(f"Row {row_number}: settlement delay cannot be negative")
    if status == "completed" and numeric_values["receive_amount"] <= 0:
        raise ValueError(
            f"Row {row_number}: completed transfer must have a receive amount"
        )

    for column in REQUIRED_COLUMNS:
        if isinstance(row[column], str):
            row[column] = row[column].strip()
    row["status"] = status


def read_transactions(path: str | Path) -> list[dict[str, Any]]:
    """Read and validate transaction records from a CSV file."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
        rows = list(reader)

    if not rows:
        raise ValueError("Input CSV contains no transaction rows")

    seen_ids: set[str] = set()
    for row_number, row in enumerate(rows, start=2):
        _validate_row(row, row_number, seen_ids)
    return rows


def write_csv(path: str | Path, rows: Iterable[dict[str, Any]]) -> None:
    records = list(rows)
    if not records:
        return
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=records[0].keys(),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(records)


def write_json(path: str | Path, payload: Any, *, compact: bool = False) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(
            payload,
            indent=None if compact else 2,
            separators=(",", ":") if compact else None,
        ),
        encoding="utf-8",
    )
