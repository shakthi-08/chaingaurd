from copy import deepcopy

from fastapi.testclient import TestClient

from app.config import settings
from app.database import SessionLocal
from app.main import app
from app.models import Attribution, Evidence, Finding, RiskIndicator
from app.services.ai_provider import AIProvider, OpenAICompatibleProvider, ProviderUnavailableError, UnavailableAIProvider
from app.services.ai_service import AIService, SYSTEM_PROMPT
from app.services.attribution_service import AttributionService
from app.services.demo_case_seeder import seed_demo_case
from app.services.evidence_service import EvidenceService
from app.services.risk_analysis_service import RiskAnalysisService

client = TestClient(app)


class FakeProvider(AIProvider):
    name = "fake-test-provider"

    def __init__(self):
        self.system_prompt = None
        self.context = None

    def generate(self, system_prompt, context, request):
        self.system_prompt = system_prompt
        self.context = deepcopy(context)
        return f"Grounded response for {request}."


def setup_demo_analysis():
    seed_demo_case()
    RiskAnalysisService().analyze_case("CASE-DEMO-001")
    AttributionService().attribute_case("CASE-DEMO-001")
    EvidenceService().collect_case("CASE-DEMO-001")


def counts():
    with SessionLocal() as session:
        return (
            session.query(RiskIndicator).count(),
            session.query(Finding).count(),
            session.query(Attribution).count(),
            session.query(Evidence).count(),
        )


def test_unconfigured_provider_is_explicitly_unavailable():
    try:
        UnavailableAIProvider().generate("system", {}, "request")
        assert False, "Expected provider unavailable error"
    except ProviderUnavailableError as exc:
        assert "no provider is configured" in str(exc)


def test_context_is_structured_and_provider_receives_only_context():
    setup_demo_analysis()
    provider = FakeProvider()
    result = AIService(provider=provider).summary("CASE-DEMO-001")

    assert result["ai_assisted"] is True
    assert result["provider"] == "fake-test-provider"
    assert provider.system_prompt == SYSTEM_PROMPT
    assert "transactions" in provider.context
    assert "api_key" not in str(provider.context).lower()
    assert result["evidence_refs"]


def test_local_ollama_provider_is_supported_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "ollama")
    monkeypatch.setattr(settings, "ai_model", "qwen2.5-coder:7b")
    monkeypatch.setattr(settings, "ai_base_url", "http://localhost:11434/v1")
    monkeypatch.setattr(settings, "ai_api_key", None)
    monkeypatch.setattr(settings, "ai_timeout", 90)

    provider = AIService._configured_provider()

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.api_key == ""
    assert provider.base_url == "http://localhost:11434/v1"
    assert provider.timeout == 90


def test_openai_defaults_base_url_and_model_when_key_present(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "ai_model", None)
    monkeypatch.setattr(settings, "ai_base_url", None)
    monkeypatch.setattr(settings, "ai_api_key", "sk-test")
    monkeypatch.setattr(settings, "ai_timeout", 60)

    provider = AIService._configured_provider()

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://api.openai.com/v1"
    assert provider.model == "gpt-4o-mini"
    assert provider.api_key == "sk-test"


