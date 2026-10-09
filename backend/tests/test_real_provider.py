import json
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.config import Settings, settings
from app.main import app
from app.services.real_provider import RealBlockchainProvider
from app.services.wallet_ingestion_service import WalletIngestionService


def test_real_provider_url_encodes_query_values_and_preserves_request_options():
    response = MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = json.dumps({"status": "1", "result": []}).encode()

    with patch("app.services.real_provider.request.urlopen", return_value=response) as urlopen:
        provider = RealBlockchainProvider("ethereum", api_key="key with+symbols", timeout=7)
        assert provider._fetch_json(
            action="tx list", address="0xabc def", startblock=0, tag="latest+final"
        ) == []

    request = urlopen.call_args.args[0]
    query = parse_qs(urlsplit(request.full_url).query)
    assert query == {
        "module": ["account"],
        "action": ["tx list"],
        "apikey": ["key with+symbols"],
        "chainid": ["1"],
        "address": ["0xabc def"],
        "startblock": ["0"],
        "tag": ["latest+final"],
    }
    assert urlsplit(request.full_url).path == "/v2/api"
    assert request.headers["User-agent"] == "ChainGuard/1.0"
    assert urlopen.call_args.kwargs["timeout"] == 7


def test_real_provider_uses_configured_chain_keys_and_settings_names(monkeypatch):
    monkeypatch.setenv("ETHERSCAN_API_KEY", "eth-test-key")
    monkeypatch.setenv("POLYGONSCAN_API_KEY", "polygon-test-key")
    configured = Settings(_env_file=None)
    assert configured.etherscan_api_key == "eth-test-key"
    assert configured.polygonscan_api_key == "polygon-test-key"

    monkeypatch.setattr(settings, "etherscan_api_key", "eth-test-key")
    monkeypatch.setattr(settings, "polygonscan_api_key", "polygon-test-key")
    assert RealBlockchainProvider("ethereum").api_key == "eth-test-key"
    assert RealBlockchainProvider("polygon").api_key == "polygon-test-key"


def test_real_provider_configuration_selects_real_provider(monkeypatch):
    monkeypatch.setattr(settings, "blockchain_provider", "real")
    monkeypatch.setattr(settings, "etherscan_api_key", "eth-test-key")

    assert isinstance(WalletIngestionService().provider, RealBlockchainProvider)


def test_integration_capabilities_routes_are_registered_with_and_without_prefix():
    client = TestClient(app)
    for route in ("/integrations/capabilities", "/api/integrations/capabilities"):
        response = client.get(route)
        assert response.status_code == 200
        assert response.json()["live_integration"] is False
