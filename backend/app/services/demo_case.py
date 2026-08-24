from __future__ import annotations

from datetime import datetime, timezone

DEMO_CASE = {
    "case_id": "CASE-DEMO-001",
    "complaint_ref": "CYBER-001-demo",
    "status": "open",
    "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc).isoformat(),
    "wallets": [
        {
            "wallet_address": "0x1111111111111111111111111111111111111111",
            "chain": "ethereum",
            "label": "synthetic-demo-wallet",
        }
    ],
    "note": "This is a synthetic demo case for application testing only. It is not real-world evidence.",
}