def test_gemini_defaults_base_url_and_model_when_key_present(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_model", None)
    monkeypatch.setattr(settings, "ai_base_url", None)
    monkeypatch.setattr(settings, "ai_api_key", "test-gemini-key")
    monkeypatch.setattr(settings, "ai_timeout", 60)

    provider = AIService._configured_provider()

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert provider.model == "gemini-2.5-flash"
    assert provider.api_key == "test-gemini-key"


def test_gemini_uses_configured_model(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_model", "gemini-2.0-flash")
    monkeypatch.setattr(settings, "ai_base_url", None)
    monkeypatch.setattr(settings, "ai_api_key", "test-gemini-key")

    provider = AIService._configured_provider()

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.model == "gemini-2.0-flash"
    assert provider.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_gemini_without_api_key_is_configuration_error(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", None)
    monkeypatch.setattr(settings, "ai_model", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "ai_base_url", "https://generativelanguage.googleapis.com/v1beta/openai")

    provider = AIService._configured_provider()
    assert isinstance(provider, UnavailableAIProvider)
    try:
        provider.generate("s", {}, "q")
        assert False, "expected configuration error"
    except ProviderUnavailableError as exc:
        assert "AI_API_KEY" in str(exc)


def test_openai_without_api_key_is_configuration_error(monkeypatch):
    monkeypatch.setattr(settings, "ai_provider", "openai")
    monkeypatch.setattr(settings, "ai_api_key", None)
    monkeypatch.setattr(settings, "ai_model", "gpt-4o-mini")
    monkeypatch.setattr(settings, "ai_base_url", "https://api.openai.com/v1")

    provider = AIService._configured_provider()
    assert isinstance(provider, UnavailableAIProvider)
    try:
        provider.generate("s", {}, "q")
        assert False, "expected configuration error"
    except ProviderUnavailableError as exc:
        assert "AI_API_KEY" in str(exc)


def test_health_reports_gemini_configured_when_api_key_present(monkeypatch):
    from app.main import _health_payload

    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", "test-gemini-key")
    monkeypatch.setattr(settings, "ai_model", None)

    payload = _health_payload()
    assert payload.ai_configured is True
    assert payload.ai_provider == "gemini"
    assert payload.ai_model == "gemini-2.5-flash"


def test_health_reports_gemini_unconfigured_without_api_key(monkeypatch):
    from app.main import _health_payload

    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "ai_api_key", None)
    monkeypatch.setattr(settings, "ai_model", "gemini-2.5-flash")

    payload = _health_payload()
    assert payload.ai_configured is False
    assert payload.ai_provider == "gemini"
    assert payload.ai_model is None


def test_context_includes_attribution_confidence_and_suspicious_evidence():
    setup_demo_analysis()
    service = AIService(provider=FakeProvider())
    context = service.build_context("CASE-DEMO-001")

    assert context["attributions"]
    assert any("confidence" in str(item) for item in context["attributions"])
    assert context["risk_indicators"]
    assert context["suspicious_transactions"]
    assert all("tx_hash" in item for item in context["suspicious_transactions"])


def test_ai_functions_do_not_change_deterministic_records():
    setup_demo_analysis()
    before = counts()
    service = AIService(provider=UnavailableAIProvider())
    for function in (service.summary, service.explain_path, service.explain_risk, service.explain_attribution, service.next_steps):
        result = function("CASE-DEMO-001")
        assert result["provider_status"] == "unavailable"
        assert result["ai_assisted"] is False
    assert counts() == before


def test_ai_endpoints_return_grounded_unavailable_responses():
    setup_demo_analysis()
    endpoints = [
        ("/cases/CASE-DEMO-001/ai/summary", None),
        ("/cases/CASE-DEMO-001/ai/explain-path", {"path_rank": 1}),
        ("/cases/CASE-DEMO-001/ai/explain-risk", None),
        ("/cases/CASE-DEMO-001/ai/explain-attribution", {"wallet": "0x1111111111111111111111111111111111111111"}),
        ("/cases/CASE-DEMO-001/ai/next-steps", None),
        ("/cases/CASE-DEMO-001/ai/ask", {"question": "What should an investigator review next?"}),
    ]
    for endpoint, payload in endpoints:
        response = client.post(endpoint, json=payload) if payload else client.post(endpoint)
        assert response.status_code == 200
        body = response.json()
        assert body["provider_status"] == "unavailable"
        assert body["ai_assisted"] is False
        assert "unavailable" in body["answer"].lower()
        assert "limitations" in body


def test_missing_case_is_rejected():
    response = client.post("/cases/NO-SUCH-CASE/ai/summary")
    assert response.status_code == 404
