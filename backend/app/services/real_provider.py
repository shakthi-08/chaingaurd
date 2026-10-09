from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request

from app.config import settings
from app.services.blockchain_provider import BlockchainProvider


class RealBlockchainProvider(BlockchainProvider):
    """Minimal real blockchain provider backed by Etherscan/Polygonscan APIs."""

    name = "real"
    SUPPORTED_CHAINS = {
        "ethereum": "1",
        "polygon": "137",
    }

    def __init__(self, chain: str = "ethereum", *, api_key: str | None = None, timeout: int | None = None) -> None:
        normalized_chain = (chain or "ethereum").strip().lower()
        if normalized_chain not in self.SUPPORTED_CHAINS:
            raise ValueError(f"Unsupported chain: {chain}")

        self.chain = normalized_chain
        self.api_key = (api_key or self._configured_api_key(normalized_chain) or "").strip()
        self.timeout = int(timeout if timeout is not None else settings.blockchain_api_timeout or 30)
        self.page_size = max(1, int(getattr(settings, "blockchain_page_size", 200) or 200))
        self.max_pages = max(1, int(getattr(settings, "blockchain_max_pages", 1) or 1))

    @staticmethod
    def _configured_api_key(chain: str) -> str | None:
        if chain == "ethereum":
            return settings.etherscan_api_key
        if chain == "polygon":
            return settings.polygonscan_api_key
        return None

    @staticmethod
    def validate_address(wallet_address: str) -> str:
        normalized = (wallet_address or "").strip().lower()
        if not re.fullmatch(r"^0x[0-9a-f]+$", normalized):
            raise ValueError("Wallet address must be a valid hexadecimal address starting with 0x.")
        return normalized

    def _base_url(self) -> str:
        if self.chain == "ethereum":
            return "https://api.etherscan.io/v2/api"
        if self.chain == "polygon":
            return "https://api.polygonscan.com/api"
        raise ValueError(f"Unsupported chain: {self.chain}")

    def _query_params(self, *, action: str, module: str = "account") -> dict[str, str]:
        params = {
            "module": module,
            "action": action,
            "apikey": self.api_key,
        }
        if self.chain == "ethereum":
            params["chainid"] = self.SUPPORTED_CHAINS[self.chain]
        return params

    def _fetch_json(self, *, action: str, module: str = "account", **extra: Any) -> list[dict[str, Any]]:
        if not self.api_key:
            raise ValueError(f"{self.chain.title()} API key is required for the real blockchain provider.")
        params = self._query_params(action=action, module=module)
        params.update({str(key): str(value) for key, value in extra.items() if value is not None})

        encoded = parse.urlencode(params)
        url = f"{self._base_url()}?{encoded}"

        try:
            req = request.Request(url, headers={"User-Agent": "ChainGuard/1.0"})
            with request.urlopen(req, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ValueError(f"Blockchain API request failed: {detail or exc.reason}") from exc
        except error.URLError as exc:
            raise ValueError(f"Unable to reach blockchain provider: {exc.reason}") from exc
        except TimeoutError as exc:
            raise ValueError(f"Blockchain provider timed out after {self.timeout}s.") from exc

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Blockchain provider returned invalid JSON.") from exc

        if isinstance(data, dict) and data.get("status") == "0":
            message = str(data.get("message") or data.get("result") or "no data")
            result_text = str(data.get("result", ""))
            if "No transactions found" in message or "No transactions found" in result_text:
                return []
            if "rate limit" in message.lower() or "max rate limit" in message.lower():
                raise ValueError("Blockchain provider rate limit exceeded.")
            if "invalid" in message.lower() and "address" in message.lower():
                raise ValueError(f"Blockchain provider rejected address: {message}")
            # Etherscan sometimes returns status=0 with empty result list as "No records"
            if isinstance(data.get("result"), list) and not data.get("result"):
                return []
            if result_text.strip() in {"", "[]", "None", "null"}:
                return []
            raise ValueError(f"Blockchain provider error: {message}")

        result = data.get("result") if isinstance(data, dict) else None
        if isinstance(result, list):
            return [item for item in result if isinstance(item, dict)]
        if isinstance(result, str) and not result.strip():
            return []
        return []

    def _paginated_account_records(self, *, action: str, address: str) -> tuple[list[dict[str, Any]], bool]:
        collected: list[dict[str, Any]] = []
        truncated = False
        for page in range(1, self.max_pages + 1):
            page_records = self._fetch_json(
                action=action,
                module="account",
                address=address,
                startblock=0,
                endblock=99999999,
                page=page,
                offset=self.page_size,
                sort="desc",
            )
            collected.extend(page_records)
            if len(page_records) < self.page_size:
                break
            if page == self.max_pages:
                truncated = True
        return collected, truncated

    def get_native_transactions(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        wallet = self.validate_address(wallet_address)
        records, truncated = self._paginated_account_records(action="txlist", address=wallet)

        filtered: list[dict[str, Any]] = []
        for item in records:
            try:
                ts = datetime.fromtimestamp(int(str(item.get("timeStamp") or 0)), tz=timezone.utc)
            except (TypeError, ValueError):
                continue
            if start_time and ts < start_time.astimezone(timezone.utc):
                continue
            if end_time and ts > end_time.astimezone(timezone.utc):
                continue
            filtered.append(
                {
                    "tx_hash": str(item.get("hash") or "").strip(),
                    "from": str(item.get("from") or "").strip().lower(),
                    "to": str(item.get("to") or "").strip().lower(),
                    "value": str(item.get("value") or "0"),
                    "token": "native",
                    "timestamp": ts.isoformat().replace("+00:00", "Z"),
                    "block": int(item.get("blockNumber") or 0),
                    "chain": self.chain,
                    "source": "chain_provider",
                    "synthetic": False,
                    "tx_type": "native",
                    "truncated": truncated,
                }
            )
        return filtered

    def get_token_transactions(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        wallet = self.validate_address(wallet_address)
        records, truncated = self._paginated_account_records(action="tokentx", address=wallet)

        filtered: list[dict[str, Any]] = []
        for item in records:
            try:
                ts = datetime.fromtimestamp(int(str(item.get("timeStamp") or 0)), tz=timezone.utc)
            except (TypeError, ValueError):
                continue
            if start_time and ts < start_time.astimezone(timezone.utc):
                continue
            if end_time and ts > end_time.astimezone(timezone.utc):
                continue
            token = str(item.get("tokenSymbol") or item.get("tokenName") or "ERC20").strip() or "ERC20"
            filtered.append(
                {
                    "tx_hash": str(item.get("hash") or "").strip(),
                    "from": str(item.get("from") or "").strip().lower(),
                    "to": str(item.get("to") or "").strip().lower(),
                    "value": str(item.get("value") or "0"),
                    "token": token,
                    "timestamp": ts.isoformat().replace("+00:00", "Z"),
                    "block": int(item.get("blockNumber") or 0),
                    "chain": self.chain,
                    "source": "chain_provider",
                    "synthetic": False,
                    "contract_address": str(item.get("contractAddress") or "").strip().lower() or None,
                    "tx_type": "token",
                    "truncated": truncated,
                }
            )
        return filtered

    def get_wallet_activity(
        self,
        wallet_address: str,
        *,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        wallet = self.validate_address(wallet_address)
        combined: dict[str, dict[str, Any]] = {}
        truncated = False
        for record in [
            *self.get_native_transactions(wallet, start_time=start_time, end_time=end_time),
            *self.get_token_transactions(wallet, start_time=start_time, end_time=end_time),
        ]:
            if not record.get("tx_hash"):
                continue
            truncated = truncated or bool(record.get("truncated"))
            combined.setdefault(record["tx_hash"], record)
        ordered = sorted(combined.values(), key=lambda item: item.get("timestamp", ""), reverse=True)
        for item in ordered:
            item["truncated"] = truncated
        return ordered
