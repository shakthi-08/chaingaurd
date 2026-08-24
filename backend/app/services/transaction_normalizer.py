from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def normalize_timestamp(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_transaction_record(record: dict[str, Any]) -> dict[str, Any]:
    tx = {
        "tx_hash": str(record["tx_hash"]).strip(),
        "chain": str(record.get("chain") or "ethereum").strip().lower(),
        "from_address": str(record["from"]).strip(),
        "to_address": str(record["to"]).strip(),
        "value": str(record.get("value", "0")),
        "token": str(record.get("token") or "native").strip() or "native",
        "timestamp": normalize_timestamp(record["timestamp"]),
        "block": int(record.get("block", 0) or 0),
    }
    if record.get("source"):
        tx["source"] = str(record["source"])
    if record.get("synthetic") is not None:
        tx["synthetic"] = bool(record["synthetic"])
    return tx
