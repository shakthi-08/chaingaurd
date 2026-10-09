"""Public known-address registry for protocol classification.

Addresses are well-documented public contracts. A match is a reference lead,
not proof of user intent, ownership, or criminal activity.
Unknown counterparties must remain unlabeled.
"""

from __future__ import annotations

from typing import Any

# Operational chains currently backed by real providers.
OPERATIONAL_CHAINS = ("ethereum", "polygon")
# Architecturally reserved — no live ingestion adapter yet.
ARCHITECTURAL_CHAINS = ("bitcoin", "tron", "bsc", "solana")

UNCONFIRMED_DESTINATION = "Cross-chain transfer indicator detected; destination not confirmed."
UNKNOWN_CONTRACT = "Unknown Contract"

# category: bridge | dex | lending | staking | liquidity | mixer | other_defi
# relation: BRIDGE | DEFI_INTERACTION | MIXER
KNOWN_PROTOCOLS: list[dict[str, Any]] = [
    {
        "address": "0x40ec5b33f54e0e8a33a975908c5ba1c14e5bbbdf",
        "chain": "ethereum",
        "name": "Polygon PoS ERC20 bridge",
        "category": "bridge",
        "relation": "BRIDGE",
        "destination_chain": "polygon",
        "source": "public_reference_registry",
    },
    {
        "address": "0x8484ef722627bf18ca5ae6bcf49547b3807c3f75",
        "chain": "ethereum",
        "name": "Polygon PoS Ether bridge",
        "category": "bridge",
        "relation": "BRIDGE",
        "destination_chain": "polygon",
        "source": "public_reference_registry",
    },
    {
        "address": "0x7a250d5630b4cf539739df2c5dacb4c659f2488d",
        "chain": "ethereum",
        "name": "Uniswap V2 Router",
        "category": "dex",
        "relation": "DEFI_INTERACTION",
        "source": "public_reference_registry",
    },
    {
        "address": "0xe592427a0aece92de3edee1f18e0157c05861564",
        "chain": "ethereum",
        "name": "Uniswap V3 SwapRouter",
        "category": "dex",
        "relation": "DEFI_INTERACTION",
        "source": "public_reference_registry",
    },
    {
        "address": "0x7d2768de32b0b80b7a3454c06bdac94a69ddc7a9",
        "chain": "ethereum",
        "name": "Aave V2 LendingPool",
        "category": "lending",
        "relation": "DEFI_INTERACTION",
        "source": "public_reference_registry",
    },
    {
        "address": "0xae7ab96520de3a18e5e111b5eaab095312d7fe84",
        "chain": "ethereum",
        "name": "Lido stETH",
        "category": "staking",
        "relation": "DEFI_INTERACTION",
        "source": "public_reference_registry",
    },
    {
        "address": "0xba12222222228d8ba445958a75a0704d566bf2c8",
        "chain": "ethereum",
        "name": "Balancer V2 Vault",
        "category": "liquidity",
        "relation": "DEFI_INTERACTION",
        "source": "public_reference_registry",
    },
    {
        "address": "0x12d66f87a04a9e220743712ce6d9bb1b5616b8fc",
        "chain": "ethereum",
        "name": "Tornado Cash 0.1 ETH",
        "category": "mixer",
        "relation": "MIXER",
        "source": "public_reference_registry",
    },
    {
        "address": "0x47ce0c6ed5b0ce3d3a51fdb1c52dc66a7c3c2936",
        "chain": "ethereum",
        "name": "Tornado Cash 1 ETH",
        "category": "mixer",
        "relation": "MIXER",
        "source": "public_reference_registry",
    },
    {
        "address": "0x910cbd523d972eb0a6f4cae4618ad62622b22577",
        "chain": "ethereum",
        "name": "Tornado Cash 10 ETH",
        "category": "mixer",
        "relation": "MIXER",
        "source": "public_reference_registry",
    },
    {
        "address": "0xa160cdab225685da1d56aa342ad8841c3b53f291",
        "chain": "ethereum",
        "name": "Tornado Cash 100 ETH",
        "category": "mixer",
        "relation": "MIXER",
        "source": "public_reference_registry",
    },
]


def _index() -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (str(item["address"]).lower(), str(item["chain"]).lower()): item
        for item in KNOWN_PROTOCOLS
    }


PROTOCOL_INDEX = _index()


def lookup_protocol(address: str | None, chain: str | None) -> dict[str, Any] | None:
    if not address:
        return None
    key = (str(address).strip().lower(), str(chain or "ethereum").strip().lower())
    return PROTOCOL_INDEX.get(key)


def node_type_for_address(address: str, chain: str | None = None) -> str:
    match = lookup_protocol(address, chain)
    if match is None:
        return "wallet"
    category = match["category"]
    if category == "bridge":
        return "bridge"
    if category == "mixer":
        return "mixer"
    return "defi"


def relation_for_counterparty(address: str, chain: str | None = None, *, is_vasp: bool = False) -> str:
    match = lookup_protocol(address, chain)
    if match is not None:
        return str(match["relation"])
    if is_vasp:
        return "EXCHANGE_DEPOSIT"
    return "TRANSFER"
