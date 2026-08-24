"""Synthetic entity data for demonstrations only; these are not real findings."""

DEMO_ENTITY_DATASET = [
    {
        "entity_id": "DEMO-VASP-001",
        "name": "Demo Exchange Alpha",
        "type": "vasp",
        "known_wallet": "0x1111111111111111111111111111111111111111",
        "chain": "ethereum",
        "source": "SYNTHETIC_DEMO",
        "source_reliability": 0.90,
        "confidence_metadata": {"match_strength": 1.0, "label": "DEMO/SAMPLE"},
    },
    {
        "entity_id": "DEMO-VASP-002",
        "name": "Demo Exchange Beta",
        "type": "vasp",
        "known_wallet": "0x2222222222222222222222222222222222222222",
        "chain": "ethereum",
        "source": "SYNTHETIC_DEMO",
        "source_reliability": 0.90,
        "confidence_metadata": {"match_strength": 1.0, "label": "DEMO/SAMPLE"},
    },
    {
        "entity_id": "DEMO-VASP-003",
        "name": "Demo Liquidity Venue",
        "type": "vasp",
        "known_wallet": "0x2222222222222222222222222222222222222222",
        "chain": "ethereum",
        "source": "SYNTHETIC_DEMO",
        "source_reliability": 0.70,
        "confidence_metadata": {"match_strength": 0.80, "label": "DEMO/SAMPLE"},
    },
    {
        "entity_id": "DEMO-ENTITY-004",
        "name": "Demo Custodial Service",
        "type": "custodial_service",
        "known_wallet": "0x5555555555555555555555555555555555555555",
        "chain": "ethereum",
        "source": "SYNTHETIC_DEMO",
        "source_reliability": 0.85,
        "confidence_metadata": {"match_strength": 0.95, "label": "DEMO/SAMPLE"},
    },
]